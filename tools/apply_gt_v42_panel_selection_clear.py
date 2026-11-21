#!/usr/bin/env python3
"""4.2: selected map text must be cleared when the ORIGINAL heading changes.
Apply after the 4.1 patch to the real GameLingoPro Android source.
"""
from pathlib import Path
import re, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
cap=src/'CaptureService.kt'
det=src/'GtSelectedMapPanel.kt'
overlay=src/'GtExactOverlay.kt'
build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
for p in (cap,det,overlay,build):
    if not p.is_file(): raise RuntimeError('Missing v4.1 original source: '+str(p))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Wrong applicationId')
if 'if(processMapDetailPanels(full))return' not in cap.read_text():
    raise RuntimeError('GameLingoPro 4.1 must run before 4.2')
def once(path,old,new):
    c=path.read_text(encoding='utf-8')
    n=c.count(old)
    if n!=1: raise RuntimeError(f'{path.name}: expected one anchor, found {n}: {old[:90]}')
    path.write_text(c.replace(old,new,1),encoding='utf-8')

# A map can be identified from MAP plus RECENTER when the changing
# screen makes OCR miss BRIEF and PROGRESS. Do NOT fall back to
# the legacy menu pipeline: it can restore an older location translation.
once(det,
'''    fun isMap(lines:List<GtAllHud.Line>,w:Int,h:Int):Boolean =
        w>=100 && h>=100 && lines.count {
            it.top.toFloat()/h<.12f &&
            it.text.lowercase(Locale.ROOT).trim() in tabs
        }>=2''',
'''    fun isMap(lines:List<GtAllHud.Line>,w:Int,h:Int):Boolean {
        if(w<100 || h<100)return false
        val topCount=lines.count {
            it.top.toFloat()/h<.125f &&
            it.text.lowercase(Locale.ROOT).trim() in tabs
        }
        val controls=lines.count { row ->
            row.left.toFloat()/w>.76f && row.top.toFloat()/h>.65f &&
            Regex("(?i)^(?:recenter|2d view|add marker|set destination|exit)\\b")
                .containsMatchIn(row.text.trim())
        }
        return topCount>=2 || (topCount>=1 && controls>=1) || controls>=3
    }''')
# In the screenshot, the translated STARLET MOTEL overlay starts at
# x=.61 of the captured image. It is not a true box heading.
# NINE1NINE starts at x=.54 and must win.
once(det,'''        val maxX=if(right).79f else .42f''',
'''        val maxX=if(right).60f else .34f''')

# Guard the renderer against late UI posts from old translations.
once(overlay,
'''    private val boxes = ArrayList<TextView>()''',
'''    private val boxes = ArrayList<TextView>()
    private val gtLabelGeneration=java.util.concurrent.atomic.AtomicLong(0L)''')
once(overlay,
'''    fun setLabels(labels:List<Overlay.Label>) {
        val container=root?:return
        container.post {
            while(boxes.size<labels.size){''',
'''    fun setLabels(labels:List<Overlay.Label>) {
        val generation=gtLabelGeneration.incrementAndGet()
        val container=root?:return
        container.post {
            if(gtLabelGeneration.get()!=generation || root!==container)return@post
            while(boxes.size<labels.size){''')

once(cap,
'''    private val gtPanelLastAttempt=java.util.concurrent.ConcurrentHashMap<String,Long>()''',
'''    private val gtPanelLastAttempt=java.util.concurrent.ConcurrentHashMap<String,Long>()
    private val gtPanelStateLock=Any()
    private val gtPanelTranslatedTitle=java.util.concurrent.ConcurrentHashMap<String,String>()''')
once(cap,
'''        gtPanelLastAttempt.clear()
        overlay.clearLabels()''',
'''        gtPanelLastAttempt.clear()
        gtPanelTranslatedTitle.clear()
        overlay.clearLabels()''')

# Title of the currently displayed translation must match current OCR title.
once(cap,
'''            val text=gtPanelText[slot]?:return@mapNotNull null
            val geo=gtPanelRects[slot]?:return@mapNotNull null
            if(text.isBlank())null else Overlay.Label(''',
'''            val text=gtPanelText[slot]?:return@mapNotNull null
            val geo=gtPanelRects[slot]?:return@mapNotNull null
            if(gtPanelTranslatedTitle[slot]!=gtPanelKeys[slot] || text.isBlank())
                null else Overlay.Label(''')

once(cap,
'''            if(gtPanelKeys[slot]!=identity) {
                gtPanelJobs.remove(slot)?.cancel()
                gtPanelKeys[slot]=identity
                gtPanelText.remove(slot)
                gtPanelRects.remove(slot)
                gtPanelLastAttempt.remove(slot)
                drawMapDetailPanels()
            }''',
'''            if(gtPanelKeys[slot]!=identity) {
                synchronized(gtPanelStateLock) {
                    val old=gtPanelKeys[slot]
                    gtPanelJobs.remove(slot)?.cancel()
                    gtPanelKeys[slot]=identity
                    gtPanelText.remove(slot)
                    gtPanelTranslatedTitle.remove(slot)
                    gtPanelRects.remove(slot)
                    gtPanelLastAttempt.remove(slot)
                    drawMapDetailPanels()
                    log("HARİTA SEÇİMİ DEĞİŞTİ: "+(old?:"boş")+" -> "+identity)
                }
            }''')

once(cap,
'''                if(missed>=2) {
                    gtPanelJobs.remove(slot)?.cancel()
                    gtPanelKeys.remove(slot)
                    gtPanelText.remove(slot)
                    gtPanelRects.remove(slot)
                    drawMapDetailPanels()
                }''',
'''                if(missed>=2) {
                    synchronized(gtPanelStateLock) {
                        gtPanelJobs.remove(slot)?.cancel()
                        gtPanelKeys.remove(slot)
                        gtPanelText.remove(slot)
                        gtPanelTranslatedTitle.remove(slot)
                        gtPanelRects.remove(slot)
                        drawMapDetailPanels()
                    }
                }''')

once(cap,
'''            if(cached!=null) {
                gtPanelText[slot]=cached
                drawMapDetailPanels()
                continue
            }''',
'''            if(cached!=null) {
                synchronized(gtPanelStateLock) {
                    if(gtPanelKeys[slot]==identity) {
                        gtPanelText[slot]=cached
                        gtPanelTranslatedTitle[slot]=identity
                        drawMapDetailPanels()
                    }
                }
                continue
            }''')

once(cap,
'''                if(!translated.isNullOrBlank() &&
                   !translated.equals(source,ignoreCase=true) &&
                   gtMapPanelMode && gtPanelKeys[slot]==identity) {
                    gtPanelCache[cacheKey]=translated
                    gtPanelText[slot]=translated
                    drawMapDetailPanels()
                    log("HARİTA KUTUSU ÇEVRİLDİ: "+slot+" / "+panel.title)
                } else if(gtMapPanelMode && gtPanelKeys[slot]==identity) {
                    log("HARİTA KUTUSU ÇEVRİLEMEDİ: "+slot+" / "+panel.title)
                }''',
'''                synchronized(gtPanelStateLock) {
                    if(!translated.isNullOrBlank() &&
                       !translated.equals(source,ignoreCase=true) &&
                       gtMapPanelMode && gtPanelKeys[slot]==identity) {
                        gtPanelCache[cacheKey]=translated
                        gtPanelText[slot]=translated
                        gtPanelTranslatedTitle[slot]=identity
                        drawMapDetailPanels()
                        log("HARİTA KUTUSU ÇEVRİLDİ: "+slot+" / "+panel.title)
                    } else if(gtMapPanelMode && gtPanelKeys[slot]==identity) {
                        log("HARİTA KUTUSU ÇEVRİLEMEDİ: "+slot+" / "+panel.title)
                    }
                }''')

# On the first confirmed exit frame clear, never submit the same
# frame to legacy map processing, which might re-publish obsolete labels.
once(cap,
'''            gtMapPanelMode=false
            gtMapMisses=0
            resetMapDetailPanels()
            return false''',
'''            gtMapPanelMode=false
            gtMapMisses=0
            resetMapDetailPanels()
            return true''')

once(cap,
'''        val isMap=GtSelectedMapPanel.isMap(lines,width,height)''',
'''        val isMap=GtSelectedMapPanel.isMap(lines,width,height) ||
            (gtMapPanelMode && lines.any { row ->
                row.top.toFloat()/height<.125f &&
                row.text.trim().lowercase(java.util.Locale.ROOT) in
                    setOf("map","brief","progress")
            })''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtMapSelection42Test.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtMapSelection42Test {
    private fun line(t:String,x:Int,y:Int,w:Int=200,h:Int=20)=
        GtAllHud.Line(t,x,y,x+w,y+h)
    private val map=listOf(line("MAP",735,25),line("RECENTER",1260,522))
    @Test fun mapRemainsDetectedWithSingleTabAndMapControl() {
        assertTrue(GtSelectedMapPanel.isMap(map,1536,690))
        assertFalse(GtSelectedMapPanel.isMap(listOf(line("MAP",735,25)),1536,690))
    }
    @Test fun previousStarletMotelOverlayCannotReplaceNine1nineTitle() {
        val rows=map+listOf(line("NINE1NINE",826,271,170),
            line("STARLET MOTEL",936,285,181),
            line("Vice City's very own ultra nightclub-strip",828,303,300),
            line("club hybrid where luxury hospitality is",827,332,300))
        val panel=GtSelectedMapPanel.panels(rows,1536,690).first()
        assertEquals("NINE1NINE",panel.title)
        assertEquals("right",panel.slot)
        assertFalse(panel.identity.contains("starlet"))
    }
    @Test fun lateUiPostsAndOldTitleTextAreGuarded() {
        val service=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val view=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(service.contains("gtPanelTranslatedTitle[slot]!=gtPanelKeys[slot]"))
        assertTrue(service.contains("HARİTA SEÇİMİ DEĞİŞTİ"))
        assertTrue(view.contains("gtLabelGeneration.get()!=generation"))
    }
}
''',encoding='utf-8')

v=build.read_text(encoding='utf-8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261215',v,count=1)
if n!=1:raise RuntimeError('versionCode missing')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-4.2-SelectionClears"',v,count=1)
if n!=1:raise RuntimeError('versionName missing')
build.write_text(v,encoding='utf-8')
print('4.2: clear old map translation when selected title changes')
