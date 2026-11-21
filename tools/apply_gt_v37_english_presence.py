#!/usr/bin/env python3
"""GameLingoPro 3.7: translate ONLY while original English text remains visible.
Apply AFTER v3.5. Do not turn on any permanent subtitle HUD retention.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
s=root/'app/src/main/java/com/example/altyazi'
cap=s/'CaptureService.kt'
geo=s/'GtSourceBox.kt'
build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
for f in (cap,geo,build,tests/'GtOriginalBoundsTest.kt'):
    if not f.exists():raise RuntimeError('Missing expected GameLingoPro 3.5 original source: '+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Not GameLingoPro')
def change(file,before,after):
    t=file.read_text(encoding='utf8')
    n=t.count(before)
    if n!=1:raise RuntimeError(f'{file.name}: wrong anchor count {n}: {before[:75]!r}')
    file.write_text(t.replace(before,after,1),encoding='utf8')

(s/'GtEnglishPresence.kt').write_text('''package com.example.altyazi

/** OCR probes check source presence without guessing its duration. */
internal object GtEnglishPresence {
    const val INTERVAL_MS=650L
    const val SETTLE_MS=65L
    fun needsCheck(now:Long,last:Long,source:String):Boolean =
        source.isNotBlank() && now-last>=INTERVAL_MS
    fun nextMissing(sourceVisible:Boolean,previous:Int):Int =
        if(sourceVisible)0 else (previous+1).coerceAtMost(2)
    fun remove(missing:Int):Boolean = missing>=2
}
''',encoding='utf8')

# Remove the unbounded v3.5 hold policy (cause of persistent HUD labels).
change(geo,
'''    // A blank OCR sample is NOT proof that the English source disappeared.
    // A translation stays in its source rect until the app observes a new
    // source in that rect or a capture/scene reset explicitly clears labels.
    fun hold(misses:Int,sinceSeenMs:Long):Boolean =
        misses >= 0 && sinceSeenMs >= 0L''',
'''    // Brief uncertainty only, never retain a menu label indefinitely.
    fun hold(misses:Int,sinceSeenMs:Long):Boolean =
        misses<2 && sinceSeenMs<1400L''')
change(cap,
'''        // Partial/blank OCR cannot prove that English was removed. Hold
        // previous regions; replacing their source is handled below by
        // GtSourceBox.nearby. A capture reset clears all regions explicitly.''',
'''        // The last English region is absent: old labels must not accumulate.
        gtHeldLabels.removeAll{held->hudNow-held.lastSeenMs>1800L}''')
change(cap,
'''    private var gtHudMissingScans=0''',
'''    private var gtHudMissingScans=0
    private var gtEnglishProbe=false
    private var gtEnglishLastProbe=0L
    private var gtEnglishMissing=0
    private var gtHudLastProbe=0L''')
change(cap,
'''                        gtHudLastConfirmedAtMs=0L''',
'''                        gtHudLastConfirmedAtMs=0L
                        gtEnglishProbe=false
                        gtEnglishLastProbe=0L
                        gtEnglishMissing=0
                        gtHudLastProbe=0L''')
# Temporarily hide our overlay to inspect real English underneath it.
# This is essential when the overlay sits exactly ON the English letters.
change(cap,
'''                    val captureStart = android.os.SystemClock.elapsedRealtime()
                    val full = grabFull()''',
'''                    val englishSource=if(shownSource.isNotBlank())shownSource else translatingFor
                    val checkEnglish=GtEnglishPresence.needsCheck(
                        nowMs,gtEnglishLastProbe,englishSource)
                    val checkHud=lastHudLabels.isNotEmpty() &&
                        nowMs-gtHudLastProbe>=GtEnglishPresence.INTERVAL_MS
                    if(checkEnglish) {
                        gtEnglishLastProbe=nowMs
                        gtEnglishProbe=true
                        overlay.hideForNewSubtitle()
                    }
                    if(checkHud) {
                        gtHudLastProbe=nowMs
                        overlay.clearLabels()
                    }
                    if(checkEnglish||checkHud)delay(GtEnglishPresence.SETTLE_MS)
                    val captureStart = android.os.SystemClock.elapsedRealtime()
                    val full = grabFull()''')
# Never treat capture failure as proof English disappeared.
change(cap,
'''                    if (full == null) {
                        diagNoFrame++''',
'''                    if (full == null) {
                        gtEnglishProbe=false
                        if(checkEnglish && shownValue.isNotBlank())showSubtitle(shownValue)
                        if(checkHud)overlay.setLabels(lastHudLabels)
                        diagNoFrame++''')
change(cap,
'''                    processSubtitle(full)

                    if (!isTv''',
'''                    try {
                        processSubtitle(full)
                    } finally {
                        gtEnglishProbe=false
                        if(checkEnglish && shownValue.isNotBlank())showSubtitle(shownValue)
                        if(checkHud)overlay.setLabels(lastHudLabels)
                    }

                    if (!isTv''')
# A full check must OCR every captured subtitle, even if bitmap unchanged.
change(cap,
'''        if (!subtitleReadGuard299.shouldOcr(sampleUnchanged, candidateSeen == 1, checkMs)) {''',
'''        if (!gtEnglishProbe &&
            !subtitleReadGuard299.shouldOcr(sampleUnchanged, candidateSeen == 1, checkMs)) {''')
# Two consecutive uncovered scans confirming English is gone -> clear Turkish.
# If English still there, the Turkish caption stays, regardless of elapsed time.
change(cap,
'''        lastOcrRaw = text
        handleText(text)''',
'''        lastOcrRaw = text
        if(gtEnglishProbe) {
            val original=if(shownSource.isNotBlank())shownSource else translatingFor
            val observed=adiAyir(clean(text))
            if(original.isNotBlank()) {
                val visible=observed.isNotBlank() &&
                    (similar(observed,original) ||
                     OcrOnar.ayniGurultulu(observed,original))
                if(visible)gtEnglishMissing=0
                else if(!isOurOwnText(observed)) {
                    gtEnglishMissing=GtEnglishPresence.nextMissing(false,gtEnglishMissing)
                    if(GtEnglishPresence.remove(gtEnglishMissing)) {
                        gtEnglishMissing=0
                        shownSource=""
                        translatingFor=""
                        candidate=""
                        candidateSeen=0
                        subtitleGeneration.invalidate()
                        showSubtitle(null)
                    }
                }
            } else gtEnglishMissing=0
        }
        handleText(text)''')
# The ordinary OCR pipeline may read the overlay instead of source. Keep
# waiting until the next unobstructed verification, not a lifetime timeout.
change(cap,
'''        // Keep the caption when an OCR scan misses visible English;
        // never dismiss just because a fixed time limit has elapsed.''',
'''        // A normal OCR miss is inconclusive under our translated overlay.
        // Uncovered source scans above decide when to remove the caption.''')
change(cap,
'''        shownSource = source
        shownValue = value''',
'''        shownSource = source
        gtEnglishMissing=0
        shownValue = value''')
# Re-read menu/HUD on unobstructed frame instead of endlessly holding
# stale translated mission text after exiting the map.
change(cap,
'''if (!isTv && cycle % MENU_EVERY == 0L''',
'''if (!isTv && (cycle % MENU_EVERY == 0L || checkHud)''')
# Replace v3.5 indefinite-hold expectations with correct limits.
change(tests/'GtOriginalBoundsTest.kt',
'''        assertTrue(GtSourceBox.hold(20,121000L))
        assertTrue(GtSourceBox.hold(1200,3600000L))''',
'''        assertFalse(GtSourceBox.hold(20,121000L))
        assertFalse(GtSourceBox.hold(1200,3600000L))''')
(tests/'GtEnglishPresenceTest.kt').write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtEnglishPresenceTest {
 @Test fun englishOnScreenMeansTurkishOnScreen() {
  assertEquals(0,GtEnglishPresence.nextMissing(true,1))
  assertFalse(GtEnglishPresence.remove(0))
  assertTrue(GtEnglishPresence.needsCheck(3600000,0,"Call me"))
 }
 @Test fun englishOffScreenRemovesTurkish() {
  assertEquals(1,GtEnglishPresence.nextMissing(false,0))
  assertFalse(GtEnglishPresence.remove(1))
  assertTrue(GtEnglishPresence.remove(GtEnglishPresence.nextMissing(false,1)))
 }
 @Test fun staleMenuLabelsAlsoDisappear() {
  assertFalse(GtSourceBox.hold(2,1700L))
  assertTrue(GtSourceBox.hold(1,700L))
 }
}
''',encoding='utf8')
v=build.read_text(encoding='utf8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261210',v,count=1)
if n!=1:raise RuntimeError('versionCode missing')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-3.7-EnglishVisibleOnly"',v,count=1)
if n!=1:raise RuntimeError('versionName missing')
build.write_text(v,encoding='utf8')
print('GameLingoPro 3.7 English source visibility controls Turkish display')
