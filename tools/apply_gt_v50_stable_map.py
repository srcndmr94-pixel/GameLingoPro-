#!/usr/bin/env python3
"""5.0 map: clear stale translations on selection/body changes, hold geometry
until stable; retain entire 4.9 translation chain, captions and colors.
"""
from pathlib import Path
import sys,re
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt";build=root/"app/build.gradle.kts";tests=root/"app/src/test/java/com/example/altyazi"
for f in (cap,build,src/"GtSelectedMapPanel.kt",src/"GtExactOverlay.kt"):
    if not f.exists():raise RuntimeError(str(f)+" missing")
assert "gtQuestBoxesOnly" not in cap.read_text()
assert "GameLingoPro-4.9" in build.read_text()
def once(file,a,b):
    s=file.read_text(encoding="utf8");count=s.count(a)
    if count!=1:raise RuntimeError(f"{file.name}: anchor count={count}: {a[:85]}")
    file.write_text(s.replace(a,b,1),encoding="utf8")

(src/"GtMapMotion50.kt").write_text(r'''package com.example.altyazi
import java.util.Locale
import kotlin.math.abs
import kotlin.math.max
/** Screen-relative map stability. Treat OCR flicker as the same mission. */
internal object GtMapMotion50 {
    fun near(ax:Int,ay:Int,bx:Int,by:Int,w:Int,h:Int):Boolean =
        abs(ax-bx) <= max(8,(w*.013f).toInt()) &&
        abs(ay-by) <= max(7,(h*.017f).toInt())
    fun newBody(old:String,next:String):Boolean {
        val a=old.lowercase(Locale.ROOT).replace(Regex("""[^\p{L}\p{N} ]""")," ")
            .split(Regex("""\s+""")).filter{it.length>2}
        val b=next.lowercase(Locale.ROOT).replace(Regex("""[^\p{L}\p{N} ]""")," ")
            .split(Regex("""\s+""")).filter{it.length>2}
        if(a.size<3 || b.size<3)return false
        val similar=b.count{it in a}.toFloat()/max(a.size,b.size).coerceAtLeast(1)
        return similar<.65f
    }
    fun settled(firstMs:Long,nowMs:Long):Boolean = nowMs-firstMs>=210L
}
''',encoding="utf8")

once(cap,
'''    private val gtPanelStateLock=Any()''',
'''    private val gtPanelStateLock=Any()
    private val gtPanelAnchors=java.util.concurrent.ConcurrentHashMap<String,Overlay.Label>()
    private val gtPanelPending=java.util.concurrent.ConcurrentHashMap<String,Overlay.Label>()
    private val gtPanelPendingSince=java.util.concurrent.ConcurrentHashMap<String,Long>()
    private val gtPanelSources=java.util.concurrent.ConcurrentHashMap<String,String>()''')
once(cap,
'''        gtPanelRects.clear()
        gtPanelMisses.clear()
        gtPanelLastAttempt.clear()
        gtPanelTranslatedTitle.clear()''',
'''        gtPanelRects.clear()
        gtPanelMisses.clear()
        gtPanelLastAttempt.clear()
        gtPanelAnchors.clear()
        gtPanelPending.clear()
        gtPanelPendingSince.clear()
        gtPanelSources.clear()
        gtPanelTranslatedTitle.clear()''')
once(cap,
'''                        gtPanelRects.remove(slot)
                        drawMapDetailPanels()
                    }
                }
                continue''',
'''                        gtPanelRects.remove(slot)
                        gtPanelAnchors.remove(slot)
                        gtPanelPending.remove(slot)
                        gtPanelPendingSince.remove(slot)
                        gtPanelSources.remove(slot)
                        drawMapDetailPanels()
                    }
                }
                continue''')
once(cap,
'''                    gtPanelRects.remove(slot)
                    gtPanelLastAttempt.remove(slot)
                    drawMapDetailPanels()''',
'''                    gtPanelRects.remove(slot)
                    gtPanelAnchors.remove(slot)
                    gtPanelPending.remove(slot)
                    gtPanelPendingSince.remove(slot)
                    gtPanelSources.remove(slot)
                    gtPanelLastAttempt.remove(slot)
                    drawMapDetailPanels()''')
once(cap,
'''            if(panel.body.isNotBlank()) {
                gtPanelRects[slot]=Overlay.Label("",
                    panel.left,panel.top,panel.right,panel.bottom,panel.rows,
                    frameWidth=width,frameHeight=height,fitSourceBox=true)
            }
            val heading=panel.title.trim()
            gtTitleRect[slot]=Overlay.Label("",panel.titleLeft,panel.titleTop,
                panel.titleRight,panel.titleBottom,1,
                frameWidth=width,frameHeight=height,fitSourceBox=true)''',
'''            // Keep exactly one anchor during OCR jitter. On a moving map
            // selection, immediately hide the old overlay. Show the new
            // translation only after its position has settled for 210 ms.
            val nowMap=android.os.SystemClock.elapsedRealtime()
            val fresh=Overlay.Label("",panel.titleLeft,panel.titleTop,
                panel.titleRight,panel.titleBottom,1,
                frameWidth=width,frameHeight=height,fitSourceBox=true)
            val anchored=gtPanelAnchors[slot]
            if(anchored==null || !GtMapMotion50.near(anchored.x,anchored.y,
                    fresh.x,fresh.y,width,height)) {
                val pending=gtPanelPending[slot]
                if(pending==null || !GtMapMotion50.near(pending.x,pending.y,
                        fresh.x,fresh.y,width,height)) {
                    gtPanelPending[slot]=fresh
                    gtPanelPendingSince[slot]=nowMap
                    if(anchored!=null) {
                        gtPanelAnchors.remove(slot)
                        gtPanelJobs.remove(slot)?.cancel()
                        gtTitleJobs.remove(slot)?.cancel()
                        gtPanelText.remove(slot)
                        gtPanelTranslatedTitle.remove(slot)
                        gtTitleText.remove(slot)
                        gtTitleDone.remove(slot)
                        gtPanelRects.remove(slot)
                        gtTitleRect.remove(slot)
                        drawMapDetailPanels()
                    }
                    continue
                }
                if(!GtMapMotion50.settled(gtPanelPendingSince[slot]?:nowMap,nowMap))
                    continue
                gtPanelAnchors[slot]=fresh
                gtPanelPending.remove(slot)
                gtPanelPendingSince.remove(slot)
            }
            if(panel.body.isNotBlank() && gtPanelRects[slot]==null) {
                gtPanelRects[slot]=Overlay.Label("",
                    panel.left,panel.top,panel.right,panel.bottom,panel.rows,
                    frameWidth=width,frameHeight=height,fitSourceBox=true)
            }
            val heading=panel.title.trim()
            if(gtTitleRect[slot]==null)
                gtTitleRect[slot]=gtPanelAnchors[slot]?:fresh''')
once(cap,
'''            val source=panel.body.trim()
            if(source.isBlank())continue
            if(gtPanelText[slot]!=null)continue''',
'''            val source=panel.body.trim()
            if(source.isBlank())continue
            val priorSource=gtPanelSources[slot]
            if(priorSource==null)gtPanelSources[slot]=source
            else if(GtMapMotion50.newBody(priorSource,source)) {
                // Header can stay identical while the selected mission body
                // changes. Never reuse the old translated paragraph.
                gtPanelSources[slot]=source
                gtPanelJobs.remove(slot)?.cancel()
                gtPanelText.remove(slot)
                gtPanelTranslatedTitle.remove(slot)
                gtPanelLastAttempt.remove(slot)
                gtPanelRects[slot]=Overlay.Label("",
                    panel.left,panel.top,panel.right,panel.bottom,panel.rows,
                    frameWidth=width,frameHeight=height,fitSourceBox=true)
                drawMapDetailPanels()
                log("HARİTA METNİ DEĞİŞTİ: "+slot)
            }
            if(gtPanelText[slot]!=null)continue''')
once(cap,
'''                       gtMapPanelMode && gtPanelKeys[slot]==identity) {
                        gtPanelCache[cacheKey]=translated''',
'''                       gtMapPanelMode && gtPanelKeys[slot]==identity &&
                       gtPanelSources[slot]==(gtPanelSources[slot]?:source) &&
                       !GtMapMotion50.newBody(gtPanelSources[slot]?:source,source)) {
                        gtPanelCache[cacheKey]=translated''')

tests.mkdir(parents=True,exist_ok=True)
(tests/"GtMapMotion50Test.kt").write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtMapMotion50Test {
    @Test fun tinyOcrJitterIsIgnoredAndMovingCardsAreNot() {
        assertTrue(GtMapMotion50.near(840,252,846,257,1536,690))
        assertFalse(GtMapMotion50.near(840,252,970,300,1536,690))
        assertFalse(GtMapMotion50.settled(100L,245L))
        assertTrue(GtMapMotion50.settled(100L,310L))
    }
    @Test fun newlySelectedTextWithSameHeaderInvalidatesOldBody() {
        assertFalse(GtMapMotion50.newBody(
            "Nightclub with luxury hospitality and beautiful views.",
            "Nightclub with luxury hospitality and beautiful view"))
        assertTrue(GtMapMotion50.newBody(
            "Nightclub with luxury hospitality and beautiful views.",
            "Take the car to the dock and meet the gang outside"))
    }
    @Test fun liveSelectionUsesMapStabilityButKeepsAllTranslations() {
        val s=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(s.contains("gtPanelSources[slot]=source"))
        assertTrue(s.contains("gtPanelPendingSince[slot]=nowMap"))
        assertTrue(s.contains("HARİTA METNİ DEĞİŞTİ"))
        assertTrue(s.contains("processSubtitle(full)"))
        assertTrue(s.contains("processGameNotice(full,noticeProbe)"))
        assertFalse(s.contains("gtQuestBoxesOnly"))
    }
}
''',encoding="utf8")
print("5.0 map selections: immediate invalidation, geometry debouncing, source comparison")
