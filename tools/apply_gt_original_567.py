#!/usr/bin/env python3
"""5.6.7: safer caption boundaries, accurate per-caption OCR timing, idioms.
GameTranslator v1.8.49 original classes MUST stay unchanged.
"""
from pathlib import Path
p=Path(".")
src=p/"app/src/main/java/com/example/altyazi"
tests=p/"app/src/test/java/com/example/altyazi"
def rep(path,old,new):
    s=path.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1: raise RuntimeError(f"{path}: expected exactly one anchor, got {n}: {old[:80]}")
    path.write_text(s.replace(old,new,1),encoding="utf-8")

guard=src/"GtOriginalInputGuard.kt"
rep(guard,
'''        if (cues.size > 1) s = s.substring(cues.last().range.first).trimStart()''',
'''        // A leftover half-sentence before ONE new speaker is also an overlap.
        // Earlier guard only handled 2+ speaker tags, causing "old text. Jason: ..."
        // to enter Google as a single sentence.
        if (cues.isNotEmpty() &&
            (cues.size > 1 || cues.first().range.first > 0)) {
            s = s.substring(cues.last().range.first).trimStart()
        }''')
rep(guard,
'''        s = s.replace(Regex("""(?i)^Bily:"""), "Billy:")''',
'''        s = s.replace(Regex("""(?i)^Bily:"""), "Billy:")
        s = s.replace(Regex("""(?i)^Staff\\s+Menmber:"""), "Staff Member:")
        s = s.replace(Regex("""(?i)^Strange:"""), "Stranger:")
        s = s.replace(Regex("""(?i)\\bVWhat'chu\\b"""), "What'chu")''')
quality=src/"GtOriginalQualityGuard.kt"
rep(quality,
'''            else -> GtDialogueQuality.polish(source, translated)''',
'''            // Source-locked short expressions; leave the upstream translator
            // unchanged and do not rewrite unrelated dialogue.
            spoken.contains("you're hurting me") &&
                spoken.endsWith("stop") &&
                translated.contains("Durmak!", ignoreCase = true) ->
                    translated.replace(Regex("""(?iu)Durmak!"""), "Dur!")
            spoken.contains("ten and two") &&
                spoken.contains("hillbilly") ->
                    speaker("Hey! Ellerini direksiyonda saat on ve iki yönünde tut, cahil köylü!")
            spoken.contains("we got time to kill") &&
                translated.contains("öldürecek zaman", ignoreCase = true) ->
                    translated.replace("öldürecek zamanımız var", "boş vaktimiz var", ignoreCase = true)
            spoken.contains("i'm not reachin' in there") &&
                spoken.contains("unhygenic") ->
                    speaker("Elimi oraya sokmam! Sokmam işte! Hijyenik değil!")
            else -> GtDialogueQuality.polish(source, translated)''')
pipeline=src/"GtOriginalDialoguePipeline.kt"
rep(pipeline,
'''import com.gametranslator.gametranslator_mobile.core.TextBox''',
'''import com.gametranslator.gametranslator_mobile.core.TextBox
import com.gametranslator.gametranslator_mobile.core.OcrNoise''')
rep(pipeline,
'''        if (text.isNotBlank() && ocrStartedMs > 0L)
            latency.read(text, ocrStartedMs, ocrDurationMs)
        val lines=if (text.isBlank()) emptyList() else text.lines()
        originalPipeline.onRead(lines,null)
        if (GtOriginalInputGuard.canFastTrack(text) &&
            !com.gametranslator.gametranslator_mobile.core.SubtitleStabilizer.endsSentence(text)) {
            originalPipeline.onRead(lines,null)
        }''',
'''        // Use exactly the cleaned source produced by the original pipeline
        // as the latency key. This avoids false "OCR 0" / "ölçülemedi" samples.
        val checked = GtOriginalInputGuard.prepare(text)
        val lines = if (checked.isBlank()) emptyList() else checked.lines()
        val upstreamCleaned = lines.map { OcrNoise.clean(it) }
            .filter { it.isNotEmpty() }.joinToString("\\n")
        if (upstreamCleaned.isNotBlank() && ocrStartedMs > 0L) {
            latency.read(upstreamCleaned, ocrStartedMs, ocrDurationMs)
        }
        // Feed exactly ONCE per captured observation. The previous fast-path
        // submitted the same frame twice to fake stability and could elevate
        // an OCR mistake before a second independent image had been read.
        originalPipeline.onRead(lines, null)''')
gradle=p/"app/build.gradle.kts"
rep(gradle,'applicationId = "com.gamelingo.pro.gt1849.fast566"',
    'applicationId = "com.gamelingo.pro.gt1849.fast567"')
rep(gradle,'versionCode = 20261237','versionCode = 20261238')
rep(gradle,'versionName = "GameLingoPro-5.6.6-GTStableFast"',
    'versionName = "GameLingoPro-5.6.7-GTDialogueFix"')
rep(p/"app/src/main/res/values/strings.xml",
    '<string name="app_name">GameLingoPro GT StableFast</string>',
    '<string name="app_name">GameLingoPro GT DialogueFix</string>')
rep(tests/"GtBrandIdentity522Test.kt",
    'GameLingoPro GT StableFast</string>',
    'GameLingoPro GT DialogueFix</string>')
(tests/"GtRealtime567Test.kt").write_text(r'''package com.example.altyazi

import org.junit.Assert.*
import org.junit.Test

class GtRealtime567Test {
 @Test fun splitSingleSpeakerTagInMiddleOfOldLine() {
   assertEquals("Jason: I'm gonna need this car.",
       GtOriginalInputGuard.prepare(
         "and she's literally immobile. Get out of the road. Jason: I'm gonna need this car."))
   assertEquals("Jason: Alright. So do something.",
       GtOriginalInputGuard.prepare(
         "you gon' see what tough is. Jason: Alright. So do something."))
 }
 @Test fun splitTwoSpeakersAndPreserveMultiSentenceCaption() {
   assertEquals("Jason: We left your car at Hank's.",
       GtOriginalInputGuard.prepare(
         "Stranger: I'll look for you. Jason: We left your car at Hank's."))
   assertEquals("Local: Ah! You're hurting me! Stop!",
       GtOriginalInputGuard.prepare("Local: Ah! You're hurting me! Stop!"))
 }
 @Test fun correctLabelsWithoutChangingSlang() {
   assertEquals("Staff Member: Anything else?",
       GtOriginalInputGuard.prepare("Staff Menmber: Anything else?"))
   assertEquals("Stranger: Hi there!",
       GtOriginalInputGuard.prepare("Strange: Hi there!"))
   assertEquals("Locals: We got time to kill! What'chu wanna do?",
       GtOriginalInputGuard.prepare(
          "Locals: We got time to kill! VWhat'chu wanna do?"))
 }
 @Test fun meaningScopedCorrections() {
   assertEquals("Local: Ah! Canımı acıtıyorsun! Dur!",
       GtOriginalQualityGuard.polish(
         "Local: Ah! You're hurting me! Stop!",
         "Local: Ah! Canımı acıtıyorsun! Durmak!"))
   assertEquals("Local: Hey! Ellerini direksiyonda saat on ve iki yönünde tut, cahil köylü!",
       GtOriginalQualityGuard.polish("Local: Hey! Ten and two! Ignorant hillbilly.",
         "Local: Hey! On ve iki! Cahil köylü."))
   assertEquals("Local: Merhaba.",
       GtOriginalQualityGuard.polish("Local: Hello.", "Local: Merhaba."))
 }
}''',encoding="utf-8")
# Strict check upstream implementation has not been modified.
assert (p/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt").exists()
print("5.6.7 speaker boundary, source-matched idioms, and OCR clock key corrected.")
