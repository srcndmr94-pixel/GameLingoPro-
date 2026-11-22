#!/usr/bin/env python3
"""Apply GameLingo OCR/quality adapters to the unmodified GameTranslator v1.8.49 integration."""
from pathlib import Path
import shutil

root = Path('.')
src = root / 'app/src/main/java/com/example/altyazi'
tests = root / 'app/src/test/java/com/example/altyazi'
for file_name in ('GtOriginalInputGuard.kt', 'GtOriginalQualityGuard.kt'):
    shutil.copyfile(root / 'tools/gt563' / file_name, src / file_name)
shutil.copyfile(root / 'tools/gt563/GtOriginalInputGuard563Test.kt',
                tests / 'GtOriginalInputGuard563Test.kt')

def replace_exact(path, old, new):
    s = path.read_text(encoding='utf8')
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'Anchor mismatch in {path}: {count}, {old[:70]}')
    path.write_text(s.replace(old, new, 1), encoding='utf8')

capture = src / 'CaptureService.kt'
replace_exact(capture,
    '                        publish(source, translated, remember = false, tag = " · GT ORİJİNAL")',
    '''                        publish(source, GtOriginalQualityGuard.polish(source, translated),
                            remember = false, tag = " · GT ORİJİNAL")''')
replace_exact(capture,
    '''        val text = if (raw.isBlank() || GtDialogueQuality.stageOnly(raw)) "" else
            GtDialogueQuality.repairOcr(adiAyir(clean(raw)))
        val usable = if (text.isBlank() || GtObjectiveLine.matches(text) ||
            isOurOwnText(text) || altyaziDegil(text) || OcrQuality.bozukMu(text)) "" else text''',
    '''        val text = if (raw.isBlank() || GtDialogueQuality.stageOnly(raw)) "" else {
            // Fix OCR before the old destructive cleaner. Restore readable spoken
            // lines if legacy heuristics falsely discard or truncate them.
            val prepared = GtOriginalInputGuard.prepare(raw)
            val cleaned = if (prepared.isBlank()) "" else clean(prepared)
            val recovered = GtOriginalInputGuard.recoverableSpokenLine(prepared) &&
                (cleaned.isBlank() || cleaned.length < prepared.length * .70f)
            val source = if (recovered) {
                if (prefs.diagnostics) log("GT ORİJİNAL OCR YANLIŞ ELEME KURTARILDI: " + prepared.take(70))
                prepared
            } else cleaned
            GtOriginalInputGuard.prepare(GtDialogueQuality.repairOcr(adiAyir(source)))
        }
        // The original upstream stabilizer still controls debounce and caching.
        val usable = if (text.isBlank() || GtOriginalInputGuard.isHudObjective(text) ||
            GtObjectiveLine.matches(text) || GtOriginalInputGuard.looksClipped(text) ||
            isOurOwnText(text) || altyaziDegil(text) || OcrQuality.bozukMu(text)) "" else text''')
replace_exact(capture,
    '''            if (isControllerLabel(text)) continue
            if (isOurOwnText(text)) continue''',
    '''            if (isControllerLabel(text)) continue
            if (GtOriginalInputGuard.isHudObjective(text)) continue
            if (isOurOwnText(text)) continue''')

original = src / 'GtOriginalDialoguePipeline.kt'
replace_exact(original,
    'import com.gametranslator.gametranslator_mobile.core.TextBox',
    '''import com.gametranslator.gametranslator_mobile.core.TextBox
import com.gametranslator.gametranslator_mobile.core.TextTranslator''')
replace_exact(original,
    '    private val originalPipeline = SubtitlePipeline(originalTranslator, object : SubtitleSink {',
    '''    // Upstream translator remains unchanged. This lightweight adapter protects
    // the English speaker's proper name before calling the original GTX -> ML Kit.
    private val speakerSafeTranslator = TextTranslator { input ->
        val (label, body) = GtOriginalInputGuard.splitSpeaker(input)
        if (label == null) originalTranslator.translate(body) else
            originalTranslator.translate(body)?.let { "$label: $it" }
    }
    private val originalPipeline = SubtitlePipeline(speakerSafeTranslator, object : SubtitleSink {''')

gradle = root / 'app/build.gradle.kts'
replace_exact(gradle, 'applicationId = "com.gamelingo.pro.gt1849"',
              'applicationId = "com.gamelingo.pro.gt1849.fix563"')
replace_exact(gradle, 'versionName = "GameLingoPro-5.6.2-GTOriginal"',
              'versionName = "GameLingoPro-5.6.3-GTOriginalFix"')
replace_exact(gradle, 'versionCode = 20261233', 'versionCode = 20261234')
strings = root / 'app/src/main/res/values/strings.xml'
replace_exact(strings, '<string name="app_name">GameLingoPro GT Original</string>',
              '<string name="app_name">GameLingoPro GT Fix</string>')
brand = tests / 'GtBrandIdentity522Test.kt'
replace_exact(brand,
    'GameLingoPro GT Original</string>',
    'GameLingoPro GT Fix</string>')
assert (src / 'GtOriginalDialoguePipeline.kt').exists()
assert (src / 'GtOriginalInputGuard.kt').exists()
assert (root/'app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt').exists()
print('5.6.3: Original GameTranslator pipeline unchanged; GameLingo OCR/quality adapters updated.')
