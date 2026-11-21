package com.example.altyazi

import java.util.Locale

/**
 * Combines genuinely continuous OCR subtitles without inventing words.
 * Never merges two different speakers or a game mission with dialogue.
 */
internal class ProSubtitleAssembler {
    private var last = ""
    private var seenAt = 0L

    fun clear() { last = ""; seenAt = 0L }

    fun accept(raw: String, nowMs: Long): String {
        val next = raw.trim()
        if (next.isEmpty()) {
            if (nowMs - seenAt > 1300L) clear()
            return ""
        }
        if (last.isEmpty() || nowMs - seenAt > 1800L) {
            last = next; seenAt = nowMs; return next
        }
        val previous = last
        fun norm(t: String) = t.lowercase(Locale.ROOT).replace(Regex("""\s+"""), " ").trim()
        val a = norm(previous); val b = norm(next)
        when {
            a == b -> { seenAt = nowMs; return previous }
            b.startsWith(a) && next.length > previous.length -> {
                last = next; seenAt = nowMs; return next
            }
            a.startsWith(b) && previous.length > next.length -> {
                seenAt = nowMs; return previous
            }
            (previous.trimEnd().lastOrNull() in listOf(',', ';')) &&
                next.firstOrNull()?.isLowerCase() == true &&
                next.length >= 14 && !next.contains(':') && !a.endsWith(b) -> {
                last = previous.trimEnd() + " " + next
                seenAt = nowMs
                return last
            }
            a.endsWith(b) && b.length >= 18 -> {
                seenAt = nowMs; return previous
            }
            else -> {
                last = next; seenAt = nowMs; return next
            }
        }
    }

    companion object {
        fun likelyContinued(text: String): Boolean {
            val s = text.trimEnd()
            if (s.length < 22) return false
            return (s.lastOrNull() in listOf(',', ';', ':')) ||
                Regex("""(?i)\b(?:and|but|while|although|because|with|to|for)\s*$""").containsMatchIn(s)
        }

        fun fuller(first: String, second: String): String {
            val a = first.trim(); val b = second.trim()
            if (b.length <= a.length + 10) return a
            if (a.isEmpty()) return b
            return if (b.startsWith(a.take(24), true)) b else a
        }
    }
}
