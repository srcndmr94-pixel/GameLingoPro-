#!/usr/bin/env python3
"""Add live game menu translation alongside GameLingoPro GT-only 3.0.1 renderer.
The original GameLingoPro app ID, MediaProjection, GT visual style, and TV bridge remain.
Only source changes after the v3.0.1 setup, never the GameTranslator application itself.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"
build=root/"app/build.gradle.kts"
for file in (cap,build,src/"GtAllHud.kt",src/"GtExactOverlay.kt"):
    if not file.is_file():raise RuntimeError(f"GameLingoPro 3.0.1 source missing: {file}")
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Refusing non-GameLingoPro project")
if "overlay = GtExactOverlay(this)" not in cap.read_text():
    raise RuntimeError("GT-only native subtitle renderer must be active")

menu=r'''package com.example.altyazi

import java.util.Locale
import kotlin.math.abs

/**
 * Complete game-menu text recognition, separate from live speech subtitles.
 * Keeps all English game labels/paragraphs in their original screen coordinates.
 * Uses only ML Kit OCR lines; does not render game graphics or translate icons.
 */
internal object GtMenuUi {
    private fun norm(s:String):String = s.trim()
        .lowercase(Locale.ROOT).replace(Regex("""\s+""")," ")

    private val nav = setOf("map","brief","progress","game","store",
        "help","photo studio","settings","recenter","set destination",
        "add marker","2d view","security","take value","exit")
    private val direct = mapOf(
        "map" to "Harita", "brief" to "Bilgi", "progress" to "İlerleme",
        "game" to "Oyun", "store" to "Mağaza", "help" to "Yardım",
        "photo studio" to "Fotoğraf Stüdyosu", "settings" to "Ayarlar",
        "recenter" to "Yeniden ortala", "2d view" to "2B görünüm",
        "add marker" to "İşaret ekle", "set destination" to "Hedef belirle",
        "exit" to "Çıkış", "security" to "Güvenlik",
        "take value" to "Ganimet değeri", "low" to "Düşük",
        "medium" to "Orta", "high" to "Yüksek"
    )
    private fun bare(s:String):String=norm(s)
        .replace(Regex("""(?:\s+[lLrR][1-3]|\s+[○◯●✕□△])+$"""),"")
        .trim()
    fun isGameMenu(lines:List<GtAllHud.Line>):Boolean {
        val labels=lines.map{bare(it.text)}.toSet()
        val sections=labels.count{it in nav}
        val top=lines.count{line->
            val t=norm(line.text)
            t=="map"||t=="brief"||t=="progress"||t=="photo studio"
        }
        val panel=lines.any{
            norm(it.text).contains("take value")||
            norm(it.text).startsWith("security")
        }
        return (sections>=2 && top>=1) || (panel && sections>=1)
    }
    fun knownControl(s:String):Boolean {
        val t=bare(s)
        return t in nav || t in direct || Regex("""(?i)^(?:recenter|2d view|add marker|set destination|exit)\b""").containsMatchIn(t)
    }
    fun localized(s:String):String? {
        val trimmed=s.trim()
        val base=bare(trimmed)
        val translation=direct[base]?:return null
        val suffix=trimmed.substring(base.length).trim()
        return if (suffix.isEmpty()) translation else "$translation $suffix"
    }
    fun keepAsGameName(s:String):Boolean {
        val t=s.trim()
        return t.length>7 && t.length<65 &&
            t.any{it=='-'} &&
            t.all{!it.isLetter() || it.isUpperCase()}
    }
    fun group(
        input:List<GtAllHud.Line>,width:Int,height:Int,subtitleTop:Float
    ):List<GtAllHud.Card> {
        if(width<2||height<2)return emptyList()
        val lines=input.filter{ line ->
            line.text.count(Char::isLetter)>=2 &&
            line.right>line.left && line.bottom>line.top &&
            line.top>=height*.018f && line.bottom<=height*.985f &&
            // Preserve the separate dialogue subtitle recognizer.
            !((line.left+line.right)/2f in width*.33f..width*.67f &&
              (line.top+line.bottom)/2f>=height*subtitleTop)
        }.sortedWith(compareBy<GtAllHud.Line>{it.top}.thenBy{it.left})
        val groups=mutableListOf<MutableList<GtAllHud.Line>>()
        for(line in lines) {
            val isolated=knownControl(line.text) || keepAsGameName(line.text) ||
                (line.text.trim().length<22 && !line.text.contains(","))
            val candidate=if(isolated)null else groups.asReversed().firstOrNull{g->
                val last=g.last()
                val previousText=last.text.trim()
                val lastHeight=(last.bottom-last.top).coerceAtLeast(8)
                val gap=line.top-last.bottom
                val xTolerance=width*.045f
                !knownControl(previousText) && !keepAsGameName(previousText) &&
                previousText.length>=19 &&
                gap>=-lastHeight*.4f && gap<=lastHeight*1.65f &&
                abs(line.left-last.left)<=xTolerance &&
                abs(line.left-g.first().left)<=xTolerance &&
                g.size<7
            }
            if(candidate==null)groups.add(mutableListOf(line))
            else candidate.add(line)
        }
        return groups.mapNotNull{group->
            val text=group.joinToString(" "){it.text.trim()}.trim()
            if(text.length<2 || keepAsGameName(text))null
            else {
                val left=group.minOf{it.left}
                val right=group.maxOf{it.right}
                val top=group.minOf{it.top}
                val bottom=group.maxOf{it.bottom}
                val centerX=(left+right)/2f/width
                val centerY=(top+bottom)/2f/height
                val zone=when {
                    centerX<.34f->"menu-left"
                    centerX>.76f->"menu-right"
                    centerY<.17f->"menu-top"
                    else->"menu-panel"
                }
                GtAllHud.Card(zone,text,left,top,right,bottom)
            }
        }.take(32)
    }
}
'''
(src/"GtMenuUi.kt").write_text(menu,encoding="utf-8")

s=cap.read_text(encoding="utf-8")
a='''        val cards = try {
            val rawLines = ocrLines(small)'''
b='''            GtAllHud.group(candidates,small.width,small.height,
                prefs.topPct.coerceIn(0,98)/100f)
        } finally {'''
assert s.count(a)==1,(a,s.count(a))
assert s.count(b)==1,(b,s.count(b))
s=s.replace(a,'''        var fullMenuDetected = false
        val cards = try {
            val rawLines = ocrLines(small)''',1)
s=s.replace('''                if (isControllerLabel(text) || isOurOwnText(text)) continue''',
            '''                if ((isControllerLabel(text) && !GtMenuUi.knownControl(text)) ||
                    isOurOwnText(text)) continue''',1)
s=s.replace(b,'''            fullMenuDetected = GtMenuUi.isGameMenu(candidates)
            if(fullMenuDetected)
                GtMenuUi.group(candidates,small.width,small.height,
                    prefs.topPct.coerceIn(0,98)/100f)
            else GtAllHud.group(candidates,small.width,small.height,
                prefs.topPct.coerceIn(0,98)/100f)
        } finally {''',1)
# Full menus must progress through their queue even while the visible OCR is unchanged.
old='''        if(key==lastMenuKey){
            PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
            return
        }
        lastMenuKey=key'''
new='''        if(key==lastMenuKey && cards.all { item ->
            GtMenuUi.keepAsGameName(item.text) ||
            gtHudTranslatedCache.containsKey(item.zone+"|"+GtNativeEngine.normalize(item.text))
        }) {
            PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
            return
        }
        lastMenuKey=key'''
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)
old='''        val labels=ArrayList<Overlay.Label>()
        for(card in cards){
            val source = GtNativeEngine.normalize(card.text)
            if(source.isBlank() || isOurOwnText(source))continue
            val cacheKey=card.zone+"|"+source
            var translated=gtHudTranslatedCache[cacheKey]
            if(translated==null){
                translated=translateMenuText(source)?.trim()
                if(translated.isNullOrBlank())continue
                if(gtHudTranslatedCache.size>160)gtHudTranslatedCache.remove(
                    gtHudTranslatedCache.keys.first())
                gtHudTranslatedCache[cacheKey]=translated
            }'''
new='''        val labels=ArrayList<Overlay.Label>()
        var newCalls=0
        for(card in cards){
            val source = GtNativeEngine.normalize(card.text)
            if(source.isBlank() || isOurOwnText(source) ||
                GtMenuUi.keepAsGameName(source)) continue
            val cacheKey=card.zone+"|"+source
            var translated=gtHudTranslatedCache[cacheKey]
            if(translated==null) {
                // Translate busy game menus incrementally to avoid 20+ network
                // requests blocking the screen, while preserving cached labels.
                if(fullMenuDetected && newCalls>=5)continue
                newCalls++
                translated=if(fullMenuDetected)
                    GtMenuUi.localized(source) ?: translateMenuText(source)?.trim()
                    else translateMenuText(source)?.trim()
                if(translated.isNullOrBlank())continue
                if(gtHudTranslatedCache.size>220)gtHudTranslatedCache.remove(
                    gtHudTranslatedCache.keys.first())
                gtHudTranslatedCache[cacheKey]=translated
            }'''
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)
# The old preference is optional for standalone menu scan; user explicitly
# requested automatic menus on game screen. Keep original phone capture guard.
old='''if (!isTv && (prefs.menuTranslate || PhoneBridgeService.running) && cycle % MENU_EVERY == 0L'''
new='''if (!isTv && cycle % MENU_EVERY == 0L'''
assert s.count(old)==1,(old,s.count(old))
s=s.replace(old,new,1)
cap.write_text(s,encoding="utf-8")

p=build.read_text(encoding="utf-8")
p,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261204',p,count=1)
assert n==1
p,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
r'\g<1>versionName = "GameLingoPro-3.1-GT-MenuOCR"',p,count=1)
assert n==1
build.write_text(p,encoding="utf-8")

test=root/"app/src/test/java/com/example/altyazi/GtMenuUiTest.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtMenuUiTest {
    private fun line(t:String,x:Int,y:Int,w:Int=190):GtAllHud.Line =
        GtAllHud.Line(t,x,y,x+w,y+22)

    @Test fun detectsTheMapMenuFromRealScreenshotLabels() {
        val rows=listOf(line("JASON & LUCIA",580,25),line("MAP",750,25),
            line("BRIEF",820,25),line("PROGRESS",940,25),
            line("TACO BOMB - GELLHORN",812,259))
        assertTrue(GtMenuUi.isGameMenu(rows))
    }
    @Test fun joinsDescriptionButNotTheStoreName() {
        val rows=listOf(line("MAP",730,25),
            line("BRIEF",820,25),line("PROGRESS",950,25),
            line("TACO BOMB - GELLHORN",815,250),
            line("Fast-food chain popular for its Mexican-",825,285,310),
            line("inspired culinary creations, with dine-in",825,309,310),
            line("and drive-thru options.",825,333,310),
            line("SECURITY",827,371),line("LOW",1090,371))
        val cards=GtMenuUi.group(rows,1536,690,.74f)
        val paragraph=cards.firstOrNull {it.text.startsWith("Fast-food")}
        assertNotNull(paragraph)
        assertTrue(paragraph!!.text.endsWith("drive-thru options."))
        assertFalse(cards.any {it.text.startsWith("TACO BOMB")})
    }
    @Test fun leftMenuAndRightButtonsAreIndependent() {
        val rows=listOf(line("Map",183,142),line("Game",183,187),
            line("Store",183,231),line("Settings",183,361),
            line("RECENTER L3",1232,522),line("SET DESTINATION X",1217,612))
        val out=GtMenuUi.group(rows,1536,690,.74f)
        assertEquals(6,out.size)
        assertTrue(out.any{it.text=="Settings"})
        assertTrue(out.any{it.text.startsWith("RECENTER")})
    }
    @Test fun translationOfKnownMenuItemsPreservesButton() {
        assertEquals("Harita",GtMenuUi.localized("Map"))
        assertEquals("Hedef belirle X",GtMenuUi.localized("SET DESTINATION X"))
    }
    @Test fun lowerCenterSpeechStaysInSubtitlePipeline() {
        val row=line("Don't translate this spoken subtitle again",600,628,370)
        assertTrue(GtMenuUi.group(listOf(row),1536,690,.75f).isEmpty())
    }
}
''',encoding="utf-8")
assert "GtMenuUi.group" in cap.read_text()
assert 'overlay = GtExactOverlay(this)' in cap.read_text()
print("GameLingoPro 3.1 GT menu OCR: all-screen map/menu text and incremental translation installed")
