package com.example.altyazi.v6

import org.junit.Assert.*
import org.junit.Test

class V6RealtimePatchTest {
    @Test fun fastOcrUsesPeriodicHighResolutionFallback() {
        assertEquals(1440,V6RealtimePolicy.targetWidth(1920,280,0))
        assertEquals(1920,V6RealtimePolicy.targetWidth(1920,280,3))
        assertEquals(1440,V6RealtimePolicy.targetWidth(1920,280,4))
        assertEquals(1920,V6RealtimePolicy.targetWidth(1920,60,0))
    }
    @Test fun fixesKnownLogErrorsWithoutChangingUnrelatedLines() {
        assertEquals("DJ: Anladın mı? Evet!",V6DialogueRepair.polish(
            "DJ: Ya dig? Yeah!","DJ: Kazdın mı? Evet!"))
        assertEquals("Stranger: Sen de alemsin.",V6DialogueRepair.polish(
            "Stranger: You a trip...","Stranger: Sen bir yolculuksun"))
        assertEquals("Jason: Bir saniye.",V6DialogueRepair.polish(
            "Jason: One sec.","Jason: Bir saniye."))
        assertEquals("What's two plus seven?",
            V6DialogueRepair.repairInput("What's tw O plus seven?"))
    }
}
