#!/usr/bin/env python3
from pathlib import Path
r=Path("."); src=r/"app/src/main/java/com/example/altyazi";tests=r/"app/src/test/java/com/example/altyazi"
def rep(f,a,b):
 s=f.read_text(encoding="utf-8")
 n=s.count(a)
 if n!=1: raise RuntimeError(f"Missing/duplicate anchor ({n}) {f}: {a[:70]}")
 f.write_text(s.replace(a,b,1),encoding="utf-8")

guard=src/"GtOriginalInputGuard.kt"
rep(guard,'    /** Defer obviously clipped OCR until a subsequent better read. */',r'''
    /** Reject strong OCR corruption, not ordinary contractions, proper names or slang. */
    fun hasSevereOcrNoise(raw: String): Boolean {
        val s=raw.trim()
        if(s.isEmpty()) return false
        if(Regex("""(?i)^(?:bee\s+t?slap:\s*(?:ann,?\s+u\s+sn\s+ouida|wnen\s+[ut]\s+net)|wnen\s+t\s+net\s+nis|toy[chgs]{3,}\s+n\s+shat)""").containsMatchIn(s)) return true
        val words=s.split(Regex("""\s+""")).map {
            it.trim('.', ',', '!', '?', ':', ';', '\'', '’', '"', '(', ')')
        }.filter { it.isNotBlank() }
        if(words.size < 4) return false
        val singles=words.count { it.length==1 && it.lowercase(Locale.ROOT) !in setOf("i","a") && it.single().isLetter() }
        val midCaps=words.count { w -> w.length>3 && w.drop(1).dropLast(1).any { it.isUpperCase() } &&
            w.any { it.isLowerCase() } && w !in setOf("McDonald","MacDonald") }
        return singles>=2 || (singles>=1 && midCaps>=1) || midCaps>=3
    }

    /** Good single-frame captions can use the original stabilizer immediately.
     * Damaged captions must wait for a better independent frame.
     */
    fun canFastTrack(raw: String): Boolean {
        val s=raw.trim()
        if(s.length !in 24..170 || hasSevereOcrNoise(s) || looksClipped(s) || isHudObjective(s)) return false
        val words=s.split(Regex("""\s+""")).filter { it.any { ch -> ch.isLetter() } }
        if(words.size !in 6..32) return false
        val (speaker,body)=splitSpeaker(s)
        if(speaker==null && body.lastOrNull() !in listOf('.','?','!','…')) return false
        if(Regex("""(?i)\b(?=[a-z0-9]*[a-z])(?=[a-z0-9]*\d)[a-z0-9]{4,}\b""").containsMatchIn(s)) return false
        return true
    }

    /** Defer obviously clipped OCR until a subsequent better read. */''')
rep(guard,'        s = s.replace(Regex("""(?i)\\bABilly:\\s*"""), "Billy: ")',
r'''        s = s.replace(Regex("""(?i)\bABilly:\s*"""), "Billy: ")
        s = s.replace(Regex("""(?i)^Bee\s*T?Slap\s*:|^Bee\s+Slap\s*:"""), "Beefslap:")
        s = s.replace(Regex("""(?i)^Toychgs\s+n\s+Shat\s+happened\s+to\s+your\s+car\s*\?"""), "What happened to your car?")
        s = s.replace(Regex("""(?i)\btw\s+O\b(?=\s*[,?.!])"""), "two")
        s = s.replace(Regex("""(?i)\bgro\s+W\s+up\b"""), "grow up")''')
cap=src/"CaptureService.kt"
rep(cap,'            if(candidate.isNotEmpty() && lastOcrRaw.isNotEmpty())handleText(lastOcrRaw)',
'''            // Visually identical captured frame counts as the second stabilizer sample.
            if (fingerprintSame && lastOcrRaw.isNotEmpty()) handleText(lastOcrRaw)''')
rep(cap,'        val text = if (raw.isBlank() || GtDialogueQuality.stageOnly(raw)) "" else {',
'''        val text = if (raw.isBlank() || GtDialogueQuality.stageOnly(raw) ||
            GtOriginalInputGuard.hasSevereOcrNoise(raw)) {
            if (raw.isNotBlank() && GtOriginalInputGuard.hasSevereOcrNoise(raw))
                log("GT OCR ÇOK BOZUK, YENİ KARE BEKLENİYOR: " + raw.take(85))
            ""
        } else {''')
rep(cap,
'''                                    log("Denemeler seyrekleşerek sürecek. Ekran duruyorsa " +
                                        "(oyundan çıkılmış, menüde beklenmiş) kare gelmemesi normaldir.")''',
'''                                    log("KARE GELMİYOR: Tek uygulama ekran paylaşımı bitmiş olabilir. " +
                                        "Devam ederse ÇEVİRİYİ DURDUR → BAŞLAT ile ekran paylaşımını yeniden seçin.")''')
meter=src/"GtLatencyMeter.kt"
rep(meter,'        val stamp = records.getOrPut(k) { Stamp(clockMs(), 0L) }\n        stamp.started = clockMs()',
'''        // Source may be changed by upstream OCR normalization: unknown != zero.
        val stamp = records.getOrPut(k) { Stamp(-1L, -1L) }
        stamp.started = clockMs()''')
rep(meter,'            waitBeforeTranslationMs = max(0L, started - (stamp.readAt + stamp.ocrMs)),',
'''            waitBeforeTranslationMs = if (stamp.readAt >= 0) max(0L, started - (stamp.readAt + stamp.ocrMs)) else -1L,''')
rep(meter,'            totalMs = max(0L, now - stamp.readAt)',
'''            totalMs = if (stamp.readAt >= 0) max(0L, now - stamp.readAt) else -1L''')
rep(cap,'                            log("GT GECİKME: OCR " + metrics.ocrMs + " ms · OCR→motor " +\n                                metrics.waitBeforeTranslationMs + " ms (kuyruk " +',
'''                            log("GT GECİKME: OCR " + (if (metrics.ocrMs < 0) "ölçülemedi" else metrics.ocrMs.toString() + " ms") +
                                " · OCR→motor " + (if (metrics.waitBeforeTranslationMs < 0) "ölçülemedi" else metrics.waitBeforeTranslationMs.toString() + " ms") +
                                " (kuyruk " +''')
rep(cap,'                                " ms · gösterim " + metrics.displayMs + " ms · toplam " +\n                                metrics.totalMs + " ms · eski kuyruk atlandı " +',
'''                                " ms · gösterim " + metrics.displayMs + " ms · toplam " +
                                (if (metrics.totalMs < 0) "ölçülemedi" else metrics.totalMs.toString() + " ms") +
                                " · eski kuyruk atlandı " +''')
pipe=src/"GtOriginalDialoguePipeline.kt"
rep(pipe,'        originalPipeline.onRead(if (text.isBlank()) emptyList() else text.lines(), null)',
'''        val lines=if (text.isBlank()) emptyList() else text.lines()
        originalPipeline.onRead(lines,null)
        if (GtOriginalInputGuard.canFastTrack(text) &&
            !com.gametranslator.gametranslator_mobile.core.SubtitleStabilizer.endsSentence(text)) {
            originalPipeline.onRead(lines,null)
        }''')
grad=r/"app/build.gradle.kts"
rep(grad,'applicationId = "com.gamelingo.pro.gt1849.fast565"','applicationId = "com.gamelingo.pro.gt1849.fast566"')
rep(grad,'versionName = "GameLingoPro-5.6.5-GTFastOCR"','versionName = "GameLingoPro-5.6.6-GTStableFast"')
rep(grad,'versionCode = 20261236','versionCode = 20261237')
rep(r/"app/src/main/res/values/strings.xml",'<string name="app_name">GameLingoPro GT Fast OCR</string>',
'<string name="app_name">GameLingoPro GT StableFast</string>')
rep(tests/"GtBrandIdentity522Test.kt",'GameLingoPro GT Fast OCR</string>','GameLingoPro GT StableFast</string>')
(tests/"GtRealtime566Test.kt").write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtRealtime566Test {
 @Test fun fastPathRejectsDamagedText() {
  assertTrue(GtOriginalInputGuard.canFastTrack("Beefslap: Then one day you wake up and realize"))
  assertFalse(GtOriginalInputGuard.canFastTrack("Drive Beefslap to the race track"))
  val damaged="Bee TSlap: WNen UMet ni Sass ne Was Jumplng OT ladders Int O kiddie pools full of snakes"
  assertTrue(GtOriginalInputGuard.hasSevereOcrNoise(damaged))
  assertFalse(GtOriginalInputGuard.canFastTrack(damaged))
  assertFalse(GtOriginalInputGuard.hasSevereOcrNoise("Beefslap: Fuckin' right! You are like a philosopher or some shit."))
 }
 @Test fun observedOcrRepairs() {
  assertEquals("Beefslap: Yeah. They grow up so fast.",GtOriginalInputGuard.prepare("Bee Slap: Yeah. They gro W up so fast."))
  assertEquals("What happened to your car?",GtOriginalInputGuard.prepare("Toychgs n Shat happened to your car?"))
  assertEquals("Jason: There's room on that wheel for two, right?",GtOriginalInputGuard.prepare("Jason: There's room on that wheel for tw O, right?"))
 }
 @Test fun missingTimestampIsNotZeroMs() {
  var now=500L;val m=GtLatencyMeter{now}
  m.translationStarted("Normalized source",0);now=590;m.translationEnded("Normalized source");now=600
  val result=m.displayed("Normalized source")!!
  assertEquals(-1L,result.ocrMs);assertEquals(-1L,result.totalMs)
  assertEquals(90L,result.translationMs)
 }
}''',encoding="utf8")
assert (r/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt").exists()
print("5.6.6 GTStableFast ready; upstream GameTranslator preserved.")
