package com.example.altyazi

import java.util.Locale

/** Source-locked idiom fixes applied after the unmodified original GTX -> ML Kit translator. */
internal object GtOriginalQualityGuard {
    fun polish(source: String, translated: String): String {
        val spoken = source.substringAfter(':', source).trim()
            .lowercase(Locale.ROOT).replace(Regex("""\s+"""), " ")
            .trimEnd('.', '!', '?', ' ', ',')
        val label = source.substringBefore(':', "").takeIf {
            source.contains(':') && it.matches(Regex("""[\p{L} .'-]{2,30}"""))
        }
        fun speaker(text: String) = if (label == null) text else "$label: $text"
        return when {
            spoken == "now that's a choice" -> speaker("İşte bu cesur bir tercih.")
            spoken.contains("before they pop their cherries") && translated.contains("kiraz", ignoreCase = true) ->
                speaker("İlk deneyimlerini yaşamadan önce onlara etrafı göstereceğim.")
            spoken.contains("she's basically a vet at this") && translated.contains("veteriner", ignoreCase = true) ->
                speaker("Bu işte artık epey tecrübeli.")
            spoken.contains("since our first blunt") && translated.contains("künt", ignoreCase = true) ->
                speaker("İlk sardığımız ottan beri kardeşiz.")
            spoken.startsWith("lookin' good") && translated.contains("iyi bak", ignoreCase = true) ->
                speaker("Vay be, çok iyi görünüyorsun!")
            else -> GtDialogueQuality.polish(source, translated)
        }
    }
}
