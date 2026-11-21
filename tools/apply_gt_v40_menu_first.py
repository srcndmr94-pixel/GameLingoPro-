#!/usr/bin/env python3
"""GameLingoPro v4.0: publish each completed menu translation immediately.

Based only on the verified v3.9 generated Kotlin source. The original app,
GameTranslator 1.8.49, OCR geometry and previous visual preferences remain.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
tests=root/'app/src/test/java/com/example/altyazi'
cap=src/'CaptureService.kt'
build=root/'app/build.gradle.kts'
for f in (cap, build, src/'GtMenuUi.kt', src/'GtAllHud.kt'):
    if not f.is_file(): raise RuntimeError(f'Expected 3.9 source missing: {f}')
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Refusing changes outside original GameLingoPro')
if 'overlay = GtExactOverlay(this)' not in cap.read_text():
    raise RuntimeError('GT renderer not active')

def once(file,before,after):
    data=file.read_text(encoding='utf8')
    count=data.count(before)
    if count != 1:
        raise RuntimeError(f'{file.name}: source does not match verified v3.9: count={count}, anchor={before[:80]!r}')
    file.write_text(data.replace(before,after,1),encoding='utf8')

(src/'GtMenuPriority.kt').write_text(r'''package com.example.altyazi

/** GameTranslator menu priority: focus on the panel the player is reading. */
internal object GtMenuPriority {
    fun score(card:GtAllHud.Card,width:Float,height:Float):Int {
        val w=width.coerceAtLeast(1f)
        val h=height.coerceAtLeast(1f)
        val x=card.left/w
        val y=card.top/h
        val panel=(x in .46f.. .81f && y in .22f.. .73f)
        val mission=(x in .15f.. .40f && y in .08f.. .40f)
        val paragraph=card.sourceLines>=2 || card.text.length>=45
        return (if(panel)1000 else 0) + (if(mission)600 else 0) +
            (if(paragraph)450 else 0) + card.text.length.coerceAtMost(130)
    }
}
''',encoding='utf8')

# Text in the highlighted (right) location-information box must go before map
# place names and controller shortcuts, even if its OCR line comes later.
once(cap,
'''        val orderedCards=if(fullMenuDetected)
            cards.sortedByDescending { (it.zone=="menu-right" || it.zone=="menu-panel") &&
                it.left > smallWidthForHud(full.width)*.45f }
        else cards''',
'''        val orderedCards=if(fullMenuDetected)
            cards.sortedByDescending { card -> GtMenuPriority.score(card,
                smallWidthForHud(full.width),
                smallHeightForHud(full.width,full.height)) }
        else cards''')

# The old code made up to EIGHT synchronous menu engine requests, then
# finally drew the whole result. It could leave the phone apparently idle
# for tens of seconds, especially the first time a menu opened.
once(cap,
'''                if(fullMenuDetected && newCalls>=8)continue
                newCalls++
                translated=if(fullMenuDetected)
                    GtMenuUi.localized(source) ?: translateMenuText(source)?.trim()
                    else translateMenuText(source)?.trim()''',
'''                val direct=if(fullMenuDetected) GtMenuUi.localized(source) else null
                translated=if(direct!=null)direct else {
                    // No request for known menu controls; limit slow calls
                    // per pass so new OCR frames are picked up quickly.
                    if(fullMenuDetected && newCalls>=3)continue
                    newCalls++
                    kotlinx.coroutines.withTimeoutOrNull(5000L) {
                        translateMenuText(source)
                    }?.trim()
                }''')

# Publish successful translations as they arrive, NOT only after the final
# card. This keeps the original overlay/geometry; no extra floating layer.
once(cap,
'''            labels.add(Overlay.Label(translated,x,y,right,bottom,card.sourceLines))
            displayed.add(normalize(translated))''',
'''            labels.add(Overlay.Label(translated,x,y,right,bottom,card.sourceLines))
            displayed.add(normalize(translated))
            if(fullMenuDetected) {
                // First translated panel is shown without waiting for the
                // other map/place labels or future translation calls.
                val ready=labels.toList()
                overlay.setLabels(ready)
                lastHudLabels=ready
                PhoneBridgeService.publishHud(ready,screenWidth,screenHeight)
            }''')

# Keep the cached-field tests and the single active renderer unchanged.
tests.mkdir(parents=True,exist_ok=True)
(tests/'GtMenuPriorityTest.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtMenuPriorityTest {
    @Test fun rightInformationBodyBeatsMapPlaceNames() {
        val info=GtAllHud.Card("menu-panel",
            "Vice City's very own ultra nightclub-strip club hybrid where luxury hospitality is delivered to private VIP lounges.",
            820,285,1130,400,5)
        val place=GtAllHud.Card("menu-panel","Atlantic Ocean",
            1200,250,1340,275,1)
        assertTrue(GtMenuPriority.score(info,1536f,690f)>
            GtMenuPriority.score(place,1536f,690f))
    }
    @Test fun primaryMissionIsHigherPriorityThanMapLabels() {
        val mission=GtAllHud.Card("menu-left",
            "Vicki said a mechanic named Moses could set you up with a ride.",
            260,140,573,205,3)
        val label=GtAllHud.Card("menu-panel","Catalan Bay",915,517,1080,540,1)
        assertTrue(GtMenuPriority.score(mission,1536f,690f)>
            GtMenuPriority.score(label,1536f,690f))
    }
    @Test fun translationOutputIsIncrementalInSingleOverlay() {
        val s=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(s.contains("GtMenuPriority.score(card"))
        assertTrue(s.contains("if(fullMenuDetected) {\n                // First translated panel"))
        assertTrue(s.contains("if(fullMenuDetected && newCalls>=3)continue"))
        assertTrue(s.contains("overlay = GtExactOverlay(this)"))
    }
}
''',encoding='utf8')

version=build.read_text(encoding='utf8')
version,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261213',version,count=1)
if n!=1:raise RuntimeError('versionCode missing')
version,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-4.0-GT-FastMenu"',version,count=1)
if n!=1:raise RuntimeError('versionName missing')
build.write_text(version,encoding='utf8')
print('GameLingoPro 4.0: prioritized panels, incremental draw, max 3 timed translation attempts')
