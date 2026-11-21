#!/usr/bin/env python3
"""Patch only original GameLingoPro Kotlin OCR/dialogue pipeline; never replace app."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"
gate=src/"TranslationQualityGate.kt"
build=root/"app/build.gradle.kts"
if not all(p.is_file() for p in (cap,gate,build)):
    raise SystemExit("Missing original GameLingoPro Android project")
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise SystemExit("Wrong Android package: refusing changes")
helper=r'''package com.example.altyazi
import java.util.Locale
/** Conservative source-level OCR fixes, with no API or token calls. */
internal object ProTranscriptGuard {
    private val speaker=Regex("^\\s*(?:\\[([\\p{L} .'-]{2,28})\\]|([\\p{Lu}][\\p{L} .'-]{1,27}):)\\s*")
    private val objective=Regex("(?i)\\s+(?:go to|wait for|pull up next to|drive to|head to|talk to|meet with|return to)\\s+[\\p{L}\\p{N}'’ -]{3,76}\\.?$")
    private fun nameOf(t:String):String? {
        val m=speaker.find(t)?:return null
        return m.groupValues[1].ifBlank{m.groupValues[2]}.trim().lowercase(Locale.ROOT)
            .replace(Regex("\\s+")," ")
    }
    fun speakersCompatible(a:String,b:String):Boolean {
        val x=nameOf(a);val y=nameOf(b)
        return x==null||y==null||x==y
    }
    fun repairOcr(raw:String):String {
        if(raw.isBlank())return raw
        return raw.replace(Regex("(?i)\\bget all Njumpy\\b"),"get all jumpy")
            .replace(Regex("(?i)\\bit'?s fne\\b"),"it's fine")
            .replace(Regex("(?i)\\bA\\.KIA\\."),"A.K.A.")
            .replace(Regex("(?i)\\bwho'?s your triend\\b"),"who's your friend")
            .replace(Regex("(?i)\\bCompličated\\b"),"Complicated")
            .replace(Regex("\\bmy OWn\\b"),"my own")
            .replace(Regex("^\\s*Vickt(?=\\s*:)"),"Vicki")
            .replace(Regex("^\\s*Lucla(?=\\s*:)"),"Lucia")
    }
    /** Never mix a spoken dialogue with a separately displayed game mission. */
    fun separateObjective(source:String):String {
        if(speaker.find(source)==null)return source
        val m=objective.find(source)?:return source
        val before=source.substring(0,m.range.first).trimEnd()
        val spoken=before.substringAfter(':',before).trim()
        if(spoken.length<12||(before.lastOrNull()?.let{it in ".!?…"}!=true))return source
        return before
    }
    /** Warn on provable idiom errors; do not fabricate a replacement. */
    fun literalIdiom(source:String,translated:String):Boolean {
        val s=source.lowercase(Locale.ROOT)
        val t=translated.lowercase(Locale.forLanguageTag("tr-TR"))
        return ("brightest bulbs" in s && "ampul" in t) ||
            ("sounds wholesome" in s && "sağlıklı" in t) ||
            ("shady-ass shit" in s && "gölgeli" in t) ||
            ("baby daddy" in s && "baba" !in t) ||
            ("you better not be" in s && "gerektik" in t) ||
            ("deals out of the car wash" in s && "araba yıkama işini" in t) ||
            ("jumpy" in s && "njumpy" in t) ||
            ("get my own place" in s && "own" in t)
    }
}
'''
(src/"ProTranscriptGuard.kt").write_text(helper,encoding="utf-8")
def patch(path,old,new):
    t=path.read_text(encoding="utf-8")
    if new in t:return
    if old not in t:raise SystemExit("Source anchor missing: "+str(path)+" :: "+old[:95])
    path.write_text(t.replace(old,new,1),encoding="utf-8")
patch(cap,
 'val onarilmis = KonusanIkiNokta.isle(DeyimDuzelt.kaynakOnar(raw))',
 'val onarilmis = KonusanIkiNokta.isle(DeyimDuzelt.kaynakOnar(ProTranscriptGuard.repairOcr(raw)))')
patch(cap,'return ocrBirlesikDuzelt(collapsed2)',
 'return ProTranscriptGuard.separateObjective(ocrBirlesikDuzelt(collapsed2))')
patch(cap,
 'if (a.isEmpty() || b.isEmpty()) return a == b\n        // "Peter:',
 'if (a.isEmpty() || b.isEmpty()) return a == b\n        if (!ProTranscriptGuard.speakersCompatible(a, b)) return false\n        // "Peter:')
patch(cap,
 'if (similar(text, shownSource) || OcrOnar.ayniGurultulu(text, shownSource)) {',
 'if (similar(text, shownSource) || (ProTranscriptGuard.speakersCompatible(text, shownSource) && OcrOnar.ayniGurultulu(text, shownSource))) {')
patch(cap,
 'if (similar(text, translatingFor) || OcrOnar.ayniGurultulu(text, translatingFor)) {',
 'if (similar(text, translatingFor) || (ProTranscriptGuard.speakersCompatible(text, translatingFor) && OcrOnar.ayniGurultulu(text, translatingFor))) {')
patch(cap,
 'tag.contains("YZ") && OcrOnar.ayniGurultulu(source, translatingFor)',
 'tag.contains("YZ") && ProTranscriptGuard.speakersCompatible(source, translatingFor) &&\n            OcrOnar.ayniGurultulu(source, translatingFor)')
patch(gate,
 '        if (onlineAgain.containsMatchIn(s) && backupMistranslated.containsMatchIn(t))',
 '        if (ProTranscriptGuard.literalIdiom(s, t)) return Problem.LITERAL_IDIOM\n        if (onlineAgain.containsMatchIn(s) && backupMistranslated.containsMatchIn(t))')
patch(cap,
 '''        } else if (issue != null && LiveEnginePolicy.secondOpinionForWarning(prefs.ceviriBicimi) &&
            ff != null && ff.hazir) {''',
 '''        } else if (issue == TranslationQualityGate.Problem.LITERAL_IDIOM &&
            LiveEnginePolicy.secondOpinionForWarning(prefs.ceviriBicimi)) {
            // Use the existing offline engine at most once; no extra API/token usage.
            val alternative = try { f?.translate(body) } catch (_: Exception) { null }
            val approved = alternative?.let(::render)
            if (!approved.isNullOrBlank() &&
                TranslationQualityGate.check(body, approved) == null) {
                duzgun = approved
                log("DEYİM DÜZELTİLDİ: yerel alternatif kalite kontrolünü geçti")
            } else {
                log("DEYİM UYARISI: güvenilir alternatif yok; uyarılı çeviri hafızaya alınmaz")
            }
        } else if (issue != null && LiveEnginePolicy.secondOpinionForWarning(prefs.ceviriBicimi) &&
            ff != null && ff.hazir) {''')
patch(build,'versionCode = 20261121','versionCode = 20261122')
patch(build,'versionName = "GameLingoPro-2.0-HUD"','versionName = "GameLingoPro-2.1-OCR"')
assert 'ProTranscriptGuard.speakersCompatible' in cap.read_text()
assert 'ProTranscriptGuard.literalIdiom' in gate.read_text()
assert 'applicationId = "com.gamelingo.pro"' in build.read_text()
print("GameLingoPro original OCR, speaker repeats and idiom quality patched")
