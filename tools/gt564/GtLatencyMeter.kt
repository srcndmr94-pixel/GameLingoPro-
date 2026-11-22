package com.example.altyazi

import java.util.Locale
import kotlin.math.max

internal data class GtLatencySample(
    val ocrMs: Long,
    val waitBeforeTranslationMs: Long,
    val queueMs: Long,
    val translationMs: Long,
    val displayMs: Long,
    val totalMs: Long
)

/** Monotonic end-to-end timing of OCR -> stabilization/queue -> translation -> UI. */
internal class GtLatencyMeter(
    private val clockMs: () -> Long = { System.nanoTime() / 1_000_000L }
) {
    private data class Stamp(
        var readAt: Long,
        var ocrMs: Long,
        var started: Long = -1,
        var ended: Long = -1,
        var queueMs: Long = 0L
    )
    private val records = LinkedHashMap<String, Stamp>()
    private fun key(text: String) = text.trim().lowercase(Locale.ROOT).replace(Regex("\\s+"), " ")

    @Synchronized fun read(text: String, ocrStartAt: Long, durationMs: Long) {
        if (text.isBlank()) return
        val k = key(text)
        if (!records.containsKey(k)) {
            if (records.size >= 80) records.remove(records.keys.first())
            records[k] = Stamp(ocrStartAt, durationMs.coerceAtLeast(0))
        }
    }

    @Synchronized fun translationStarted(text: String, queueMs: Long) {
        val k = key(text)
        val stamp = records.getOrPut(k) { Stamp(clockMs(), 0L) }
        stamp.started = clockMs()
        stamp.queueMs = queueMs.coerceAtLeast(0)
    }

    @Synchronized fun translationEnded(text: String) {
        records[key(text)]?.ended = clockMs()
    }

    @Synchronized fun displayed(text: String): GtLatencySample? {
        val stamp = records.remove(key(text)) ?: return null
        val now = clockMs()
        val started = stamp.started.takeIf { it >= 0 } ?: now
        val ended = stamp.ended.takeIf { it >= 0 } ?: started
        return GtLatencySample(
            ocrMs = stamp.ocrMs,
            waitBeforeTranslationMs = max(0L, started - (stamp.readAt + stamp.ocrMs)),
            queueMs = stamp.queueMs,
            translationMs = max(0L, ended - started),
            displayMs = max(0L, now - ended),
            totalMs = max(0L, now - stamp.readAt)
        )
    }
}
