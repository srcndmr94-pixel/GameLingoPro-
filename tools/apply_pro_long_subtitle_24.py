#!/usr/bin/env python3
"""GameLingoPro 2.4: fix long source OCR captions and remove 3-line text truncation.
Run after 2.3 original GameLingoPro Kotlin patches. No GameTranslator replacement.
"""
from pathlib import Path
import re,sys,shutil
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"
offline=src/"OfflineFix.kt"
overlay=src/"Overlay.kt"
build=root/"app/build.gradle.kts"
for f in (cap,offline,overlay,build):
    if not f.is_file():raise RuntimeError("Missing GameLingoPro source: "+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Wrong Android application; refusing to patch")
shutil.copyfile("tools/ProSubtitleAssembler.kt",src/"ProSubtitleAssembler.kt")

def once(f,a,b):
    s=f.read_text(encoding="utf8")
    if b in s:return
    if s.count(a)!=1:
        raise RuntimeError(f"{f.name}: expected 1 anchor, found {s.count(a)}: {a[:80]!r}")
    f.write_text(s.replace(a,b,1),encoding="utf8")

# No maximum of three OCR lines: an English description may wrap into 4-6.
once(offline,
    'if (out.size >= 3) break               // altyazı en fazla üç satırdır',
    'if (out.size >= 6) break               // uzun altyazı satırlarını kesme')

anchor='    private var ocrScreenPerCap = 1f'
once(cap,anchor,anchor+'''
    private val proSubtitleAssembler = ProSubtitleAssembler()
    private var candidateStartedAtMs = 0L
    private var lastLongOcrRetryAtMs = 0L''')

# Recheck a still-pending partial read even if no bitmap pixels changed.
once(cap,
    'if (candidateSeen == 1 && lastOcrRaw.isNotEmpty()) handleText(lastOcrRaw)',
    'if (candidate.isNotEmpty() && lastOcrRaw.isNotEmpty()) handleText(lastOcrRaw)')

once(cap,
'''        val text = runOcr(band, filterEdges = true)
        sonOcrMs = android.os.SystemClock.elapsedRealtime() - ocrBasi''',
'''        var text = runOcr(band, filterEdges = true)
        // Second OCR pass only when the first row clearly ends mid-clause.
        val ocrNow = android.os.SystemClock.elapsedRealtime()
        if (ProSubtitleAssembler.likelyContinued(text) &&
            band.width < 2700 && ocrNow - lastLongOcrRetryAtMs >= 450L) {
            lastLongOcrRetryAtMs = ocrNow
            val zoom = if (band.width >= 1450) 1.35f else 1.6f
            val scaled = Bitmap.createScaledBitmap(
                band, (band.width * zoom).toInt(), (band.height * zoom).toInt(), true)
            if (scaled !== band) {
                val oldScale = ocrBandScale
                try {
                    ocrBandScale *= zoom
                    text = ProSubtitleAssembler.fuller(text, runOcr(scaled, filterEdges = true))
                } finally {
                    ocrBandScale = oldScale
                    scaled.recycle()
                }
            }
        }
        sonOcrMs = android.os.SystemClock.elapsedRealtime() - ocrBasi''')

# Align translation box ABOVE the actual English text, not just a guessed row.
once(cap,
'''        val blok = SubtitleBlocks.bottomBlock(kept)
        if (altta && blok.isNotEmpty()) {''',
'''        val blok = SubtitleBlocks.bottomBlock(kept)
        if (filterEdges && blok.isNotEmpty() &&
            (prefs.subtitlePos == Prefs.POS_ABOVE || prefs.subtitlePos == Prefs.POS_COVER)) {
            val sourceTopPx = ekranY(blok.minOf { it.top })
            subtitleBottomPx = minOf(
                subtitleBottomPx.takeIf { it > 0 } ?: sourceTopPx,
                sourceTopPx - dp(10)).coerceAtLeast(dp(24))
        }
        if (altta && blok.isNotEmpty()) {''')

# Use the fullest recent OCR read; don't let a one-line retry overwrite a
# complete two-line English caption.
once(cap,
    'val text = adiAyir(clean(raw))',
    '''val text = proSubtitleAssembler.accept(
            adiAyir(clean(raw)), android.os.SystemClock.elapsedRealtime())''')
once(cap,
'''        if (similar(text, candidate)) {
            candidateSeen++
        } else {
            candidate = text
            candidateSeen = 1
        }''',
'''        if (similar(text, candidate)) {
            candidateSeen++
        } else {
            candidate = text
            candidateSeen = 1
            candidateStartedAtMs = android.os.SystemClock.elapsedRealtime()
        }''')
once(cap,
'''        if (candidateSeen < gerekenOkuma) return
        if (!ProTranscriptGuard.meaningfulExpansion(text, translatingFor)''',
'''        if (candidateSeen < gerekenOkuma) return
        // Wait only 750ms for a comma-ended subtitle to complete.
        if (ProSubtitleAssembler.likelyContinued(text) &&
            android.os.SystemClock.elapsedRealtime() - candidateStartedAtMs < 750L) return
        if (!ProTranscriptGuard.meaningfulExpansion(text, translatingFor)''')

# Never silently ellipsize or clip a long Turkish translation.
once(overlay,
'''            t.maxWidth = (displayWidth * .84f).toInt().coerceAtLeast(dp(200))
            t.maxLines = 3
            t.layoutParams = lp''',
'''            t.maxWidth = (displayWidth * .86f).toInt().coerceAtLeast(dp(200))
            t.maxLines = Int.MAX_VALUE
            t.ellipsize = null
            val scale = when {
                value.length > 290 -> .70f
                value.length > 210 -> .78f
                value.length > 145 -> .85f
                value.length > 95 -> .91f
                else -> 1f
            }
            t.setTextSize(TypedValue.COMPLEX_UNIT_SP,
                (stil.boyutSp * scale).coerceAtLeast(11f))
            t.layoutParams = lp''')

s=build.read_text(encoding="utf8")
s,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
            r'\g<1>versionCode = 20261125',s,count=1)
if n!=1:raise RuntimeError("VersionCode missing")
s,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-2.4-LongSubtitle"',s,count=1)
if n!=1:raise RuntimeError("VersionName missing")
build.write_text(s,encoding="utf8")
assert "ProSubtitleAssembler.fuller" in cap.read_text()
assert "versionCode = 20261125" in build.read_text()
print("GameLingoPro 2.4 full multi-line OCR and overlay patch installed")
