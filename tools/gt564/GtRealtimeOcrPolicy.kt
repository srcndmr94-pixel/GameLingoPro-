package com.example.altyazi

/** Prevents synchronous duplicate OCR for blanks and short, complete captions.
 * Long clipped captions may still receive a vertical expansion at a safe cadence.
 */
internal object GtRealtimeOcrPolicy {
    const val EXPANDED_RETRY_COOLDOWN_MS = 1800L

    fun shouldExpand(text: String, elapsedSinceRetryMs: Long, mapVisible: Boolean): Boolean {
        if (mapVisible || text.isBlank() ||
            elapsedSinceRetryMs < EXPANDED_RETRY_COOLDOWN_MS) return false
        val s = text.trim()
        if (s.length < 42 || s.length > 200) return false
        return ProSubtitleAssembler.likelyContinued(s) ||
            GtOriginalInputGuard.looksClipped(s)
    }
}
