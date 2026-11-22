#!/usr/bin/env python3
"""GameLingoPro 4.8: correct OCR dialogue noise and narrow, verifiable idioms.

Apply AFTER the successful 4.7 colored build. No change to GT/GTX engine
order, OCR boxes, subtitle colors, display lifetime, HUD or package name.
"""
from pathlib import Path
import re
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
tests=root/'app/src/test/java/com/example/altyazi'
engine=src/'GtNativeEngine.kt'
capture=src/'CaptureService.kt'
build=root/'app/build.gradle.kts'
view=src/'GtExactOverlay.kt'
for p in (engine,capture,build,view,src/'GtSelectedMapPanel.kt'):
    if not p.is_file():raise RuntimeError('Missing 4.7 source: '+str(p))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Wrong Android package')
if 'Color.rgb(255,203,86)' not in view.read_text() or \
   'processGameNotice(full,noticeProbe)' not in capture.read_text():
    raise RuntimeError('4.7 full translations and colors must remain in place')
if 'gtQuestBoxesOnly' in capture.read_text():
    raise RuntimeError('Disabled translation regions must not be reintroduced')

def once(path,old,new):
    content=path.read_text(encoding='utf-8')
    count=content.count(old)
    if count!=1:raise RuntimeError(
        f'{path.name}: source mismatch (expected 1 anchor, got {count}): {old[:100]}')
    path.write_text(content.replace(old,new,1),encoding='utf-8')

(src/'GtDialogueQuality.kt').write_text(r'''package com.example.altyazi

import java.util.Locale

/**
 * Conservative English OCR normalization and short spoken-idiom repair.
 * No lookup by game title or entire scripted scene; never invent context.
 * Quality repair is independent of the GTX/ML Kit translator ordering.
 */
internal object GtDialogueQuality {
    fun repairOcr(raw:String):String {
        var s=raw
        // Spoken speaker tag is *not* translated and should not oscillate.
        s=s.replace(Regex("""(?i)^Dr\s+Bill:"""),"Dr. Bill:")
        s=s.replace(Regex("""(?i)^Dunk\s+(?=Dr\.?\s*Bill[,!])"""),"Dunk: ")
        // Leading capital I is often seen as 1/T on dark game subtitles.
        // Limit repairs to highly specific neighboring English words.
        s=s.replace(Regex("""(?i)(:\s*)1(?=\s*,\s*(?:uh|um)\b)""")) {
            it.groupValues[1]+"I"
        }
        s=s.replace(Regex("""(?i)-[TI](?=\s+forgot\b)"""),"I")
        s=s.replace(Regex("""(?i)\b(?:I1|1I)(?=\s+will\b)"""),"I")
        s=s.replace(Regex("""(?i)\bTm-(?=I'm\b)"""),"")
        s=s.replace(Regex("""(?i)\bYouire\b"""),"You're")
        s=s.replace(Regex("""(?i)\bIll(?=\s+(?:sort|be|call|take)\b)"""),"I'll")
        s=s.replace(Regex("""(?i)\bDont\s+knowe\b"""),"Don't know")
        s=s.replace(Regex("""(?i)(how many\s+)ser\s+[i1l]\s+pts\b""")){
            it.groupValues[1]+"scripts"
        }
        s=s.replace(Regex("""(?i)\bcạn\b"""),"can")
        s=s.replace(Regex("""(?i)\bDřive\b"""),"Drive")
        return s.replace(Regex("""\s{2,}""")," ").trim()
    }

    fun polish(source:String, translation:String):String {
        val english=repairOcr(source).lowercase(Locale.ROOT)
            .trim().replace(Regex("""\s+""")," ")
        val turkish=translation.trim()
        // English dialogue idioms that GTX translates literally in the
        // recorded session. Only exact short phrases receive fixed rewrites.
        if(english.matches(Regex("""don't sweat[.!…]*""")))
            return "Takma kafana."
        if(english.matches(Regex("""she(?:'|’)s pedigree[.!…]*""")))
            return "O safkan."
        if(english.matches(Regex("""any minute!\s*like,?\s*soon-soon[.!…]*""")))
            return "Her an! Çok yakında!"
        if(english.matches(Regex("""i(?:'|’)m out[.!]?\s*what[!?.…]*""")))
            return "Ben bu işte yokum. Ne?"

        var result=turkish
        // Do not add terms of endearment absent from the original.
        if(english.matches(Regex("""okay[.!…]*""")) &&
            result.contains(Regex("""(?i)\b(?:aşkım|sevgilim|canım)\b""")))
            result="Tamam..."
        // Preserve the meaning of "have" vs "bought" in recorded dialogue.
        if(english.contains("i know you got 'em")) {
            result=result.replace(
                Regex("""(?i)\bonları aldığını biliyorum\b"""),
                "Elinde olduklarını biliyorum")
        }
        // "hand jobs" must not become the craft-related "el işi".
        if(english.contains("hand jobs")) {
            result=result.replace(Regex("""(?i)\bel işi yapacaksın\b"""),
                "başkalarını elle tatmin edeceksin")
        }
        return result
    }
}
''',encoding='utf-8')

# Repair source *before* duplicate comparison, not just after sending to GTX.
# Equivalent OCR forms are deduplicated without weakening different-speech checks.
once(capture,
'''            adiAyir(clean(raw)), android.os.SystemClock.elapsedRealtime())''',
'''            GtDialogueQuality.repairOcr(adiAyir(clean(raw))),
            android.os.SystemClock.elapsedRealtime())''')

once(engine,
'''        val text=OcrNoise.clean(raw).trim().ifEmpty { raw.trim() }''',
'''        val text=GtDialogueQuality.repairOcr(
            OcrNoise.clean(raw).trim().ifEmpty { raw.trim() })''')

once(engine,
'''        return if(label.isEmpty())translated else "$label $translated"''',
'''        val fluent=GtDialogueQuality.polish(body,translated)
        return if(label.isEmpty())fluent else "$label $fluent"''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtDialogueQuality48Test.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
class GtDialogueQuality48Test {
    @Test fun ocrMisreadIAndScriptAreRepairedBeforeDedup() {
        assertEquals("Dr. Bill: I, uh, I don't have any change.",
            GtDialogueQuality.repairOcr("Dr Bill: 1, uh, I don't have any change."))
        assertEquals("Dr. Bill: Hey, uh, I forgot my wallet.",
            GtDialogueQuality.repairOcr("Dr. Bill: Hey, uh, -T forgot my wallet."))
        assertEquals("Dunk: Dr. Bill, it's Dunk. How many scripts you write for me?",
            GtDialogueQuality.repairOcr(
                "Dunk Dr. Bill, it's Dunk. How many ser I pts you write for me?"))
        assertEquals("Dr. Bill: I'm-I'm here to see Declan.",
            GtDialogueQuality.repairOcr("Dr Bill: Tm-I'm-I'm here to see Declan."))
        assertEquals("I'll sort this whole thing out.",
            GtDialogueQuality.repairOcr("Ill sort this whole thing out."))
    }
    @Test fun fixesRecordedDialogueIdiomsWithoutRewritingUnrelatedSentences() {
        assertEquals("Takma kafana.",GtDialogueQuality.polish("Don't sweat.","Terleme."))
        assertEquals("O safkan.",GtDialogueQuality.polish("She's pedigree.","O bir soyağacı."))
        assertEquals("Ben bu işte yokum. Ne?",
            GtDialogueQuality.polish("I'm out. What?","Ben dışarıdayım. Ne?"))
        assertEquals("Tamam...",GtDialogueQuality.polish("Okay...","Tamam aşkım..."))
        assertEquals("Hızlıca terlemeden gel.",GtDialogueQuality.polish(
            "Run without sweat!","Hızlıca terlemeden gel."))
        assertEquals("Elinde olduklarını biliyorum.",GtDialogueQuality.polish(
            "I know you got 'em","Onları aldığını biliyorum."))
    }
    @Test fun noTokenCostAndSpeakerTagPreserved()= runBlocking {
        var calls=0
        val result=GtNativeEngine.translateWith("Dunk: Don't sweat.",
            { calls++; "Terleme." }, { "Yedek." })
        assertEquals("Dunk: Takma kafana.",result)
        assertEquals(1,calls)
    }
    @Test fun originalUserColorsHudAndEnginesAreNotTouched() {
        val capture=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val render=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        val engine=java.io.File("src/main/java/com/example/altyazi/GtNativeEngine.kt").readText()
        assertTrue(capture.contains("processSubtitle(full)"))
        assertTrue(capture.contains("processGameNotice(full,noticeProbe)"))
        assertTrue(capture.contains("processMapDetailPanels(full,noticeProbe)"))
        assertFalse(capture.contains("gtQuestBoxesOnly"))
        assertTrue(render.contains("Color.rgb(255,203,86)"))
        assertTrue(render.contains("Color.rgb(105,232,242)"))
        assertTrue(engine.contains("GoogleGtxTranslator"))
        assertTrue(engine.contains("MlKitTranslator"))
    }
}
''',encoding='utf-8')

v=build.read_text(encoding='utf-8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261220',v,count=1)
if n!=1:raise RuntimeError('versionCode missing')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-4.8-DialogueQuality"',v,count=1)
if n!=1:raise RuntimeError('versionName missing')
build.write_text(v,encoding='utf-8')
print("GameLingoPro 4.8: OCR and short dialogue quality; original UI, colors, translation routing and duplicate filter retained")
