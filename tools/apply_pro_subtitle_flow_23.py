#!/usr/bin/env python3
"""Fix missing second lines, wrong OPUS literal meanings and oversized captions.
Applies only to the original Kotlin GameLingoPro. Run after HUD and quality patches.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
src = root / "app/src/main/java/com/example/altyazi"
cap = src / "CaptureService.kt"
over = src / "Overlay.kt"
helper = src / "ProTranscriptGuard.kt"
gate = src / "TranslationQualityGate.kt"
sub = src / "OfflineFix.kt"
build = root / "app/build.gradle.kts"
for file in (cap, over, helper, gate, sub, build):
    if not file.is_file():
        raise SystemExit(f"Missing GameLingoPro original source: {file}")
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise SystemExit("Refusing to patch another app package")

def replace_once(file, old, new):
    s = file.read_text(encoding="utf-8")
    if new in s:
        return
    if s.count(old) != 1:
        raise RuntimeError(f"Unexpected source at {file}: {old[:100]!r} ({s.count(old)})")
    file.write_text(s.replace(old, new, 1), encoding="utf-8")

marker = "    /** Flag visibly literal idioms, never invent a replacement translation. */"
guard = r'''    /** A NEW trailing clause is not duplicate OCR of its earlier first line. */
    fun meaningfulExpansion(incoming: String, older: String): Boolean {
        fun normalizeWords(t: String): String = t.lowercase(Locale.ROOT)
            .replace(Regex("""[^\p{L}\p{N}]+"""), " ")
            .trim().replace(Regex("""\s+"""), " ")
        val current = normalizeWords(incoming)
        val previous = normalizeWords(older)
        if (previous.length < 24 || current.length < previous.length + 15) return false
        if (!current.startsWith(previous)) return false
        return current.substring(previous.length).trim()
            .split(Regex("""\s+""")).count { it.isNotBlank() } >= 3
    }

'''
replace_once(helper, marker, guard + marker)

# Both near-match detection and noisy-OCR dedupe must allow a later full line.
for previous in ("shownSource", "translatingFor"):
    before = (
        f"if (similar(text, {previous}) || "
        f"(ProTranscriptGuard.speakersCompatible(text, {previous}) && "
        f"OcrOnar.ayniGurultulu(text, {previous}))) {{"
    )
    after = (
        f"if (!ProTranscriptGuard.meaningfulExpansion(text, {previous}) &&\n"
        f"            (similar(text, {previous}) || "
        f"(ProTranscriptGuard.speakersCompatible(text, {previous}) && "
        f"OcrOnar.ayniGurultulu(text, {previous})))) {{"
    )
    replace_once(cap, before, after)

replace_once(
    cap, "if (similar(source, translatingFor)) return",
    "if (!ProTranscriptGuard.meaningfulExpansion(source, translatingFor) && "
    "similar(source, translatingFor)) return"
)
replace_once(
    cap,
    "val gerekenOkuma = if (tamamGorunuyor && SubtitlePreparation.confidentFirstRead(text)) 1 else 2",
    'val gerekenOkuma = if (text.trimEnd().endsWith(",")) 2\n'
    '            else if (tamamGorunuyor && SubtitlePreparation.confidentFirstRead(text)) 1 else 2'
)

# Two lines separated by slightly more than one glyph-height still belong to
# the same OCR subtitle if the upper line is clearly a continuation.
replace_once(
    sub,
    "if (gap > lineH * 0.9f) break          // arada bir satırdan fazla boşluk: başka blok",
    """val continued = l.text.trimEnd().endsWith(',') ||
                l.text.trimEnd().endsWith(';') ||
                below.text.trimStart().firstOrNull()?.isLowerCase() == true
            val gapFactor = if (continued) 1.65f else 0.9f
            if (gap > lineH * gapFactor) break"""
)

# During phone screen capture the translated window sometimes masks the still
# visible English second line. Keep even "COVER" above the OCR read strip.
replace_once(
    cap,
    "subtitleBottomPx = if (prefs.subtitlePos == Prefs.POS_ABOVE) seritUstu - dp(6) else -1",
    """subtitleBottomPx = if (prefs.subtitlePos == Prefs.POS_ABOVE ||
            prefs.subtitlePos == Prefs.POS_COVER) seritUstu - dp(9) else -1"""
)
replace_once(
    cap,
    "boyutSp = if (tv) maxOf(prefs.subtitleSize * 1.5f, 26f) else prefs.subtitleSize.toFloat(),",
    """boyutSp = if (screenWidth > screenHeight) {
                prefs.subtitleSize.toFloat().coerceIn(14f, 20f)
            } else if (tv) maxOf(prefs.subtitleSize * 1.5f, 26f)
            else prefs.subtitleSize.toFloat(),"""
)
replace_once(
    over,
    """            lp.leftMargin = kenar
            lp.rightMargin = kenar
            t.layoutParams = lp""",
    """            lp.leftMargin = kenar
            lp.rightMargin = kenar
            val displayWidth = context.resources.displayMetrics.widthPixels
            t.maxWidth = (displayWidth * .84f).toInt().coerceAtLeast(dp(200))
            t.maxLines = 3
            t.layoutParams = lp"""
)
replace_once(
    over,
    "oncekiYerlestir(previous, lp.topMargin, lp.leftMargin, lp.rightMargin)",
    """oncekiYerlestir(if (context.resources.displayMetrics.widthPixels >
                context.resources.displayMetrics.heightPixels) null else previous,
                lp.topMargin, lp.leftMargin, lp.rightMargin)"""
)

# The observed medium -> "orta yol" and hold-on -> "bekle biraz" errors should
# make OPUS reject only that bad output and use the existing Google fallback.
replace_once(
    gate,
    "        if (ProTranscriptGuard.literalIdiom(s, t)) return Problem.LITERAL_IDIOM",
    """        if (ProTranscriptGuard.literalIdiom(s, t)) return Problem.LITERAL_IDIOM
        if (s.contains("serve as a medium", ignoreCase = true) &&
            (t.contains("orta yol", ignoreCase = true) || t.contains("medyum", ignoreCase = true)))
            return Problem.LITERAL_IDIOM
        if (s.contains("hold on any longer", ignoreCase = true) &&
            (t.contains("bekle biraz", ignoreCase = true) || t.contains("daha fazla açık", ignoreCase = true)))
            return Problem.LITERAL_IDIOM
        if (s.startsWith("May ") && s.contains(" rise to ") && t.startsWith("May "))
            return Problem.ENGLISH_FRAGMENT"""
)

# Narrow, context-validated OCR slips only, not an open-ended hallucination map.
replace_once(
    helper,
    r'            .replace(Regex("\\bmy OWn\\b"),"my own")',
    r'''            .replace(Regex("\\bmy OWn\\b"),"my own")
            .replace(Regex("(?i)\\bMaster[. ]+0 finally\\b"),"Master... I finally")
            .replace(Regex("(?i)\\bIcanthold on any longer\\b"),"I can't hold on any longer")'''
)
s = build.read_text(encoding="utf-8")
s = re.sub(r"(?m)^(\s*)versionCode\s*=\s*\d+",
           r"\g<1>versionCode = 20261124", s, count=1)
s = re.sub(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
           r'\g<1>versionName = "GameLingoPro-2.3-SubtitleFlow"', s, count=1)
build.write_text(s, encoding="utf-8")
assert 'meaningfulExpansion' in helper.read_text()
assert 'gapFactor' in sub.read_text()
assert 'serve as a medium' in gate.read_text()
assert "versionCode = 20261124" in build.read_text()
print("GameLingoPro 2.3 OCR continuation + quality + compact landscape display applied")
