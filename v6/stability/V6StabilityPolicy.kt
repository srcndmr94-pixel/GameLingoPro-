package com.example.altyazi.v6

/** Safe frame-copy budget for a long-running OCR process. Pure logic for unit testing. */
internal object V6StabilityPolicy {
    const val MIN_HEADROOM_BYTES = 32L * 1024 * 1024
    fun canCopyFrame(width: Int, height: Int, heapHeadroomBytes: Long): Boolean {
        if (width <= 0 || height <= 0 || heapHeadroomBytes < 0L) return false
        val required = width.toLong() * height.toLong() * 4L
        return required > 0 && heapHeadroomBytes >= maxOf(MIN_HEADROOM_BYTES, required * 3L)
    }
    fun errorBackoffMs(consecutiveFailures: Int): Long {
        val shift = (consecutiveFailures - 1).coerceIn(0, 5)
        return (500L shl shift).coerceAtMost(12_000L)
    }
}
