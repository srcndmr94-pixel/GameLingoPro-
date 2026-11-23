package com.example.altyazi.v6

/** Small, fast OCR first; periodic full-resolution scan rescues tiny text. */
internal object V6RealtimePolicy {
    const val FAST_MAX_WIDTH = 1440
    const val FULL_RETRY_AFTER_EMPTY_READS = 3
    fun targetWidth(width: Int, height: Int, precedingEmptyReads: Int): Int {
        if (width <= 0 || height <= 0 || width <= FAST_MAX_WIDTH || height < 140) return width
        if (precedingEmptyReads >= FULL_RETRY_AFTER_EMPTY_READS &&
            precedingEmptyReads % (FULL_RETRY_AFTER_EMPTY_READS + 1) == FULL_RETRY_AFTER_EMPTY_READS) return width
        return FAST_MAX_WIDTH
    }
    fun nextEmptyCount(previous: Int, rawText: String): Int =
        if (rawText.isNotBlank()) 0 else (previous + 1).coerceAtMost(1_000_000)
}
