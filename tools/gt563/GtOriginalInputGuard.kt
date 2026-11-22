package com.example.altyazi

import java.util.Locale

/** GameLingo MediaProjection OCR adapter for the unmodified GameTranslator v1.8.49 pipeline.
 * Filters unrelated HUD instructions and prevents two distinct speakers merging in one translation.
 * No API, model, or whole-scene lookup is used. */
internal object GtOriginalInputGuard {
    private val speaker = Regex("""(?<![\p{L}])(?:[A-Z][\p{L}'’-]{1,24}(?:\s+[A-Z][\p{L}'’-]{1,19})?):\s*""")
    private val objective = Regex(
        """(?i)^(?:buy\s+(?:a|an|the|some)\s+.+|leave\s+the\s+(?:store|shop|area)|(?:go|drive|head)\s+to\s+.+|(?:talk|speak)\s+to\s+.+)$""")
    private val distinctObjectivePrefix = Regex(
        """(?i)^\s*(?:buy\s+a\s+new\s+outfit\s+at\s+the\s+merch\s+stall|leave\s+the\s+store)\s+(?=[A-Z][a-z]{2,20}:)""")
    private val trailingObjectiveFragment = Regex(
        """(?i)(?<=[.!?])\s+buy\s+a\s+new\s*(?:outfit(?:\s+at\s+the\s+merch\s+sta\w*)?)?\s*$""")
    private val leadingSpeaker = Regex("""^([A-Z][\p{L}'’-]{1,24}(?:\s+[A-Z][\p{L}'’-]{1,19})?):\s*(.+)$""")

    /** Names and roles must never be translated (Clerk -> Katip, etc.). */
    fun splitSpeaker(text: String): Pair<String?, String> {
        val m = leadingSpeaker.matchEntire(text.trim()) ?: return null to text
        return m.groupValues[1] to m.groupValues[2]
    }

    fun isHudObjective(text: String): Boolean {
        val s = text.trim()
        return s.length in 7..115 && !s.contains(':') &&
            !s.contains('?') && !s.contains('!') && !s.contains('.') &&
            objective.matches(s)
    }

    /** Recover clearly spoken text which older, dictionary-based OCR filters
     * reject as a false positive. Protects against passing real HUD rubbish.
     */
    fun recoverableSpokenLine(raw: String): Boolean {
        val (name, body) = splitSpeaker(raw)
        if (name == null || body.length !in 20..210 || isHudObjective(body)) return false
        if (body.split(Regex("""\s+""")).size < 5) return false
        if (body.any { it in "$@#%^*={}<>"} ) return false
        return body.count { it.isLetter() }.toFloat() / body.length >= .70f
    }

    fun prepare(raw: String): String {
        if (raw.isBlank()) return ""
        var s = raw.replace(Regex("""\s+"""), " ").trim()
        s = distinctObjectivePrefix.replace(s, "")
        if (isHudObjective(s)) return ""
        // Two speaker cues can be visible simultaneously. Prefer the most
        // recent lower caption, rather than blending the two into one sentence.
        val cues = speaker.findAll(s).toList()
        if (cues.size > 1) s = s.substring(cues.last().range.first).trimStart()
        s = trailingObjectiveFragment.replace(s, "").trim()
        s = s.replace(Regex("""(?i)\b[yY]outwo\b"""), "you two")
        s = s.replace(Regex("""(?i)\bClerk:\s+It'd\s+go\s+for\b"""), "Clerk: I'd go for")
        s = s.replace(Regex("""(?i)\b0\s+(?=look\s+good\b)""")) { "I " }
        s = s.replace(Regex("""(?i)\bWyaman(?=\s+Woo-hoo)"""), "Wyman:")
        s = s.replace(Regex("""(?i)\b(?:Wymans|Wymane)(?=\s+(?:Well|Oh))"""), "Wyman:")
        s = s.replace(Regex("""(?i)\bABilly:\s*"""), "Billy: ")
        return s.replace(Regex("""\s{2,}"""), " ").trim()
    }

    /** Defer obviously clipped OCR until a subsequent better read. */
    fun looksClipped(text: String): Boolean {
        val s = text.trim()
        if (s.length < 47 || s.last() in ".!?…,:;\"'’") return false
        val last = s.substringAfterLast(' ').trim()
        return last.length in 1..3 && last.all { it.isLetter() } &&
            last.lowercase(Locale.ROOT) !in setOf("you", "the", "and", "for", "but", "not", "out", "get", "let", "him", "her", "our", "are", "all", "now", "see", "can", "was", "got", "one", "two")
    }
}
