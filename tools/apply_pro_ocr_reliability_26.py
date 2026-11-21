#!/usr/bin/env python3
"""GameLingoPro: prevent lost continuation and outdated translation work."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"; ass=src/"ProSubtitleAssembler.kt"
gate=src/"TranslationQualityGate.kt"; build=root/"app/build.gradle.kts"
assert all(f.exists() for f in (cap,ass,gate,build))
assert 'applicationId = "com.gamelingo.pro"' in build.read_text()
def replace(file,old,new):
    s=file.read_text()
    if s.count(old)!=1: raise RuntimeError(f"Unexpected {file.name}: {s.count(old)} matches for {old[:60]}")
    file.write_text(s.replace(old,new,1))

replace(ass,'''            return Regex("""(?i)\b(?:and|but|while|although|because|with|to|for|if|or|then|now|she's|he's|it's|they're|we're|i'm)\s*$""").containsMatchIn(s)''',
'''            return Regex("""(?i)\b(?:and|but|while|although|because|with|to|for|if|or|then|now|she's|he's|it's|they're|we're|i'm|the|a|an|of|at|in|on|from|by|his|her|their|our|this|that|is|are|were|was|did|do|does|would|could|should|will|has|have)\s*$""").containsMatchIn(s) ||
                (s.length > 68 && Regex("""(?i)\b(?:and|but|or)\s+(?:(?:\p{L}+[ '’]*){1,4})$""").containsMatchIn(s)) ||
                Regex("""(?i)\b(?:and|but)\s+[\p{L}-]*ing\s*$""").containsMatchIn(s)''')
replace(ass,"if(wordCount(previous)-wordCount(next)<2)return false",
            "if(wordCount(previous)-wordCount(next)<1)return false")
replace(cap,'''        val gerekenOkuma = if (text.trimEnd().endsWith(",")) 2
            else if (tamamGorunuyor && SubtitlePreparation.confidentFirstRead(text)) 1 else 2''',
'''        val gerekenOkuma = if (text.length > 88 ||
            ProSubtitleAssembler.likelyContinued(text) || text.trimEnd().endsWith(",")) 2
            else if (tamamGorunuyor && SubtitlePreparation.confidentFirstRead(text)) 1 else 2''')
replace(cap,"android.os.SystemClock.elapsedRealtime() - candidateStartedAtMs < 1000L) return",
            "android.os.SystemClock.elapsedRealtime() - candidateStartedAtMs < 1250L) return")
replace(cap,'''        if (ProSubtitleAssembler.likelyContinued(text) &&
            android.os.SystemClock.elapsedRealtime() - candidateStartedAtMs < 1250L) return''',
'''        if (ProSubtitleAssembler.likelyContinued(text) &&
            android.os.SystemClock.elapsedRealtime() - candidateStartedAtMs < 1250L) {
            if (prefs.diagnostics && candidateSeen == 2)
                log("EKSİK CÜMLE BEKLENİYOR: ${text.take(90)}")
            return
        }''')
replace(cap,'''        if (runId != null && !subtitleGeneration.isCurrent(runId)) {
            log("ESKİ İSTEK ATLANDI: ${source.take(65)}")
            return
        }
        // All producers (dictionary, memory, Google, Firefox, device AI, bridge)
        // converge here. Do not poison caches with structurally suspicious output.
        val outputIssue = TranslationQualityGate.check(source, value)''',
'''        // Never show a stale result over a different active subtitle.
        // Preserve valid late translations in cache for repeated game prompts.
        val outputIssue = TranslationQualityGate.check(source, value)
        if (runId != null && !subtitleGeneration.isCurrent(runId)) {
            if (remember && outputIssue == null && !value.startsWith("⚠")) {
                saveToMemory(source, value, tag)
                log("ESKİ İSTEK HAFIZAYA ALINDI: ${source.take(65)}")
            } else log("ESKİ İSTEK EKRANA BASILMADI: ${source.take(65)}")
            return
        }''')
replace(cap,'''                        bandImza = null
                        overlay.clearLabels()''',
'''                        bandImza = null
                        proSubtitleAssembler.clear()
                        candidate = ""
                        candidateSeen = 0
                        lastOcrRaw = ""
                        overlay.clearLabels()''')
replace(gate,'''        if (s.count { it == '?' } >= 2 && t.count { it == '?' } < s.count { it == '?' })
            return Problem.MISSING_QUESTION''',
'''        if (s.count { it == '?' } >= 2 && t.count { it == '?' } < s.count { it == '?' })
            return Problem.MISSING_QUESTION
        // A long English contrastive clause must not simply vanish.
        if (Regex("""(?i)\bbut\s+\w+""").containsMatchIn(s) &&
            !Regex("""(?iu)\b(?:ama|fakat|ancak|lakin|oysa|halbuki)\b""").containsMatchIn(t) &&
            !t.contains("yine de",true) && !t.contains("buna rağmen",true) &&
            s.length > 60) return Problem.MISSING_DETAIL''')
s=build.read_text()
s,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261127',s,count=1)
if n!=1:raise RuntimeError("versionCode missing")
s,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',r'\g<1>versionName = "GameLingoPro-2.6-OCR-Flow"',s,count=1)
if n!=1:raise RuntimeError("versionName missing")
if 'testImplementation("junit:junit:4.13.2")' not in s:
    s=s.replace("dependencies {",'dependencies {\n    testImplementation("junit:junit:4.13.2")',1)
build.write_text(s)
unit=root/"app/src/test/java/com/example/altyazi/ProSubtitleFlowTest.kt"
unit.parent.mkdir(parents=True,exist_ok=True)
unit.write_text("""package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class ProSubtitleFlowTest {
    @Test fun detectsTruncatedSentences() {
        assertTrue(ProSubtitleAssembler.likelyContinued("The map points to the northern mountains... and so did the"))
        assertTrue(ProSubtitleAssembler.likelyContinued("I was planning to eavesdrop, but that henchman of his"))
        assertTrue(ProSubtitleAssembler.likelyContinued("Press +to [Drink], restoring Sha-Chi and entering"))
        assertFalse(ProSubtitleAssembler.likelyContinued("Please... end my suffering..."))
    }
    @Test fun expandedOcrOnlyAcceptsSameBeginning() {
        val first="Landing an attack inflicts Bleeding and builds the enemy's Bleed Gauge."
        val full=first+" When the gauge is full, it triggers Blood Loss."
        assertEquals(full,ProSubtitleAssembler.fuller(first,full))
        assertEquals(first,ProSubtitleAssembler.fuller(first,"Sweeping Blade consumes 1 point."))
    }
    @Test fun glitchDoesNotReplaceCleanText() {
        val a=ProSubtitleAssembler()
        a.accept("Go on...let me rest...",100L)
        assertEquals("Go on...let me rest...",a.accept("Go onsoolet merest...",250L))
    }
    @Test fun separateSpeakersAreNotGlued() {
        val a=ProSubtitleAssembler()
        a.accept("Vicki: Wait for me.",100L)
        assertEquals("Lucia: Let's go.",a.accept("Lucia: Let's go.",300L))
    }
}
""")
print("GameLingoPro 2.6 patch and 4 JUnit regressions installed")
