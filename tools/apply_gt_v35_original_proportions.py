#!/usr/bin/env python3
"""GameLingoPro 3.5: keep native GT HUD labels tied to OCR source geometry,
and never delete them only because their fixed timer elapsed.
Apply AFTER apply_gt_v34_source_geometry.py to the original Kotlin app.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
src = root/'app/src/main/java/com/example/altyazi'
geometry = src/'GtSourceBox.kt'
renderer = src/'GtExactOverlay.kt'
service = src/'CaptureService.kt'
unit = root/'app/src/test/java/com/example/altyazi/GtOriginalBoundsTest.kt'
build = root/'app/build.gradle.kts'
for p in (geometry, renderer, service, unit, build):
    if not p.is_file():
        raise RuntimeError('Missing previous GameLingoPro v3.4 file: '+str(p))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Wrong Android package, patch refused')
if 'overlay = GtExactOverlay(this)' not in service.read_text():
    raise RuntimeError('Native GT renderer is not active')

def replace_once(path, before, after):
    data = path.read_text(encoding='utf-8')
    count = data.count(before)
    if count != 1:
        raise RuntimeError(f'{path.name}: expected 1 source anchor, found {count}: {before[:90]}')
    path.write_text(data.replace(before, after, 1), encoding='utf-8')

# Both dimensions are drawn from the source OCR rectangle, not a preset
# percentage of display width and not the optional caption-size slider.
replace_once(geometry,
'''    fun width(source:Int,viewport:Int,padding:Int):Int =
        (source.coerceAtLeast(1)+padding.coerceAtLeast(0))
            .coerceIn(1,(viewport*0.47f).toInt().coerceAtLeast(1))''',
'''    fun width(source:Int,viewport:Int,padding:Int):Int =
        (source.coerceAtLeast(1)+padding.coerceAtLeast(0))
            .coerceIn(1,viewport.coerceAtLeast(1))''')
replace_once(geometry,
'''        return (rowPx/1.13f).coerceIn(6f*density.coerceAtLeast(1f),
            16f*density.coerceAtLeast(1f))''',
'''        // OCR knows the actual source glyph-row height. Never inflate
        // a small label to an arbitrary HUD size, or cap a large one to 16dp.
        return (rowPx/1.13f).coerceAtLeast(6f*density.coerceAtLeast(1f))''')
replace_once(geometry,
'''    fun hold(misses:Int,sinceSeenMs:Long):Boolean =
        misses<5 || sinceSeenMs<120000L''',
'''    // A blank OCR sample is NOT proof that the English source disappeared.
    // A translation stays in its source rect until the app observes a new
    // source in that rect or a capture/scene reset explicitly clears labels.
    fun hold(misses:Int,sinceSeenMs:Long):Boolean =
        misses<2''')

# Do not let failure to re-read an opaque translation window clear a visible
# caption. This applies to fixed-location HUD and menu text.
replace_once(service,
'''            gtHudMissingScans++
            if(GtSourceBox.hold(gtHudMissingScans,''',
'''            gtHudMissingScans=(gtHudMissingScans+1).coerceAtMost(100000)
            if(GtSourceBox.hold(gtHudMissingScans,''')
replace_once(service,
'''        // Preserve readable translations through occasional partial/blank
        // OCR results, but replace a previous card when new source takes over
        // the same rectangle. Stale cards expire only after 120 seconds.
        gtHeldLabels.removeAll{held->hudNow-held.lastSeenMs>120000L}''',
'''        // Only currently observed English labels are displayed.
        gtHeldLabels.clear()''')

# Dialogue captions use a separate OCR pipeline. An OCR blank is an
# inconclusive read (especially if the floating caption covers the source),
# not proof the English has left the screen. Preserve the translated line
# until a new source or an explicit capture reset is observed.
replace_once(service,
'''        if(GtObjectiveLine.matches(text)) {
            // HUD OCR will draw this at its source rectangle, never as a
            // large bottom-centred speech subtitle.
            if(GtObjectiveLine.matches(shownSource)) {
                shownSource=""
                showSubtitle(null)
            }
            return
        }

        if (text.isEmpty()) {''',
'''        if(GtObjectiveLine.matches(text)) {
            // HUD OCR will draw this at its source rectangle, never as a
            // large bottom-centred speech subtitle.
            if(GtObjectiveLine.matches(shownSource)) {
                shownSource=""
                showSubtitle(null)
            }
            return
        }

        // Keep the caption when an OCR scan misses visible English;
        // never dismiss just because a fixed time limit has elapsed.
        if (text.isEmpty() && shownSource.isNotBlank() && !gtUncoveredScan) return
        if (text.isEmpty()) {''')

# If MediaProjection temporarily returns no frame, there is no reliable
# observation that the English source vanished. Preserve the caption; the
# capture-stop/rotation path remains responsible for explicit cleanup.
replace_once(service,
'''                        if (shownSource.isNotEmpty() && lastFrameMs > 0 && nowMs - lastFrameMs > STALE_MS) {
                            shownSource = ""
                            candidate = ""
                            candidateSeen = 0
                            translatingFor = ""
                            subtitleGeneration.invalidate()
                            showSubtitle(null)
                            if (!staleWarned) {
                                staleWarned = true
                                log("GÖRÜNTÜ GELMİYOR: ${STALE_MS / 1000} sn'dir yeni kare yok, eski çeviri kaldırıldı.")
                            }
                        }''',
'''                        if (shownSource.isNotEmpty() && lastFrameMs > 0 && nowMs - lastFrameMs > STALE_MS) {
                            // Stop covering the game when source is unavailable.
                            shownSource=""
                            translatingFor=""
                            candidate=""
                            candidateSeen=0
                            subtitleGeneration.invalidate()
                            showSubtitle(null)
                            gtHeldLabels.clear()
                            lastHudLabels=emptyList()
                            overlay.clearLabels()
                            if (!staleWarned) {
                                staleWarned = true
                                log("GÖRÜNTÜ GELMİYOR: eski çeviri temizlendi.")
                            }
                        }''')

# Text fitting uses actual OCR bounds. For translations that contain more
# letters than English, scale down enough to fit rather than enlarge their
# background or assign the same 12/28sp size to every source label.
replace_once(renderer,
'''                val minPx=dp(6).toFloat()
                var fontPx=GtSourceBox.fontPx(originalHeight,card.sourceLines,density)''',
'''                var fontPx=GtSourceBox.fontPx(originalHeight,card.sourceLines,density)
                val minPx=(fontPx*.42f).coerceAtLeast(dp(4).toFloat())''')
replace_once(renderer,
'''                val sourceH=(originalHeight+dp(7)).coerceAtLeast(dp(17))''',
'''                val sourceH=(originalHeight+dp(4)).coerceAtLeast(dp(12))''')
replace_once(renderer,
'''                // Fit translated text WITHIN the source rectangle before
                // permitting any expansion; no forced 28sp HUD labels.
                for(n in 0 until 26) {''',
'''                // Preserve the original OCR font as the MAXIMUM. Shrink
                // only if the translated sentence needs more lines.
                tv.maxLines=Int.MAX_VALUE
                tv.ellipsize=null
                for(n in 0 until 70) {''')
replace_once(renderer,
'''                    fontPx=(fontPx-.7f).coerceAtLeast(minPx)''',
'''                    fontPx=(fontPx-.5f).coerceAtLeast(minPx)''')

# Unit tests verify original-width placement and indefinite caption retention
# through OCR misses; no device behavior is claimed until APK is field tested.
replace_once(unit,
'''        assertEquals(96,GtSourceBox.width(88,2142,8))''',
'''        assertEquals(96,GtSourceBox.width(88,2142,8))
        assertEquals(1108,GtSourceBox.width(1100,1536,8))
        assertEquals(1536,GtSourceBox.width(2000,1536,8))''')
replace_once(unit,
'''        assertFalse(GtSourceBox.hold(20,121000L))''',
'''        assertFalse(GtSourceBox.hold(20,121000L))
        assertFalse(GtSourceBox.hold(1200,3600000L))''')


# A mission objective is not a spoken subtitle. Clear the previous
# large dialogue overlay, regardless of what that dialogue previously said.
replace_once(service,
'''            if(GtObjectiveLine.matches(shownSource)) {
                shownSource=""
                showSubtitle(null)
            }''',
'''            if(shownSource.isNotBlank()) {
                shownSource=""
                translatingFor=""
                subtitleGeneration.invalidate()
                showSubtitle(null)
            }''')

# The game's source is hidden by our opaque Turkish overlay. Read English in
# a fresh uncovered capture, so text is cleared by disappearance, not by TTL.
replace_once(service,'''    private var gtHudMissingScans=0''',
'''    private var gtHudMissingScans=0
    private var gtUncoveredScan=false''')
replace_once(service,
'''                    val captureStart = android.os.SystemClock.elapsedRealtime()
                    val full = grabFull()''',
'''                    val uncoverSource = !isTv && cycle % 2L == 0L &&
                        (shownSource.isNotBlank() || lastHudLabels.isNotEmpty())
                    if(uncoverSource) {
                        overlay.setSubtitle(null, subtitleAnchorPx)
                        overlay.clearLabels()
                        delay(55L)
                    }
                    gtUncoveredScan=uncoverSource
                    val captureStart = android.os.SystemClock.elapsedRealtime()
                    val full = grabFull()''')
replace_once(service,
'''                    if (full == null) {
                        diagNoFrame++''',
'''                    if (full == null) {
                        gtUncoveredScan=false
                        if(uncoverSource && shownValue.isNotBlank())showSubtitle(shownValue)
                        if(uncoverSource && lastHudLabels.isNotEmpty())
                            overlay.setLabels(lastHudLabels)
                        diagNoFrame++''')
replace_once(service,
'''                    processSubtitle(full)

                    if (!isTv''',
'''                    try {
                        processSubtitle(full)
                    } finally {
                        gtUncoveredScan=false
                        if(uncoverSource && shownValue.isNotBlank())showSubtitle(shownValue)
                        if(uncoverSource && lastHudLabels.isNotEmpty())
                            overlay.setLabels(lastHudLabels)
                    }

                    if (!isTv''')
replace_once(service,
'''        if (!subtitleReadGuard299.shouldOcr(sampleUnchanged, candidateSeen == 1, checkMs)) {''',
'''        if (!gtUncoveredScan &&
            !subtitleReadGuard299.shouldOcr(sampleUnchanged, candidateSeen == 1, checkMs)) {''')
replace_once(service,
'''            if (emptyFrames >= 6 && shownSource.isNotEmpty() && yeterinceDurdu) {''',
'''            if (gtUncoveredScan && emptyFrames >= 2 && shownSource.isNotEmpty()) {''')
replace_once(service,'''            fullMenuDetected = GtMenuUi.isGameMenu(candidates)''',
'''            fullMenuDetected = GtMenuUi.isGameMenu(candidates)
            if(fullMenuDetected && shownSource.isNotBlank()) {
                shownSource=""
                translatingFor=""
                subtitleGeneration.invalidate()
                showSubtitle(null)
            }''')
replace_once(service,
'''        val labels=ArrayList<Overlay.Label>()
        var newCalls=0
        for(card in cards){''',
'''        val labels=ArrayList<Overlay.Label>()
        var newCalls=0
        val prioritizedCards=if(fullMenuDetected)
            cards.sortedByDescending { item ->
                item.left.toFloat()>smallWidthForHud(full.width)*.48f &&
                item.top.toFloat()>smallHeightForHud(full.width,full.height)*.22f &&
                item.top.toFloat()<smallHeightForHud(full.width,full.height)*.75f
            }
        else cards
        for(card in prioritizedCards){''')
replace_once(service,
'''                if(fullMenuDetected && newCalls>=5)continue''',
'''                if(fullMenuDetected && newCalls>=8)continue''')
replace_once(unit,
'''        assertTrue(GtSourceBox.hold(3,5500L))''',
'''        assertFalse(GtSourceBox.hold(3,5500L))''')
replace_once(unit,
'''        assertTrue(GtSourceBox.hold(50,30000L))''',
'''        assertFalse(GtSourceBox.hold(50,30000L))''')
tests.mkdir(parents=True,exist_ok=True)
(tests/'GtVisibleOnlyTest.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtVisibleOnlyTest {
 @Test fun previousMenuTextCannotStayForever() {
  assertTrue(GtSourceBox.hold(1,600L))
  assertFalse(GtSourceBox.hold(2,900L))
  assertFalse(GtSourceBox.hold(50,120000L))
 }
 @Test fun underlyingEnglishIsRechecked() {
  val s=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
  assertTrue(s.contains("gtUncoveredScan"))
  assertTrue(s.contains("overlay.setSubtitle(null, subtitleAnchorPx)"))
  assertTrue(s.contains("prioritizedCards"))
 }
}
''',encoding='utf-8')

s = build.read_text(encoding='utf-8')
s, n = re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
               r'\g<1>versionCode = 20261211', s, count=1)
if n != 1: raise RuntimeError('versionCode missing')
s, n = re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
               r'\g<1>versionName = "GameLingoPro-3.8-VisibleOnly-RightPanel"',s,count=1)
if n != 1: raise RuntimeError('versionName missing')
build.write_text(s,encoding='utf-8')
print('GameLingoPro 3.5: source OCR font and box; no HUD/menu timeout while OCR misses')
