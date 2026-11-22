package com.example.altyazi.v6

import org.junit.Assert.*
import org.junit.Test

class V6FramePolicyTest {
    @Test fun producerDoesNotBlockOnSlowOcr() {
        assertTrue(V6FramePolicy.shouldSnapshot(1000L,0L,true))
        assertFalse(V6FramePolicy.shouldSnapshot(1100L,1000L,true))
        assertTrue(V6FramePolicy.shouldSnapshot(1180L,1000L,true))
        assertFalse(V6FramePolicy.shouldSnapshot(2500L,1000L,false))
    }

    @Test fun staleOrRotatedSnapshotsCannotOverwriteNewCaptions() {
        assertTrue(V6FramePolicy.isFresh(1000L,1800L,7,7))
        assertFalse(V6FramePolicy.isFresh(1000L,1800L,7,8))
        assertFalse(V6FramePolicy.isFresh(1000L,3500L,7,7))
        assertFalse(V6FramePolicy.isFresh(2000L,1900L,7,7))
    }

    @Test fun menuOcrIsRateLimitedIndependently() {
        assertTrue(V6FramePolicy.shouldProbeMenu(1000L,0L,false,false))
        assertFalse(V6FramePolicy.shouldProbeMenu(1300L,1000L,false,false))
        assertTrue(V6FramePolicy.shouldProbeMenu(2500L,1000L,false,false))
        assertFalse(V6FramePolicy.shouldProbeMenu(1300L,1000L,true,false))
        assertTrue(V6FramePolicy.shouldProbeMenu(1500L,1000L,true,false))
        assertFalse(V6FramePolicy.shouldProbeMenu(5000L,1000L,true,true))
    }

    @Test fun atMostOneQueuedFrameIsAllowedByMailboxCapacity() {
        assertEquals(180L,V6FramePolicy.MIN_SNAPSHOT_GAP_MS)
        assertEquals(2400L,V6FramePolicy.MAX_FRAME_AGE_MS)
    }
}
