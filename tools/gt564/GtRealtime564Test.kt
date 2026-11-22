package com.example.altyazi

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class GtRealtime564Test {
    @Test fun avoidDuplicateOcrButRecoverClippedLines() {
        assertFalse(GtRealtimeOcrPolicy.shouldExpand("", 9999, false))
        assertFalse(GtRealtimeOcrPolicy.shouldExpand("Wyman: All right.", 9999, false))
        val clipped = "Wyman: if you wanna go, get yourselves another set of clo"
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(clipped, 1799, false))
        assertTrue(GtRealtimeOcrPolicy.shouldExpand(clipped, 1800, false))
        assertFalse(GtRealtimeOcrPolicy.shouldExpand(clipped, 9999, true))
    }

    @Test fun measureActualStages() {
        var now = 1000L
        val meter = GtLatencyMeter { now }
        meter.read("Jason: Hey", 800, 100)
        now = 1150; meter.translationStarted("Jason: Hey", 30)
        now = 1400; meter.translationEnded("Jason: Hey")
        now = 1450
        val result = meter.displayed("Jason: Hey")!!
        assertEquals(100L, result.ocrMs)
        assertEquals(250L, result.waitBeforeTranslationMs)
        assertEquals(30L, result.queueMs)
        assertEquals(250L, result.translationMs)
        assertEquals(50L, result.displayMs)
        assertEquals(650L, result.totalMs)
        assertNull(meter.displayed("Jason: Hey"))
    }

    @Test fun newestPendingSubtitleWins() {
        val first = CountDownLatch(2)
        val release = CountDownLatch(1)
        val finish = CountDownLatch(1)
        val seen = java.util.Collections.synchronizedList(mutableListOf<Int>())
        val executor = GtLatestFirstExecutor()
        try {
            for (i in 1..2) executor.execute(Runnable {
                first.countDown()
                release.await(4, TimeUnit.SECONDS)
                seen.add(i)
            })
            assertTrue(first.await(2, TimeUnit.SECONDS))
            for (i in 3..8) executor.execute(Runnable {
                seen.add(i)
                finish.countDown()
            })
            release.countDown()
            assertTrue(finish.await(4, TimeUnit.SECONDS))
            assertTrue(seen.contains(8))
            assertFalse(seen.any { it in 3..7 })
            assertTrue(executor.discardedOldRequests() >= 4)
        } finally {
            release.countDown()
            executor.close()
        }
    }
}
