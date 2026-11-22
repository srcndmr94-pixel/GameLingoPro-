package com.example.altyazi.v6

/**
 * V6's deterministic, dependency-free shadow audit of the OCR stream.
 *
 * The original GameTranslator engine still decides what reaches the overlay.
 * The audit runs alongside it so we can establish a replay baseline without
 * risking live subtitle loss. Once corpus and on-device metrics support a
 * decision, routing can move behind this boundary.
 */
internal object V6CaptionAudit {
    enum class Kind { EMPTY, OBJECTIVE, DIALOGUE, OVERLAP, UNLABELLED, SUSPECT }

    internal data class Observation(
        val kind: Kind,
        val candidate: String,
        val speaker: String? = null,
        val note: String = ""
    )

    private val cue = Regex("""(?<![\p{L}])([\p{Lu}][\p{L}'’.-]{1,23}(?:\s+[\p{Lu}][\p{L}'’.-]{1,22})?):\s*""")
    private val mission = Regex(
        """(?i)^(?:drive\b.+\bto\b.+|buy\s+(?:a|an|the|some)\b.+|leave\s+(?:the|this)\b.+|help\s+\p{L}+\b.+|steal\s+(?:a|the|some|vehicles)\b.+|join\s+\p{L}+\b.+|talk\s+to\b.+)$"""
    )
    private val highNoise = Regex("""(?i)^(?:wnen\s+[it]\s+net\s+nis\b|toy[chgs]+\s+n\s+shat\b|bee\s+t?slap:\s+ann,?\s+u\s+sn\b)""")

    fun inspect(raw: String): Observation {
        val clean = raw.replace(Regex("""\s+"""), " ").trim()
        if (clean.isEmpty()) return Observation(Kind.EMPTY, "")
        if (mission.matches(clean)) return Observation(Kind.OBJECTIVE, clean)
        if (highNoise.containsMatchIn(clean)) return Observation(Kind.SUSPECT, clean, note = "severe-ocr")
        val hits = cue.findAll(clean).toList()
        if (hits.isNotEmpty()) {
            val last = hits.last()
            val overlap = hits.size > 1 || last.range.first > 0
            return Observation(
                if (overlap) Kind.OVERLAP else Kind.DIALOGUE,
                clean.substring(last.range.first),
                last.groupValues[1],
                if (overlap) "speaker-boundary" else ""
            )
        }
        return Observation(Kind.UNLABELLED, clean)
    }
}
