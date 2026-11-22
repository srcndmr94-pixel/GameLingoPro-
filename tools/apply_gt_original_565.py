#!/usr/bin/env python3
"""GameLingo 5.6.5: targeted OCR scheduling, readable latency telemetry, OCR token fixes.
Preserves original GameTranslator v1.8.49 pipeline and Google GTX -> ML Kit fallback.
"""
from pathlib import Path
import re
root=Path(".")
src=root/"app/src/main/java/com/example/altyazi"
tests=root/"app/src/test/java/com/example/altyazi"

def replace(path,old,new):
    s=path.read_text(encoding="utf-8")
    n=s.count(old)
    if n != 1:
        raise AssertionError(f"{path}: expected 1 match, found {n} for {old[:80]!r}")
    path.write_text(s.replace(old,new,1),encoding="utf-8")

ocr=src/"GtRealtimeOcrPolicy.kt"
replace(ocr,
'''        return ProSubtitleAssembler.likelyContinued(s) ||
            GtOriginalInputGuard.looksClipped(s)''',
'''        // A natural pause/line break is NOT proof the capture rectangle
        // clipped a word. Extra OCR formerly ran for many complete fragments.
        // Only retry when the last short token looks physically truncated.
        return GtOriginalInputGuard.looksClipped(s)''')
replace(ocr,"const val EXPANDED_RETRY_COOLDOWN_MS = 1800L",
        "const val EXPANDED_RETRY_COOLDOWN_MS = 2400L")

guard=src/"GtOriginalInputGuard.kt"
replace(guard,
'''        s = s.replace(Regex("""(?i)\\bABilly:\\s*"""), "Billy: ")
        return s.replace(Regex("""\\s{2,}"""), " ").trim()''',
'''        s = s.replace(Regex("""(?i)\\bABilly:\\s*"""), "Billy: ")
        // Context-constrained OCR repairs observed in real-game captions.
        // Avoid global replacements of common English words/names.
        s = s.replace(Regex("""(?i)^Bily:"""), "Billy:")
        s = s.replace(Regex("""(?i)\\bwalit\\s+up\\b"""), "wait up")
        s = s.replace(Regex("""(?i)\\bFO\\s+hit\\s+you\\s+up\\b"""), "I'll hit you up")
        s = s.replace(Regex("""(?i)\\bIt\\s+I\\s+be\\s+with\\b"""), "It'll be with")
        s = s.replace(Regex("""(?i)\\bhis[t]?\\s+[o0]\\s+[dD]\\s+(?=identity\\b)"""), "his ")
        s = s.replace(Regex("""(?i)\\bkn\\s+Ow\\b"""), "know")
        s = s.replace(Regex("""(?i)\\bI,\\s+mean\\b"""), "I mean")
        s = s.replace(Regex("""(?i)\\bdepends\\.g\\b"""), "depends.")
        return s.replace(Regex("""\\s{2,}"""), " ").trim()''')

capture=src/"CaptureService.kt"
replace(capture,
'''                        gtOriginalDialogueDelegate.value.shown(source)?.let { metrics ->
                            if (prefs.diagnostics) log(
                                "GT GECİKME: OCR " + metrics.ocrMs + " ms · OCR→motor " +
                                metrics.waitBeforeTranslationMs + " ms (kuyruk " +
                                metrics.queueMs + " ms) · çeviri " + metrics.translationMs +
                                " ms · gösterim " + metrics.displayMs + " ms · toplam " +
                                metrics.totalMs + " ms · eski kuyruk atlandı " +
                                gtOriginalDialogueDelegate.value.droppedOldRequests() +
                                " · " + source.take(55))
                        }''',
'''                        // Always emit one end-to-end sample per displayed subtitle.
                        // In 5.6.4 this ran only with "diagnostics" enabled, making
                        // real-world performance logs appear to have no measurements.
                        val metrics = gtOriginalDialogueDelegate.value.shown(source)
                        if (metrics != null) {
                            log("GT GECİKME: OCR " + metrics.ocrMs + " ms · OCR→motor " +
                                metrics.waitBeforeTranslationMs + " ms (kuyruk " +
                                metrics.queueMs + " ms) · çeviri " + metrics.translationMs +
                                " ms · gösterim " + metrics.displayMs + " ms · toplam " +
                                metrics.totalMs + " ms · eski kuyruk atlandı " +
                                gtOriginalDialogueDelegate.value.droppedOldRequests() +
                                " · " + source.take(55))
                        } else {
                            log("GT GECİKME: önbellek/ölçüm eşleşmedi · " + source.take(55))
                        }''')
gradle=root/"app/build.gradle.kts"
replace(gradle,'applicationId = "com.gamelingo.pro.gt1849.fast564"',
        'applicationId = "com.gamelingo.pro.gt1849.fast565"')
replace(gradle,'versionName = "GameLingoPro-5.6.4-GTFast"',
        'versionName = "GameLingoPro-5.6.5-GTFastOCR"')
replace(gradle,"versionCode = 20261235","versionCode = 20261236")
strings=root/"app/src/main/res/values/strings.xml"
replace(strings,'<string name="app_name">GameLingoPro GT Fast</string>',
        '<string name="app_name">GameLingoPro GT Fast OCR</string>')
brand=tests/"GtBrandIdentity522Test.kt"
replace(brand,'GameLingoPro GT Fast</string>',
        'GameLingoPro GT Fast OCR</string>')
test=tests/"GtRealtime565Test.kt"
test.write_text(r'''package com.example.altyazi

import org.junit.Assert.*
import org.junit.Test

class GtRealtime565Test {
    @Test fun doNotRescanEveryUnpunctuatedClause() {
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(
            "Authorities are urging Leonida residents to be on the lookout",
            10000L, false))
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(
            "Victims report seeing the suspect running out of homes",
            10000L, false))
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(
            "A long complete phrase can end with an ordinary English word",
            10000L, false))
    }
    @Test fun stillAllowGenuinelyClippedWordsWithCooldown() {
        val broken = "Wyman: if you wanna go, get yourselves another set of clo"
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(broken,2399L,false))
        assertTrue(GtRealtimeOcrPolicy.shouldExpand(broken,2400L,false))
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(broken,10000L,true))
    }
    @Test fun observedOcrBrokenTokensFixedOnlyInContext() {
        assertEquals("Billy: Yo, wait up.",GtOriginalInputGuard.prepare("Bily: Yo, walit up."))
        assertEquals("Billy: Okay, cool. I'll hit you up then.",
            GtOriginalInputGuard.prepare("Billy: Okay, cool. FO hit you up then."))
        assertEquals("Billy: It'll be with the crew you met already.",
            GtOriginalInputGuard.prepare("Billy: It I be with the crew you met already."))
        assertEquals("The suspect is using black lace to mask his identity.",
            GtOriginalInputGuard.prepare(
                "The suspect is using black lace to mask hist o D identity."))
        assertEquals("Lucia: Sure. I mean, I guess that depends.",
            GtOriginalInputGuard.prepare("Lucia: Sure. I, mean, I guess that depends."))
    }
}''',encoding="utf-8")
# Existing original-engine sources were NOT modified.
orig=root/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt"
assert orig.is_file()
assert "Always emit one end-to-end sample" in capture.read_text()
assert 'applicationId = "com.gamelingo.pro.gt1849.fast565"' in gradle.read_text()
print("Applied GameLingoPro 5.6.5 latency logging, careful second OCR policy and observed OCR word repair")
