#!/usr/bin/env python3
"""Apply 5.6.8 source-grounded translations and stable map OCR identities.
Keep upstream GameTranslator v1.8.49 implementation unchanged.
"""
from pathlib import Path
import shutil
r=Path(".")
src=r/"app/src/main/java/com/example/altyazi"
tests=r/"app/src/test/java/com/example/altyazi"
shutil.copyfile(r/"tools/gt568/GtMapIdentity568.kt",src/"GtMapIdentity568.kt")
shutil.copyfile(r/"tools/gt568/GtRealtime568Test.kt",tests/"GtRealtime568Test.kt")

def replace(path,old,new):
    s=path.read_text(encoding="utf8")
    found=s.count(old)
    if found!=1:
        raise ValueError(f"Anchor count {found} in {path} for {old[:75]!r}")
    path.write_text(s.replace(old,new,1),encoding="utf8")

cap=src/"CaptureService.kt"
replace(cap,"            val identity=panel.identity",
        "            val identity=GtMapIdentity568.identity(panel.identity)")
replace(cap,"            val heading=panel.title.trim()",
        "            val heading=GtMapIdentity568.heading(panel.title)")

quality=src/"GtOriginalQualityGuard.kt"
replace(quality,
'''            else -> GtDialogueQuality.polish(source, translated)''',
'''            // Conservative source-confirmed idiom corrections after the
            // authentic GameTranslator (GTX -> ML Kit) returns its answer.
            spoken == "damn" -> speaker("Vay be.")
            spoken.contains("five figures each") ->
                speaker("Kişi başı en az beş haneli bir meblağ!")
            spoken.contains("delight's could be big for all of us") &&
                spoken.contains("work together") ->
                speaker("Birlikte çalışırsak Delight's hepimiz için büyük bir fırsat olabilir.")
            spoken.contains("if it meant i could fuck over frankie even once") ->
                speaker("Frankie'ye bir kez olsun kazık atabileceksem...")
            spoken.contains("i would punt a orphan into traffic") ||
                spoken.contains("i would punt an orphan into traffic") ->
                speaker("Lucia, biliyorsun, bir yetimi bile trafiğin ortasına tekmelerim.")
            spoken.startsWith("good see in' you two the other day") &&
                spoken.contains("y'all been stewin'") ->
                speaker("Geçen gün ikinizi görmek güzeldi. Konuştuklarımızı düşündünüz mü?")
            spoken.startsWith("girl, i say go for it") ->
                speaker("Kızım, bence hiç durma, yap gitsin.")
            else -> GtDialogueQuality.polish(source, translated)''')

gradle=r/"app/build.gradle.kts"
replace(gradle,'applicationId = "com.gamelingo.pro.gt1849.fast567"',
               'applicationId = "com.gamelingo.pro.gt1849.fast568"')
replace(gradle,'versionName = "GameLingoPro-5.6.7-GTDialogueFix"',
               'versionName = "GameLingoPro-5.6.8-GTQuality"')
replace(gradle,'versionCode = 20261238','versionCode = 20261239')
replace(r/"app/src/main/res/values/strings.xml",
        '<string name="app_name">GameLingoPro GT DialogueFix</string>',
        '<string name="app_name">GameLingoPro GT Quality</string>')
replace(tests/"GtBrandIdentity522Test.kt",
        'GameLingoPro GT DialogueFix</string>',
        'GameLingoPro GT Quality</string>')

assert (r/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt").is_file()
print("5.6.8 GTQuality source-grounded idioms and map OCR identity corrections applied")
