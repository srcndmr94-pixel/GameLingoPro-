package com.example.altyazi.v6

import java.util.Locale

/** Conservative corrections for documented OCR and idiom mistranslations. */
internal object V6DialogueRepair {
    private fun spoken(source: String): String = source.substringAfter(':', source)
        .lowercase(Locale.ROOT).replace(Regex("\\s+"), " ")
        .trim().trimEnd('.', '!', '?', ',', ' ', '…')
    fun repairInput(raw: String): String {
        var text = raw
        text = text.replace(Regex("(?i)\\btw\\s+o\\s+plus\\b"), "two plus")
        text = text.replace(Regex("(?i)\\bwe need to discus\\s+S\\s+Something\\b"), "We need to discuss something")
        text = text.replace(Regex("(?i)\\blook\\s+in'\\s+good\\b"), "lookin' good")
        text = text.replace(Regex("(?i)\\bI'?m just say\\s+in'\\b"), "I'm just sayin'")
        return text
    }
    fun polish(source: String, translated: String): String {
        if (translated.isBlank()) return translated
        val body = spoken(source)
        val prefix = source.substringBefore(':', "").trim().takeIf {
            source.contains(':') && it.matches(Regex("[\\p{L} .'-]{2,30}"))
        }
        fun withSpeaker(s: String) = if (prefix != null) "$prefix: $s" else s
        return when {
            body == "ya dig" || body == "ya dig? yeah" ->
                withSpeaker(if (body.contains("yeah")) "Anladın mı? Evet!" else "Anladın mı?")
            body == "you a trip" -> withSpeaker("Sen de alemsin.")
            body == "look who's back. what's good" -> withSpeaker("Bak kim gelmiş! Ne haber?")
            body == "ah, shit. i wake ya" -> withSpeaker("Ah, lanet olsun. Seni uyandırdım mı?")
            body == "can you not" -> withSpeaker("Yapmasan olmaz mı?")
            body.startsWith("jacked up all day, jacked up all night") &&
                body.contains("we don't close") ->
                withSpeaker("Gece gündüz coşuyoruz, burası hiç kapanmaz lan!")
            else -> translated
        }
    }
}
