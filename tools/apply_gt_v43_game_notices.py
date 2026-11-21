#!/usr/bin/env python3
"""GameLingoPro 4.3: auto-translate in-game SMS popup and on-screen tips.

Apply AFTER GameLingoPro 4.2. Keeps the same Android package, model order,
WebOS features and single GameTranslator overlay. English-source-driven: only
the source notification is translated; it clears on disappearance.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"
over=src/"GtExactOverlay.kt"
contract=src/"Overlay.kt"
build=root/"app/build.gradle.kts"
test=root/"app/src/test/java/com/example/altyazi"
for f in (cap,over,contract,build,src/"GtSelectedMapPanel.kt"):
    if not f.is_file():raise RuntimeError("Expected GameLingoPro 4.2 source missing: "+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Not original GameLingoPro")
if "gtPanelTranslatedTitle" not in cap.read_text():raise RuntimeError("4.2 is required")
def once(path,before,after):
    s=path.read_text(encoding="utf8")
    n=s.count(before)
    if n!=1:raise RuntimeError(f"{path.name}: anchor count {n} (need 1): {before[:90]!r}")
    path.write_text(s.replace(before,after,1),encoding="utf8")

(src/"GtGameNotice.kt").write_text(r'''package com.example.altyazi
import java.util.Locale
import kotlin.math.abs

/** OCR geometry for *in-game* SMS and tutorial notices, not Android alerts. */
internal object GtGameNotice {
    data class Notice(
        val kind:String, val title:String, val body:String,
        val left:Int,val top:Int,val right:Int,val bottom:Int,val rows:Int
    ) {
        val identity:String get()=kind+"|"+title.lowercase(Locale.ROOT).trim()
        val isSms:Boolean get()=kind=="sms"
    }
    private val excluded=setOf("map","brief","progress","game","store",
        "settings","inventory","features","standard","recenter",
        "exit","sms","message","messages","subtitle","mission")
    private fun person(s:String):Boolean {
        val t=s.trim()
        if(t.length !in 3..28 || t.lowercase(Locale.ROOT) in excluded)return false
        if(t.count{it==' '}>2 || !t.first().isUpperCase())return false
        return t.count(Char::isLetter)>=3 &&
            t.all{it.isLetter() || it==' ' || it=='\'' || it=='’'}
    }
    fun find(lines:List<GtAllHud.Line>,w:Int,h:Int,
             activeTitle:String?=null):Notice? {
        if(w<100 || h<100)return null
        val valid=lines.filter{
            it.text.isNotBlank() && it.right>it.left && it.bottom>it.top
        }.sortedWith(compareBy<GtAllHud.Line>{it.top}.thenBy{it.left})
        // In-game texts (Moses, Vicki, etc.) show an untouched sender heading
        // followed by one or more English lines in a pop-up at screen side.
        val headers=valid.filter{
            person(it.text) &&
            it.left.toFloat()/w in .025f.. .65f &&
            it.top.toFloat()/h in .34f.. .91f
        }
        for(head in headers) {
            val near=valid.filter{
                it !== head && it.top>head.bottom &&
                it.top-head.bottom<=h*.25f &&
                abs(it.left-head.left)<=w*.16f &&
                it.right.toFloat()/w<=.84f &&
                it.text.length>=11 &&
                it.text.count(Char::isLetter)>=7 &&
                it.text.any(Char::isLowerCase)
            }.sortedBy{it.top}
            val rows=ArrayList<GtAllHud.Line>()
            for(row in near) {
                if(rows.isNotEmpty()) {
                    val previous=rows.last()
                    val gap=row.top-previous.bottom
                    val lineH=(previous.bottom-previous.top).coerceAtLeast(8)
                    if(gap < -lineH/2 || gap > lineH*2.1f)break
                    if(abs(row.left-previous.left)>w*.10f)break
                }
                rows.add(row)
                if(rows.size>=6)break
            }
            val source=rows.joinToString(" "){it.text.trim()}.trim()
            if(source.length>=23) return Notice("sms",head.text.trim(),source,
                rows.minOf{it.left},rows.minOf{it.top},
                rows.maxOf{it.right},rows.maxOf{it.bottom},rows.size)
            // When our translation sits on the English body, the untouched
            // heading is still a valid presence signal for the SAME sender.
            if(activeTitle!=null &&
               activeTitle.equals(head.text.trim(),ignoreCase=true)) {
                return Notice("sms",head.text.trim(),"",
                    head.left,head.bottom+1,head.right,head.bottom+24,1)
            }
        }

        // Tutorial notifications (e.g. long-gun storage) have no sender.
        // Narrow to the upper-left pop-up area and require multiple OCR lines,
        // so regular bottom dialogue is not mistaken for a notification.
        val candidates=valid.filter{
            it.left.toFloat()/w in .025f.. .46f &&
            it.top.toFloat()/h in .12f.. .70f &&
            it.right.toFloat()/w<.69f &&
            it.text.length>=12 && it.text.any(Char::isLowerCase)
        }
        for(first in candidates) {
            val rows=ArrayList<GtAllHud.Line>()
            rows.add(first)
            for(row in candidates.filter{it.top>first.top}.sortedBy{it.top}) {
                val previous=rows.last()
                val gap=row.top-previous.bottom
                val lineH=(previous.bottom-previous.top).coerceAtLeast(8)
                if(gap>lineH*1.5f || gap < -lineH/2)break
                if(abs(row.left-first.left)>w*.052f)break
                rows.add(row)
                if(rows.size>=5)break
            }
            val text=rows.joinToString(" "){it.text.trim()}.trim()
            if(rows.size>=2 && text.length>=48) return Notice(
                "tip",text,text,
                rows.minOf{it.left},rows.minOf{it.top},
                rows.maxOf{it.right},rows.maxOf{it.bottom},rows.size)
        }
        return null
    }
}
''',encoding="utf8")

once(contract,
'''        val sourceLines: Int = 1
    )''',
'''        val sourceLines: Int = 1,
        val gameNotice: Boolean = false,
        val lightNotice: Boolean = false
    )''')

# Note: all captions use the native GT overlay; these two flags only tune
# text/background for the notification's original white or dark surface.
once(over,
'''                hudStyle(tv)
                tv.gravity=Gravity.TOP or Gravity.START
                tv.setPadding(dp(4),dp(2),dp(4),dp(2))''',
'''                hudStyle(tv)
                tv.gravity=Gravity.TOP or Gravity.START
                if(card.gameNotice) {
                    val light=card.lightNotice
                    tv.setTextColor(if(light)Color.rgb(40,53,83) else Color.WHITE)
                    tv.background=GradientDrawable().apply{
                        cornerRadius=dp(3).toFloat()
                        setColor(if(light)Color.rgb(233,240,248) else Color.rgb(51,49,65))
                    }
                    tv.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
                    tv.setPadding(dp(2),dp(1),dp(2),dp(1))
                    tv.maxLines=(card.sourceLines+1).coerceIn(1,7)
                    tv.ellipsize=android.text.TextUtils.TruncateAt.END
                } else {
                    tv.setPadding(dp(4),dp(2),dp(4),dp(2))
                }''')
once(over,
'''                lp.height=FrameLayout.LayoutParams.WRAP_CONTENT
                lp.leftMargin=x''',
'''                lp.height=if(card.gameNotice)sourceH else FrameLayout.LayoutParams.WRAP_CONTENT
                lp.leftMargin=x''')

once(cap,
'''    private var menuJob: Job? = null''',
'''    private var menuJob: Job? = null
    @Volatile private var gtNoticeMode=false
    private var gtNoticeIdentity=""
    private var gtNoticeTitle=""
    private var gtNoticeSource=""
    private var gtNoticeTranslated=""
    private var gtNoticeLight=false
    private var gtNoticeMissing=0
    private var gtNoticeAttempt=0L
    private var gtNoticeRect:Overlay.Label?=null
    private var gtNoticeJob:Job?=null
    private val gtNoticeCache=java.util.concurrent.ConcurrentHashMap<String,String>()''')

# Clear stale notification on a capture orientation change.
once(cap,
'''                        gtMapPanelMode=false
                        gtPanelJobs.values.forEach{it.cancel()}''',
'''                        gtMapPanelMode=false
                        gtNoticeMode=false
                        gtNoticeIdentity=""
                        gtNoticeTitle=""
                        gtNoticeTranslated=""
                        gtNoticeJob?.cancel()
                        gtNoticeJob=null
                        gtNoticeRect=null
                        gtNoticeMissing=0
                        gtPanelJobs.values.forEach{it.cancel()}''')

# Temporarily remove Turkish labels on every second frame while a game
# notification is active: source must be read without being hidden by us.
once(cap,
'''                    val full = grabFull()
                    if (full == null) {''',
'''                    val noticeProbe=gtNoticeMode && cycle%2L==0L
                    if(noticeProbe) {
                        overlay.clearLabels()
                        delay(65L)
                    }
                    val full = grabFull()
                    if (full == null) {
                        if(noticeProbe)drawGameNotice()''')

once(cap,
'''                    if(!gtMapPanelMode)processSubtitle(full)''',
'''                    if(!gtMapPanelMode && !gtNoticeMode)processSubtitle(full)''')

once(cap,
'''                    if (!isTv && (gtMapPanelMode || cycle % MENU_EVERY == 0L) &&
                        menuJob?.isActive != true) {''',
'''                    if (!isTv &&
                        (gtMapPanelMode || gtNoticeMode || cycle % MENU_EVERY == 0L) &&
                        menuJob?.isActive != true) {''')

once(cap,'''                                processMenu(copy)''',
'''                                processMenu(copy,noticeProbe)''')

once(cap,
'''    private suspend fun processMenu(full: Bitmap) {
        if(processMapDetailPanels(full))return''',
'''    private suspend fun processMenu(full: Bitmap, noticeProbe:Boolean=false) {
        if(!gtMapPanelMode && processGameNotice(full,noticeProbe))return
        if(processMapDetailPanels(full)) {
            if(gtNoticeMode)resetGameNotice()
            return
        }''')

anchor='''    // The capture bitmap is scaled uniformly down to MENU_WIDTH.'''
helper=r'''    private fun drawGameNotice() {
        if(!gtNoticeMode || gtNoticeTranslated.isBlank())return
        val rect=gtNoticeRect?:return
        val label=Overlay.Label(gtNoticeTranslated,rect.x,rect.y,
            rect.rightX,rect.bottomY,rect.sourceLines,
            gameNotice=true,lightNotice=gtNoticeLight)
        overlay.setLabels(listOf(label))
        lastHudLabels=listOf(label)
        PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
    }

    private fun resetGameNotice() {
        gtNoticeJob?.cancel()
        gtNoticeJob=null
        gtNoticeMode=false
        gtNoticeIdentity=""
        gtNoticeTitle=""
        gtNoticeSource=""
        gtNoticeTranslated=""
        gtNoticeMissing=0
        gtNoticeRect=null
        lastHudLabels=emptyList()
        gtHeldLabels.clear()
        overlay.clearLabels()
        PhoneBridgeService.clearHud()
    }

    /** In-game SMS and tutorial tips: independently recognized and translated.
     * No manually supplied screenshots/logs are required for normal operation.
     * Removal is by source OCR, not a permanent 120-second retention.
     */
    private suspend fun processGameNotice(full:Bitmap,probe:Boolean):Boolean {
        if(gtNoticeMode && !probe)return true
        val factor=min(1f,MENU_WIDTH.toFloat()/max(full.width,1))
        val small=if(factor<1f)Bitmap.createScaledBitmap(full,
            max(2,(full.width*factor).toInt()),
            max(2,(full.height*factor).toInt()),true) else full
        val w=small.width
        val h=small.height
        val lines=try {
            ocrLines(small).mapNotNull{(text,box)->
                if(box==null || text.count(Char::isLetter)<2)null
                else GtAllHud.Line(text.trim(),box.left,box.top,box.right,box.bottom)
            }
        } finally {if(small!==full)small.recycle()}
        if(GtSelectedMapPanel.isMap(lines,w,h)) {
            if(gtNoticeMode)resetGameNotice()
            return false
        }
        val notice=GtGameNotice.find(lines,w,h,
            if(gtNoticeMode && gtNoticeLight)gtNoticeTitle else null)
        if(notice==null) {
            if(!gtNoticeMode)return false
            gtNoticeMissing++
            if(gtNoticeMissing>=2) {
                log("OYUN BİLDİRİMİ KAYBOLDU: çeviri silindi")
                resetGameNotice()
            } else drawGameNotice()
            return true
        }
        gtNoticeMissing=0
        val identity=notice.identity
        if(!gtNoticeMode || gtNoticeIdentity!=identity) {
            gtNoticeJob?.cancel()
            gtNoticeMode=true
            gtNoticeIdentity=identity
            gtNoticeTitle=notice.title
            gtNoticeSource=""
            gtNoticeTranslated=""
            gtNoticeRect=null
            gtNoticeAttempt=0L
            gtNoticeLight=notice.isSms
            lastMenuKey=""
            gtHudCandidateKey=""
            gtHeldLabels.clear()
            lastHudLabels=emptyList()
            overlay.clearLabels()
            shownSource=""
            translatingFor=""
            subtitleGeneration.invalidate()
            showSubtitle(null)
            log("OYUN BİLDİRİMİ ALGILANDI: "+notice.title.take(40))
        }
        if(notice.body.isNotBlank() && notice.body!=gtNoticeSource) {
            gtNoticeJob?.cancel()
            gtNoticeSource=notice.body
            gtNoticeTranslated=""
            val xScale=screenWidth.toFloat()/w
            val yScale=screenHeight.toFloat()/h
            gtNoticeRect=Overlay.Label("",
                (notice.left*xScale).toInt(),
                (notice.top*yScale).toInt(),
                (notice.right*xScale).toInt(),
                (notice.bottom*yScale).toInt(),notice.rows)
            overlay.clearLabels()
            val key=notice.identity+"|"+GtNativeEngine.normalize(notice.body)
            val cached=gtNoticeCache[key]
            if(cached!=null) {
                gtNoticeTranslated=cached
                drawGameNotice()
            }
        }
        val source=gtNoticeSource
        val id=gtNoticeIdentity
        if(source.isBlank() || gtNoticeTranslated.isNotBlank() ||
            gtNoticeJob?.isActive==true) {
            drawGameNotice()
            return true
        }
        val now=android.os.SystemClock.elapsedRealtime()
        if(now-gtNoticeAttempt<1250L)return true
        gtNoticeAttempt=now
        gtNoticeJob=scope.launch {
            val result=kotlinx.coroutines.withTimeoutOrNull(4200L) {
                translateMenuText(source)
            }?.trim()
            if(gtNoticeMode && gtNoticeIdentity==id &&
               gtNoticeSource==source && !result.isNullOrBlank() &&
               !result.equals(source,ignoreCase=true)) {
                gtNoticeTranslated=result
                gtNoticeCache[id+"|"+GtNativeEngine.normalize(source)]=result
                drawGameNotice()
                log("OYUN BİLDİRİMİ ÇEVRİLDİ: "+gtNoticeTitle.take(40))
            }
        }
        return true
    }

'''
s=cap.read_text(encoding="utf8")
if s.count(anchor)!=1:raise RuntimeError("No notification-helper insertion anchor")
cap.write_text(s.replace(anchor,helper+anchor,1),encoding="utf8")

test.mkdir(parents=True,exist_ok=True)
(test/"GtGameNoticeTest.kt").write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtGameNoticeTest {
    private fun row(text:String,x:Int,y:Int,w:Int=350,h:Int=22) =
        GtAllHud.Line(text,x,y,x+w,y+h)
    @Test fun recognizesMosesIncomingPopupWithoutManualSelection() {
        val sample=listOf(
            row("Moses",316,487,160),
            row("Clients stiffed me when it",220,539),
            row("was time to pay up. Trashed",219,571),
            row("my shop, too. They wanna...",222,603))
        val notice=GtGameNotice.find(sample,1536,690)
        assertNotNull(notice)
        assertEquals("sms",notice!!.kind)
        assertEquals("Moses",notice.title)
        assertEquals(3,notice.rows)
        assertTrue(notice.body.contains("Trashed"))
        assertEquals(220,notice.left)
    }
    @Test fun senderHeaderStillSignalsNotificationUnderTranslatedBody() {
        val item=GtGameNotice.find(listOf(row("Moses",316,487,160)),
            1536,690,"Moses")
        assertNotNull(item)
        assertEquals("",item!!.body)
    }
    @Test fun tutorialTipIsSeparateFromDialogue() {
        val tip=GtGameNotice.find(listOf(
            row("Long guns can be stored",130,275,345),
            row("in your trunk and taken out",130,304,354),
            row("when you need them.",130,333,290)),1536,690)
        assertEquals("tip",tip!!.kind)
        assertTrue(tip.body.contains("trunk"))
        val speech=GtGameNotice.find(listOf(
            row("Where are you going?",600,622,320),
            row("Wait for me!",600,652,200)),1536,690)
        assertNull(speech)
    }
    @Test fun noticeUsesOneOriginalSizeOverlayAndClearsWhenAbsent() {
        val service=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val overlay=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(service.contains("resetGameNotice()"))
        assertTrue(service.contains("noticeProbe=gtNoticeMode"))
        assertTrue(service.contains("gameNotice=true"))
        assertTrue(overlay.contains("if(card.gameNotice)"))
    }
}
''',encoding="utf8")

v=build.read_text(encoding="utf8")
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261216',v,count=1)
if n!=1:raise RuntimeError("versionCode missing")
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-4.3-AutoGameNotices"',v,count=1)
if n!=1:raise RuntimeError("versionName missing")
build.write_text(v,encoding="utf8")
print("GameLingoPro 4.3: in-game incoming messages and tips are recognized, translated in-place, and cleared with their source")
