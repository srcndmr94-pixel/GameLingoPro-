#!/usr/bin/env python3
"""GameLingoPro 3.6: clear translated HUD on real screen transitions;
translate GTA-style in-game phone messages inside their OCR text rectangles.

Requires all v3.4 and v3.5 patches. Original GameLingoPro APK, settings, bridge,
GameTranslator core and existing package identity are preserved.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
cap=src/'CaptureService.kt'
overlay=src/'GtExactOverlay.kt'
contract=src/'Overlay.kt'
build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
for file in (cap,overlay,contract,build,src/'GtSourceBox.kt'):
    if not file.is_file():raise RuntimeError('Missing generated GT 3.5 source: '+str(file))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Only the original GameLingoPro project is supported')
if 'overlay = GtExactOverlay(this)' not in cap.read_text():
    raise RuntimeError('GT single overlay not active')

def once(file,old,new):
    s=file.read_text(encoding='utf-8')
    if s.count(old)!=1:
        raise RuntimeError(f'{file.name}: expected exactly one anchor, got {s.count(old)}: {old[:95]!r}')
    file.write_text(s.replace(old,new,1),encoding='utf-8')

# Scene detection only reads on-screen OCR, never a timer.
(src/'GtUiScene.kt').write_text(r'''package com.example.altyazi
import java.util.Locale

/** Source-backed recognition of a modal menu vs a phone message page. */
internal object GtUiScene {
    private val tabs=setOf("map","brief","progress","game","store","settings",
        "journal","missions","objectives","inventory",
        "harita","bilgi","ilerleme","oyun","mağaza","ayarlar","görevler","envanter")
    fun mode(lines:List<GtAllHud.Line>,width:Int,height:Int,
             menuDetected:Boolean,phoneDetected:Boolean):String {
        if(phoneDetected)return "phone"
        if(menuDetected)return "menu"
        // These tabs can be read in EN before or in TR after rendering an
        // overlay. The two-language detector avoids a false scene exit.
        val topTabs=lines.count {
            val cx=(it.left+it.right)*.5f/width.coerceAtLeast(1)
            val cy=(it.top+it.bottom)*.5f/height.coerceAtLeast(1)
            cx in .12f.. .98f && cy in .015f.. .27f &&
                it.text.trim().lowercase(Locale.ROOT) in tabs
        }
        return if(topTabs>=2)"menu" else "game"
    }
    fun shouldSwitch(current:String,observed:String,stableScans:Int):Boolean =
        current!=observed && (observed!="game" || stableScans>=2)
}
''',encoding='utf-8')

# Phone screen: messages (inbox) / an opened contact (thread).
# Group nearby OCR lines belonging to a message bubble; no fixed screen
# coordinates for the translated text (source bounding rectangles are used).
(src/'GtPhoneUi.kt').write_text(r'''package com.example.altyazi
import java.util.Locale
import kotlin.math.abs
import kotlin.math.max

internal object GtPhoneUi {
    private val knownHeaders=setOf("messages","message","texts","sms",
        "linda","vicki","cal","andy","mia","kyle, jason, lucia")
    private val chrome=setOf("messages","message","texts","sms","back",
        "new message","edit","compose","send","cancel","reply")
    private fun norm(s:String)=s.trim().lowercase(Locale.ROOT)
    private fun central(line:GtAllHud.Line,width:Int,height:Int):Boolean {
        val cx=(line.left+line.right)*.5f/width.coerceAtLeast(1)
        val cy=(line.top+line.bottom)*.5f/height.coerceAtLeast(1)
        return cx in .39f.. .79f && cy in .07f.. .87f
    }
    private fun header(lines:List<GtAllHud.Line>,width:Int,height:Int):String? {
        val found=lines.filter { central(it,width,height) &&
            (it.top+it.bottom)*.5f/height.coerceAtLeast(1) in .07f.. .24f
        }.sortedBy{it.top}
        return found.firstOrNull { norm(it.text) in knownHeaders }?.text?.trim()
            ?: found.firstOrNull {
                it.text.length in 3..25 &&
                it.text.trim().matches(Regex("""[\p{L} ]{3,25}""")) &&
                lines.count { l->central(l,width,height) }>=4
            }?.text?.trim()
    }
    fun isPhoneScreen(lines:List<GtAllHud.Line>,width:Int,height:Int):Boolean {
        if(width<=0||height<=0)return false
        val centralLines=lines.filter { central(it,width,height) }
        if(centralLines.size<3)return false
        val title=header(lines,width,height)?:return false
        // Names alone cannot prove phone UI. Messages is a strong anchor;
        // named conversations need multiple rows in the phone's centre.
        return norm(title) in knownHeaders ||
            (centralLines.size>=5 && centralLines.count{it.text.length>19}>=2)
    }
    fun page(lines:List<GtAllHud.Line>,width:Int,height:Int):String {
        val name=header(lines,width,height)?.let(::norm)?:return "phone"
        return if(name in setOf("messages","message","texts","sms"))"inbox"
               else "thread:$name"
    }
    private fun skip(s:String):Boolean {
        val text=s.trim()
        return text.length<3 || norm(text) in chrome ||
            // Speaker/contact names belong to the phone's own UI.
            (norm(text) in knownHeaders && text.length<23)
    }
    fun group(lines:List<GtAllHud.Line>,width:Int,height:Int):List<GtAllHud.Card> {
        if(width<=0||height<=0)return emptyList()
        val inside=lines.filter { central(it,width,height) && !skip(it.text) &&
            it.top.toFloat()/height>.20f && it.bottom.toFloat()/height<.88f &&
            it.right>it.left && it.bottom>it.top
        }.sortedWith(compareBy<GtAllHud.Line>{it.top}.thenBy{it.left})
        val groups=ArrayList<MutableList<GtAllHud.Line>>()
        for(line in inside) {
            val existing=groups.lastOrNull()
            val previous=existing?.lastOrNull()
            val gap=if(previous==null)999999 else line.top-previous.bottom
            val lineHeight=if(previous==null)1 else max(8,previous.bottom-previous.top)
            val nearX=previous!=null && abs(line.left-previous.left)<width*.035f
            // Bubble line spacing is tight; a gap between chat bubbles starts
            // a fresh card so one translation cannot swallow another message.
            if(existing!=null && existing.size<9 && nearX &&
               gap>=-lineHeight/3 && gap<=lineHeight*.65f) existing.add(line)
            else groups.add(mutableListOf(line))
        }
        return groups.map { rows->
            GtAllHud.Card("phone-message",rows.joinToString(" "){it.text.trim()},
                rows.minOf{it.left},rows.minOf{it.top},
                rows.maxOf{it.right},rows.maxOf{it.bottom},rows.size)
        }.filter{it.text.length>=3}.take(18)
    }
}
''',encoding='utf-8')

# Carry the phone-bubble appearance through the existing overlay data contract.
once(contract,
'''        val sourceLines: Int = 1''',
'''        val sourceLines: Int = 1,
        val phoneBubble: Boolean = false, val phoneBackground: Int? = null''')

once(cap,
'''    private var gtLastMenuMode:Boolean?=null''',
'''    private var gtLastMenuMode:Boolean?=null
    private var gtActiveSurface="game"
    private var gtObservedSurface="game"
    private var gtSurfaceSeen=0
    private var gtPhonePage=""''')

# Rotation/capture reset must also reset the finite state machine.
once(cap,
'''                        gtLastMenuMode=null''',
'''                        gtLastMenuMode=null
                        gtActiveSurface="game"
                        gtObservedSurface="game"
                        gtSurfaceSeen=0
                        gtPhonePage=""''')

# A phone message is NOT a large dialogue subtitle at screen bottom.
once(cap,
'''                    processSubtitle(full)

                    if (!isTv''',
'''                    if(gtActiveSurface!="phone")processSubtitle(full)

                    if (!isTv''')

once(cap,
'''        var fullMenuDetected = false
        val cards = try {''',
'''        var fullMenuDetected = false
        var phoneDetected = false
        var observedSurface = "game"
        var observedPhonePage = ""
        val cards = try {''')

once(cap,
'''            fullMenuDetected = GtMenuUi.isGameMenu(candidates)
            if(fullMenuDetected)
                GtMenuUi.group(candidates,small.width,small.height,
                    prefs.topPct.coerceIn(0,98)/100f)
            else GtAllHud.group(candidates,small.width,small.height,
                prefs.topPct.coerceIn(0,98)/100f)''',
'''            // Full OCR is used for scene detection. Rendering candidates
            // excludes our own translated letters, but scene changes must
            // still work when earlier labels cover the English menu tabs.
            val screenLines=rawLines.mapNotNull { pair->
                val r=pair.second?:return@mapNotNull null
                GtAllHud.Line(pair.first,r.left,r.top,r.right,r.bottom)
            }
            phoneDetected=GtPhoneUi.isPhoneScreen(screenLines,small.width,small.height)
            fullMenuDetected=GtMenuUi.isGameMenu(candidates)
            observedSurface=GtUiScene.mode(screenLines,small.width,small.height,
                fullMenuDetected,phoneDetected)
            if(phoneDetected) {
                observedPhonePage=GtPhoneUi.page(screenLines,small.width,small.height)
                GtPhoneUi.group(candidates,small.width,small.height)
            } else if(fullMenuDetected || observedSurface=="menu")
                GtMenuUi.group(candidates,small.width,small.height,
                    prefs.topPct.coerceIn(0,98)/100f)
            else GtAllHud.group(candidates,small.width,small.height,
                prefs.topPct.coerceIn(0,98)/100f)''')

once(cap,
'''        val key = cards.joinToString("|") { item ->
            item.zone+":"+item.text+":"+item.left/25+":"+item.top/25
        }
        val hudNow''',
'''        if(observedSurface!=gtObservedSurface) {
            gtObservedSurface=observedSurface
            gtSurfaceSeen=1
        } else gtSurfaceSeen=(gtSurfaceSeen+1).coerceAtMost(30)
        val switched=GtUiScene.shouldSwitch(gtActiveSurface,observedSurface,gtSurfaceSeen)
        val phonePageChanged=observedSurface=="phone" && !switched &&
            gtActiveSurface=="phone" && observedPhonePage.isNotEmpty() &&
            gtPhonePage.isNotEmpty() && gtPhonePage!=observedPhonePage
        if(switched || phonePageChanged) {
            gtActiveSurface=observedSurface
            gtPhonePage=if(gtActiveSurface=="phone")observedPhonePage else ""
            gtHeldLabels.clear()
            lastHudLabels=emptyList()
            lastMenuKey=""
            gtHudCandidateKey=""
            gtHudCandidateSeen=0
            gtHudMissingScans=0
            gtLastMenuMode=null
            overlay.clearLabels()
            PhoneBridgeService.clearHud()
            if(gtActiveSurface=="phone") {
                // Remove the previous spoken subtitle when an on-screen chat
                // is opened; phone messages use OCR-aligned bubbles instead.
                shownSource=""
                candidate=""
                candidateSeen=0
                translatingFor=""
                subtitleGeneration.invalidate()
                showSubtitle(null)
            }
        }
        if(observedSurface!=gtActiveSurface)return
        val key = cards.joinToString("|") { item ->
            item.zone+":"+item.text+":"+item.left/25+":"+item.top/25
        }
        val hudNow''')

once(cap,
'''                if(fullMenuDetected && newCalls>=5)continue''',
'''                if((fullMenuDetected || phoneDetected) && newCalls>=5)continue''')

once(cap,
'''            labels.add(Overlay.Label(translated,x,y,right,bottom,card.sourceLines))''',
'''            // A pale in-game phone bubble must not look like the yellow
            // black-backed map/menu labels. Sample its native light fill.
            val phoneBackground=if(phoneDetected) try {
                val sx=((card.right+3).toFloat()/
                    smallWidthForHud(full.width)*full.width).toInt()
                    .coerceIn(0,full.width-1)
                val sy=((card.top+card.bottom)*.5f/
                    smallHeightForHud(full.width,full.height)*full.height).toInt()
                    .coerceIn(0,full.height-1)
                val sampled=full.getPixel(sx,sy)
                if(android.graphics.Color.red(sampled)>115 &&
                   android.graphics.Color.green(sampled)>115 &&
                   android.graphics.Color.blue(sampled)>115)sampled
                else android.graphics.Color.rgb(232,232,236)
            } catch (_:Throwable) { android.graphics.Color.rgb(232,232,236) }
            else null
            labels.add(Overlay.Label(translated,x,y,right,bottom,card.sourceLines,
                phoneDetected,phoneBackground))''')

# A new phone conversation page must not inherit the previous page's bubbles.
# In the same page we retain labels across transient OCR misses, but new
# messages at nearby coordinates replace previous text via the v3.4 matcher.

once(overlay,
'''                hudStyle(tv)
                tv.gravity=Gravity.TOP or Gravity.START
                tv.setPadding(dp(4),dp(2),dp(4),dp(2))''',
'''                hudStyle(tv)
                tv.gravity=Gravity.TOP or Gravity.START
                if(card.phoneBubble) {
                    // In-game mobile: native light bubble with dark lettering.
                    // Preserve the captured phone's background where possible.
                    tv.setTextColor(Color.rgb(35,37,41))
                    tv.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
                    tv.background=GradientDrawable().apply {
                        cornerRadius=dp(3).toFloat()
                        setColor(card.phoneBackground?:Color.rgb(232,232,236))
                    }
                    tv.setPadding(dp(2),dp(1),dp(2),dp(1))
                } else tv.setPadding(dp(4),dp(2),dp(4),dp(2))''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtPhoneUiSceneTest.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtPhoneUiSceneTest {
    private fun line(t:String,x:Int,y:Int,w:Int=190,h:Int=20)=
        GtAllHud.Line(t,x,y,x+w,y+h)
    @Test fun inGamePhoneListAndConversationAreDetected() {
        val inbox=listOf(line("Messages",765,90),
            line("Kyle, Jason, Lucia",752,141),line("Eh",790,168),
            line("Linda",752,199),line("Thanks for the heads up...",780,232),
            line("Vicki",752,270),line("This is mo's shop",785,295))
        assertTrue(GtPhoneUi.isPhoneScreen(inbox,1536,690))
        assertEquals("inbox",GtPhoneUi.page(inbox,1536,690))
        val thread=listOf(line("Linda",849,90),line("Rent. Remember it.",785,152),
            line("I saw you with our guest",778,223),
            line("from room 10.",778,247),
            line("She has been cautioned",778,271),
            line("for breaking guest policy",778,295),
            line("Thanks for the heads up.",778,420))
        assertTrue(GtPhoneUi.isPhoneScreen(thread,1536,690))
        assertEquals("thread:linda",GtPhoneUi.page(thread,1536,690))
        val cards=GtPhoneUi.group(thread,1536,690)
        assertTrue(cards.any{it.text.contains("I saw you with our guest")})
        assertFalse(cards.any{it.text=="Linda"})
    }
    @Test fun oldMapTextClearsWhenPhoneAppearsOrGameplayReturns() {
        assertTrue(GtUiScene.shouldSwitch("menu","phone",1))
        assertFalse(GtUiScene.shouldSwitch("menu","game",1))
        assertTrue(GtUiScene.shouldSwitch("menu","game",2))
    }
    @Test fun translatedMenuLabelsDoNotFakeGameExit() {
        val tabs=listOf(line("Harita",650,25),
            line("İlerleme",920,25),line("Ayarlar",1200,25))
        assertEquals("menu",GtUiScene.mode(tabs,1536,690,false,false))
        assertEquals("phone",GtUiScene.mode(tabs,1536,690,true,true))
    }
    @Test fun phoneMessageCardsUseOriginalOcrBounds() {
        val cards=GtPhoneUi.group(listOf(
            line("I saw you with our guest",780,230,215),
            line("from room 10.",780,253,158),
            line("Just so you understand",780,276,195)),1536,690)
        assertEquals(1,cards.size)
        assertEquals(3,cards.first().sourceLines)
        assertEquals(780,cards.first().left)
    }
}
''',encoding='utf-8')

# Regressions in v3.4 now expect a finite timeout, while v3.5 intentionally
# retained until mode change. Keep those assertions intact; scene tests above
# establish explicit removal semantics on menu/phone exit.

v=build.read_text(encoding='utf-8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
            r'\g<1>versionCode = 20261209',v,count=1)
if n!=1:raise RuntimeError('versionCode missing')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-3.6-GT-ScenePhone"',v,count=1)
if n!=1:raise RuntimeError('versionName missing')
build.write_text(v,encoding='utf-8')
print('GameLingoPro 3.6: menu/phone/game scene clearing + OCR-aligned in-game SMS')
