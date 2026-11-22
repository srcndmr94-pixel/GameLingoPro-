#!/usr/bin/env python3
"""5.2.1 clean QA: fix reproduced corner false positives + HUD mask reset."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
notice=src/'GtGameNotice.kt';view=src/'GtExactOverlay.kt'
cap=src/'CaptureService.kt';build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
if 'GameLingoPro-5.2-UserColors' not in build.read_text():raise RuntimeError('Need 5.2 base')
if 'gtQuestBoxesOnly' in cap.read_text():raise RuntimeError('Translation categories are not enabled')
def once(f,a,b):
 s=f.read_text(encoding='utf8');n=s.count(a)
 if n!=1:raise RuntimeError(f'{f.name}: expected one anchor, found {n}: {a[:85]}')
 f.write_text(s.replace(a,b,1),encoding='utf8')

once(notice,
'''            val cornerCue=Regex(
                """(?i)\\b(?:objective|mission|new|reward|complete|available|""" +
                """collect|meet|drive|reach|find|delivered)\\b""")
            if(w>h && body.length>=25 && (gameEnglish(body) ||
                    cornerCue.containsMatchIn(body)) &&
                !psShell.containsMatchIn(body) &&
                // Generic speech is not a game notification. Single-line
                // notices need an explicit game objective/action cue.
                (rows.size>=2 || cornerCue.containsMatchIn(body))) {''',
'''            val gameNoticeCue=Regex(
                """(?i)\\b(?:new\\s+(?:objective|mission|task)|objective|""" +
                """mission|quest|reward|challenge|completed|unlocked|""" +
                """available|delivered|notification|updated)\\b""")
            val taskInstruction=Regex(
                """(?i)^(?:meet|drive|reach|find|collect|take|""" +
                """go to|return to|head to|deliver|locate)\\b""")
            // Two video subtitle lines are NOT evidence of a game notice.
            val realGameCue=gameNoticeCue.containsMatchIn(body) ||
                taskInstruction.containsMatchIn(rows.first().text.trim())
            if(w>h && body.length>=25 && realGameCue &&
                !psShell.containsMatchIn(body)) {''')

once(view,
'''    private val boxes = ArrayList<TextView>()
    private val gtLabelGeneration=java.util.concurrent.atomic.AtomicLong(0L)''',
'''    private val boxes = ArrayList<TextView>()
    @Volatile private var lastRenderedLabels: List<Overlay.Label> = emptyList()
    private val gtLabelGeneration=java.util.concurrent.atomic.AtomicLong(0L)''')
once(view,
'''            caption?.let(::subtitleStyle)
            boxes.forEach(::hudStyle)
            if (!lastSubtitleValue.isNullOrBlank())
                setSubtitle(lastSubtitleValue,lastSubtitleTop,bottomPx=lastSubtitleBottom)''',
'''            caption?.let(::subtitleStyle)
            // Repaint the source rectangles; hudStyle() alone erases masks.
            setLabels(lastRenderedLabels)
            if (!lastSubtitleValue.isNullOrBlank())
                setSubtitle(lastSubtitleValue,lastSubtitleTop,bottomPx=lastSubtitleBottom)''')
once(view,
'''    fun setLabels(labels:List<Overlay.Label>) {
        val generation=gtLabelGeneration.incrementAndGet()
        val container=root?:return''',
'''    fun setLabels(labels:List<Overlay.Label>) {
        val snapshot=labels.toList()
        lastRenderedLabels=snapshot
        val generation=gtLabelGeneration.incrementAndGet()
        val container=root?:return''')
once(view,'val card=labels.getOrNull(i)','val card=snapshot.getOrNull(i)')
once(view,
'''        root=null;caption=null;boxes.clear()
        lastSubtitleValue=null''',
'''        root=null;caption=null;boxes.clear()
        lastRenderedLabels=emptyList()
        gtLabelGeneration.incrementAndGet()
        lastSubtitleValue=null''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtCleanRegression521Test.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtCleanRegression521Test {
    private fun line(t:String,x:Int,y:Int,w:Int=375)=
        GtAllHud.Line(t,x,y,x+w,y+24)

    @Test fun videoSubtitleWithTwoLinesNeverBecomesGameNotification() {
        assertNull(GtGameNotice.find(listOf(
            line("I don't care what you want anymore.",1050,540),
            line("You can just leave me alone!",1050,575)),1536,690))
        assertNull(GtGameNotice.find(listOf(
            line("What can you give me for this?",1050,540),
            line("I really need your help here.",1050,575)),1536,690))
    }
    @Test fun realMissionNoticeAndInstructionAreStillDetected() {
        val mission=GtGameNotice.find(listOf(
            line("New objective available",1040,545,310),
            line("Meet your contact at the docks.",1040,574,335)),1536,690)
        assertEquals("corner",mission!!.kind)
        val oneLine=GtGameNotice.find(listOf(
            line("Drive to the office slowly.",1080,550,330)),1536,690)
        assertEquals("corner",oneLine!!.kind)
    }
    @Test fun consoleAlertsAreIgnoredWhileNamedGameMessagesWork() {
        assertNull(GtGameNotice.find(listOf(
            line("PS5 sisteminiz kapatilmaya hazırlanıyor.",1020,540,410)),1536,690))
        val message=GtGameNotice.find(listOf(
            line("Moses",316,487,160),
            line("Clients stiffed me when it",220,539,350),
            line("was time to pay up. Trashed",219,571,350),
            line("my shop, too. They wanna...",222,603,350)),1536,690)
        assertEquals("Moses",message!!.title)
    }
    @Test fun selectedColorKeepsSourceAlignedBackdrop() {
        val renderer=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(renderer.contains("setLabels(lastRenderedLabels)"))
        assertTrue(renderer.contains("lastRenderedLabels=snapshot"))
        assertTrue(renderer.contains("val card=snapshot.getOrNull(i)"))
        assertTrue(renderer.contains("tv.setTextColor(style.yaziRengi)"))
        assertTrue(renderer.contains("Color.argb(248,17,24,38)"))
        assertFalse(renderer.contains("boxes.forEach(::hudStyle)"))
    }
    @Test fun allTranslationRegionsAndPreviousCleanUiRemainEnabled() {
        val service=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val activity=java.io.File("src/main/java/com/example/altyazi/MainActivity.kt").readText()
        assertTrue(service.contains("processSubtitle(full)"))
        assertTrue(service.contains("processGameNotice(full,noticeProbe)"))
        assertTrue(service.contains("processMapDetailPanels(full,noticeProbe)"))
        assertTrue(service.contains("SubtitleStyle.yaziRengi(prefs.subtitleColor)"))
        assertTrue(activity.contains("private fun showUiPage(settings:Boolean)"))
        assertFalse(service.contains("gtQuestBoxesOnly"))
    }
}
''',encoding='utf8')

v=build.read_text(encoding='utf8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261225',v,count=1)
if n!=1:raise RuntimeError('Missing versionCode')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
  r'\g<1>versionName = "GameLingoPro-5.2.1-CleanQA"',v,count=1)
if n!=1:raise RuntimeError('Missing versionName')
build.write_text(v,encoding='utf8')
print('5.2.1: source-aligned mask persists through color changes; video captions not game popups')
