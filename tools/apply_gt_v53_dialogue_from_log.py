#!/usr/bin/env python3
"""GameLingoPro 5.3: preserve 5.2.2 identity, repair logged dialogue."""
from pathlib import Path
import re,sys
p=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=p/"app/src/main/java/com/example/altyazi"
quality=src/"GtDialogueQuality.kt"
engine=src/"GtNativeEngine.kt"
service=src/"CaptureService.kt"
build=p/"app/build.gradle.kts"
tests=p/"app/src/test/java/com/example/altyazi"
if "GameLingoPro-5.2.2-BrandFix" not in build.read_text():
    raise RuntimeError("Brand script must run first")
def replace1(file,a,b):
    s=file.read_text(encoding="utf-8")
    n=s.count(a)
    if n!=1:raise RuntimeError(str(file)+": anchor count "+str(n)+": "+a[:70])
    file.write_text(s.replace(a,b,1),encoding="utf-8")
replace1(quality,
'''internal object GtDialogueQuality {
    fun repairOcr(raw:String):String {''',
'''internal object GtDialogueQuality {
    private val soundOrStage=Regex(
        """(?i)\\[(?:[^\\]]{1,34}\\b(?:music|sighs|groans|""" +
        """crackles|beeps|sparks|swells)\\b|sinisterly|high pitched voice)\\]\\)?\\s*""")
    fun removeSceneDirections(raw:String):String =
        raw.replace(soundOrStage,"").trim()
    fun stageOnly(raw:String):Boolean =
        raw.isNotBlank() && removeSceneDirections(raw).isBlank()
    fun repairOcr(raw:String):String {''')
replace1(quality,
'''        s=s.replace(Regex("""(?i)\\bDřive\\b"""),"Drive")
        return s.replace(Regex("""\\s{2,}""")," ").trim()''',
'''        s=s.replace(Regex("""(?i)\\bDřive\\b"""),"Drive")
        s=s.replace(Regex("""(?i)\\bho\\s+[wW]\\s+many\\b"""),"how many")
        s=s.replace(Regex("""(?i)\\bWet(?=,?\\s+that's\\s+not\\s+a\\s+problem)"""),"Well")
        // This ungrammatical read-back appeared just after the correct line.
        s=s.replace(Regex("""(?i)\\bWe\\s+not\\s+that\\s+covered\\b"""),
            "We got that covered")
        return s.replace(Regex("""\\s{2,}""")," ").trim()''')
replace1(quality,
'''        if(english.matches(Regex("""don't sweat[.!…]*""")))
            return "Takma kafana."''',
'''        if(english.matches(Regex("""don't sweat[.!…]*""")))
            return "Takma kafana."
        if(english.matches(Regex("""now then[.!…]*""")))
            return "Pekâlâ."
        if(english.matches(Regex("""fine[.!…]*""")) &&
            turkish.equals("İyi.",ignoreCase=true))
            return "Peki."
        if(english.matches(Regex("""whoa,?\\s+badass[.!…]*""")))
            return "Vay be, müthiş!"
        val emptyThreat=Regex(
            """or[,.…\\s]+([a-z][a-z'-]*) can come back to absolutely nothing[.!…]*""")
            .matchEntire(english)
        if(emptyThreat!=null) {
            val name=source.split(Regex("""\\s+"""))
                .firstOrNull { it.equals(emptyThreat.groupValues[1],ignoreCase=true) }
                ?: emptyThreat.groupValues[1]
            return "Yoksa "+name+" döndüğünde ortada hiçbir şey kalmayacak!"
        }
        val yearly=Regex("""got a good (\\d+) this year,? sir[.!…]*""")
            .matchEntire(english)
        if(yearly!=null)
            return "Bu yıl tam "+yearly.groupValues[1]+" tane, efendim."''')
replace1(quality,
'''        var result=turkish
        // Do not add terms of endearment absent from the original.''',
'''        var result=turkish
        if(english.contains("pound it"))
            result=result.replace(Regex("""(?i)\\bvur onu[.!]?"""),
                "Yumruk tokuşturalım!")
        if(english.contains("make a fucking commercial"))
            result=result.replace(Regex("""(?i)hadi lanet bir reklam yapalım"""),
                "hadi şu lanet reklamı çekelim")
        // Do not add terms of endearment absent from the original.''')
replace1(engine,
'''        val clean=normalize(raw)
        if(clean.isEmpty())return null''',
'''        val clean=GtDialogueQuality.removeSceneDirections(normalize(raw))
        if(clean.isEmpty())return null''')
replace1(engine,
'''        val body=if(label.isEmpty())clean else clean.drop(label.length).trim()
        if(body.isEmpty())return null''',
'''        val body=(if(label.isEmpty())clean else clean.drop(label.length).trim())
            .trimStart('-',' ')
        if(body.isEmpty())return null''')
replace1(service,
'''    private fun handleText(raw: String) {
        // Öğrenilmiş konuşan adını ayır:''',
'''    private fun handleText(raw: String) {
        if(GtDialogueQuality.stageOnly(raw)) {
            dustu(raw,"yalnız müzik/sahne notu")
            return
        }
        // Öğrenilmiş konuşan adını ayır:''')
tests.mkdir(parents=True,exist_ok=True)
(tests/"GtUserDialogue53Test.kt").write_text(r'''package com.example.altyazi
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import java.io.File

class GtUserDialogue53Test {
    @Test fun pureSoundScenesDoNotUseTranslationEngines()=runBlocking {
        var api=0
        for(raw in listOf("[ominous music]","[grand music swells]",
          "[camera crackles] [haunting music]")) {
            assertNull(GtNativeEngine.translateWith(raw,
              { api++; "hatali" },{ api++; "yedek" }))
        }
        assertEquals(0,api)
    }
    @Test fun stageDirectionsRemovedButSpeakerNameRetained()=runBlocking {
        var body=""
        val out=GtNativeEngine.translateWith(
            "[camera beeps] [Adam] --When you take her out for the fifth time",
            { body=it; "Onu beşinci kez dışarı çıkardığında" },
            {"yedek"})
        assertEquals("When you take her out for the fifth time",body)
        assertEquals("[Adam] Onu beşinci kez dışarı çıkardığında",out)
        assertEquals("Fine.",
            GtDialogueQuality.removeSceneDirections("[Vaggie sighs]) Fine."))
    }
    @Test fun naturalTurkishAgainstExactUserLogErrors() {
        assertEquals("Vay be, müthiş!",
            GtDialogueQuality.polish("Whoa, Badass!","Vay, Baş belası!"))
        assertEquals("Harika iş, tehlikeli memeler! Yumruk tokuşturalım!",
            GtDialogueQuality.polish("Awesome job, danger tits! Pound it.",
            "Harika iş, tehlikeli memeler! Vur onu."))
        assertEquals("Pekâlâ.",
            GtDialogueQuality.polish("Now then.","Şimdi o zaman."))
        assertEquals("Yoksa Charlie döndüğünde ortada hiçbir şey kalmayacak!",
            GtDialogueQuality.polish(
            "Or... Charlie can come back to absolutely nothing!",
            "Veya... Charlie kesinlikle hiçbir şeye geri dönebilir!"))
        assertEquals("Bu yıl tam 275 tane, efendim.",
            GtDialogueQuality.polish("Got a good 275 this year, sir.",
            "Bu yıl iyi bir 275 aldım efendim."))
    }
    @Test fun ocrRepairsNarrowAndNegationPreserved() {
        assertEquals("Lute, how many demons did you kill this year?",
            GtDialogueQuality.repairOcr("Lute, ho W many demons did you kill this year?"))
        assertEquals("Ohh! Well, that's not a problem! We got that covered.",
            GtDialogueQuality.repairOcr(
            "Ohh! Wet, that's not a problem! We not that covered."))
        assertEquals("We are not buying it.",
            GtDialogueQuality.repairOcr("We are not buying it."))
    }
    @Test fun allPriorRegionsAndNewBrandStillEnabled() {
        val ui=File("src/main/res/layout/activity_main.xml").readText()
        val c=File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(ui.contains("GAMELINGOPRO · ALTYAZI ALANLARI"))
        assertTrue(c.contains("processSubtitle(full)"))
        assertTrue(c.contains("processGameNotice(full,noticeProbe)"))
        assertTrue(c.contains("processMapDetailPanels(full,noticeProbe)"))
        assertFalse(c.contains("gtQuestBoxesOnly"))
    }
}
''',encoding='utf-8')
v=build.read_text(encoding='utf-8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
    r'\g<1>versionCode = 20261227',v,count=1)
if n!=1:raise RuntimeError("version code missing")
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-5.3-BrandAndDialogue"',v,count=1)
if n!=1:raise RuntimeError("version name missing")
build.write_text(v,encoding='utf-8')
print("5.3: sound effects excluded; new dialogue corrections, GameLingoPro branding")
