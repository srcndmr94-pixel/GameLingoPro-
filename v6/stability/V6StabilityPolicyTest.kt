package com.example.altyazi.v6

import org.junit.Assert.*
import org.junit.Test

class V6StabilityPolicyTest {
    @Test fun refusesSnapshotsWhenHeapLow() {
        assertFalse(V6StabilityPolicy.canCopyFrame(1920, 1080, 10_000_000L))
        assertTrue(V6StabilityPolicy.canCopyFrame(960, 540, 70_000_000L))
        assertFalse(V6StabilityPolicy.canCopyFrame(0, 1080, Long.MAX_VALUE))
        assertFalse(V6StabilityPolicy.canCopyFrame(1920, 1080, -1L))
    }
    @Test fun repeatedErrorsBackOffWithoutUnboundedDelay() {
        assertEquals(500L, V6StabilityPolicy.errorBackoffMs(1))
        assertEquals(1000L, V6StabilityPolicy.errorBackoffMs(2))
        assertEquals(12_000L, V6StabilityPolicy.errorBackoffMs(100))
    }
}
