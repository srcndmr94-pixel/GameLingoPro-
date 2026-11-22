package com.example.altyazi.v6

import org.junit.Assert.*
import org.junit.Test

class V6CaptureRecoveryTest {
    @Test fun retryOnlyAfterResizeAndAtControlledInterval() {
        assertFalse(V6CaptureRecovery.shouldReattach(true,1000L,0,0,1000L,3499L))
        assertTrue(V6CaptureRecovery.shouldReattach(true,1000L,0,0,1000L,3500L))
        assertFalse(V6CaptureRecovery.shouldReattach(true,1000L,0,1,3500L,8499L))
        assertTrue(V6CaptureRecovery.shouldReattach(true,1000L,0,1,3500L,8500L))
        assertFalse(V6CaptureRecovery.shouldReattach(true,1000L,0,2,8500L,40000L))
    }
    @Test fun dontDestroyStoppedOrStableProjection() {
        assertFalse(V6CaptureRecovery.shouldReattach(false,1000L,0,0,1000L,50000L))
        assertFalse(V6CaptureRecovery.shouldReattach(true,1000L,1,0,1000L,50000L))
        assertFalse(V6CaptureRecovery.shouldReattach(true,0L,0,0,0L,50000L))
        assertTrue(V6CaptureRecovery.needsUserConsentMessage(2,0))
        assertFalse(V6CaptureRecovery.needsUserConsentMessage(2,1))
    }
    @Test fun blankFramesAreNotOcrFailures() {
        assertEquals("üretici yeni görüntü vermiyor", V6CaptureRecovery.noFrameExplanation(0))
        assertEquals("görüntü bildirimi var, ancak kare alınamadı",
            V6CaptureRecovery.noFrameExplanation(2))
    }
}
