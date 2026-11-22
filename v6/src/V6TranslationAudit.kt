package com.example.altyazi.v6

/** Non-destructive validation. The original translation remains visible.
 * The audit records problems; it never discards a subtitle in shadow mode.
 */
internal object V6TranslationAudit {
    enum class Issue { BLANK_OUTPUT, SOURCE_RETURNED, SPEAKER_CHANGED, EXTREME_LENGTH }
    fun check(source: String, translation: String): Set<Issue> {
        val issues = linkedSetOf<Issue>()
        val s = source.trim()
        val t = translation.trim()
        if (t.isEmpty()) {
            issues.add(Issue.BLANK_OUTPUT)
            return issues
        }
        val sourceBody = s.substringAfter(": ", s).trim()
        val outputBody = t.substringAfter(": ", t).trim()
        if (sourceBody.length > 3 && sourceBody.equals(outputBody, ignoreCase = true))
            issues.add(Issue.SOURCE_RETURNED)
        val label = V6CaptionAudit.inspect(source).speaker
        if (label != null && !t.startsWith("$label:"))
            issues.add(Issue.SPEAKER_CHANGED)
        if (sourceBody.length > 12 && outputBody.length > sourceBody.length * 4 + 40)
            issues.add(Issue.EXTREME_LENGTH)
        return issues
    }
}
