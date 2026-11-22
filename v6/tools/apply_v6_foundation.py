#!/usr/bin/env python3
"""V6 foundation: fixed test app ID + shadow routing and quality audits.
Deliberately preserves current GameTranslator rendering and request path.
"""
from pathlib import Path
import shutil

root=Path(".")
app=root/"app/src/main/java/com/example/altyazi"
unit=root/"app/src/test/java/com/example/altyazi"
app_v6=app/"v6";unit_v6=unit/"v6"
app_v6.mkdir(parents=True,exist_ok=True);unit_v6.mkdir(parents=True,exist_ok=True)
for name in ("V6CaptionAudit.kt","V6TranslationAudit.kt"):
    shutil.copyfile(root/"v6/src"/name,app_v6/name)
for name in ("V6CaptionAuditTest.kt","V6TranslationAuditTest.kt"):
    shutil.copyfile(root/"v6/src"/name,unit_v6/name)
resources=root/"app/src/test/resources"
resources.mkdir(parents=True,exist_ok=True)
shutil.copyfile(root/"v6/fixtures/v6-caption-cases.tsv",resources/"v6-caption-cases.tsv")

def replace(file,needle,replacement):
    text=file.read_text(encoding="utf8")
    n=text.count(needle)
    if n != 1:
        raise RuntimeError(f"V6 failed to find unique anchor ({n}): {file} / {needle[:85]}")
    file.write_text(text.replace(needle,replacement,1),encoding="utf8")

service=app/"CaptureService.kt"
replace(service,
'''    private fun handleOriginalGameTranslatorText(raw: String) {
        val text = if''',
'''    private fun handleOriginalGameTranslatorText(raw: String) {
        // V6 shadow audit: independent observations, no translation/filter change.
        if (prefs.diagnostics && raw.isNotBlank()) {
            val review = com.example.altyazi.v6.V6CaptionAudit.inspect(raw)
            if (review.kind == com.example.altyazi.v6.V6CaptionAudit.Kind.OVERLAP ||
                review.kind == com.example.altyazi.v6.V6CaptionAudit.Kind.SUSPECT) {
                log("V6 OCR İNCELEME: " + review.kind + " · " + raw.take(75))
            }
        }
        val text = if''')
replace(service,
'''                        publish(source, GtOriginalQualityGuard.polish(source, translated),
                            remember = false, tag = " · GT ORİJİNAL")''',
'''                        val rendered = GtOriginalQualityGuard.polish(source, translated)
                        if (prefs.diagnostics) {
                            val issues = com.example.altyazi.v6.V6TranslationAudit.check(source,rendered)
                            if (issues.isNotEmpty()) log("V6 KALİTE UYARISI: " +
                                issues.joinToString(",") + " · " + source.take(55))
                        }
                        publish(source, rendered,
                            remember = false, tag = " · GT ORİJİNAL")''')

gradle=root/"app/build.gradle.kts"
replace(gradle,'applicationId = "com.gamelingo.pro.gt1849.fast568"',
              'applicationId = "com.gamelingo.pro.v6test"')
replace(gradle,'versionCode = 20261239',
              'versionCode = 600001')
replace(gradle,'versionName = "GameLingoPro-5.6.8-GTQuality"',
              'versionName = "6.0.0-alpha.1"')
replace(root/"app/src/main/res/values/strings.xml",
        '<string name="app_name">GameLingoPro GT Quality</string>',
        '<string name="app_name">GameLingo V6 Test</string>')
replace(unit/"GtBrandIdentity522Test.kt",
        'GameLingoPro GT Quality</string>',
        'GameLingo V6 Test</string>')

assert (app/"GtOriginalDialoguePipeline.kt").is_file()
assert (root/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt").is_file()
print("V6 shadow mode ready: fixed package identity, audited OCR/translation, original engine untouched.")
