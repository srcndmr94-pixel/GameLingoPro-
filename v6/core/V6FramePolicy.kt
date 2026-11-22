package com.example.altyazi.v6

/** Pure, bounded rules for a producer which must never await the OCR consumer. */
internal object V6FramePolicy {
    const val MIN_SNAPSHOT_GAP_MS = 180L
    const val MAX_FRAME_AGE_MS = 2400L

    fun shouldSnapshot(nowMs: Long, previousMs: Long, projectionActive: Boolean): Boolean =
        projectionActive && (previousMs <= 0L || nowMs - previousMs >= MIN_SNAPSHOT_GAP_MS)

    /** Map selection can be responsive; ordinary full-menu scans must not starve spoken OCR. */
    fun shouldProbeMenu(
        nowMs: Long, previousMs: Long, selectedMenuVisible: Boolean, jobActive: Boolean
    ): Boolean {
        if (jobActive) return false
        val spacing = if (selectedMenuVisible) 500L else 1500L
        return previousMs <= 0L || nowMs - previousMs >= spacing
    }

    fun isFresh(capturedAtMs: Long, nowMs: Long, snapshotEpoch: Int, currentEpoch: Int): Boolean =
        snapshotEpoch == currentEpoch && capturedAtMs >= 0L &&
            nowMs >= capturedAtMs &&
            nowMs - capturedAtMs <= MAX_FRAME_AGE_MS
}
