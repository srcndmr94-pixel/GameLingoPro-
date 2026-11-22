package com.example.altyazi

import org.junit.Assert.*
import org.junit.Test

class GtOriginalInputGuard563Test {
    @Test fun objectiveIsNotSpokenSubtitle() {
        assertTrue(GtOriginalInputGuard.isHudObjective("Buy a new outfit at the merch stall"))
        assertTrue(GtOriginalInputGuard.isHudObjective("Leave the store"))
        assertEquals("", GtOriginalInputGuard.prepare("Buy a new outfit at the merch stall"))
        assertFalse(GtOriginalInputGuard.isHudObjective("Clerk: Buy a new outfit at the merch stall."))
    }
    @Test fun mixedObjectiveRemovedWithoutLosingDialogue() {
        assertEquals("Clerk: Hey, dude.", GtOriginalInputGuard.prepare("Buy a new outfit at the merch stall Clerk: Hey, dude."))
        assertEquals("Clerk: Come on, dude.", GtOriginalInputGuard.prepare("Clerk: Come on, dude. Buy a new"))
    }
    @Test fun overlappingSpeakersNotTranslatedTogether() {
        assertEquals("Lucia: Well, Vicki's real nosey, but...", GtOriginalInputGuard.prepare(
            "Stranger: Yeah, rest of 'em just got down there. Lucia: Well, Vicki's real nosey, but..."))
        assertEquals("Jason: We left your car at Hank's.", GtOriginalInputGuard.prepare(
            "Stranger: I'll look for you. Jason: We left your car at Hank's."))
    }
    @Test fun observedOcrMisreadsAreCorrectedConservatively() {
        assertEquals("Clerk: I'd go for something that won't fly off.", GtOriginalInputGuard.prepare(
            "Clerk: It'd go for something that won't fly off."))
        assertEquals("Lucia: Yeah. I look good in these.", GtOriginalInputGuard.prepare(
            "Lucia: Yeah. 0 look good in these."))
        assertEquals("Wyman: Woo-hoo! Look in' good!", GtOriginalInputGuard.prepare("Wyaman Woo-hoo! Look in' good!"))
        assertEquals("Billy: So Ricky is here.", GtOriginalInputGuard.prepare("ABilly: So Ricky is here."))
    }
    @Test fun clippedLineWaitsButCompleteLineGoesThrough() {
        assertTrue(GtOriginalInputGuard.looksClipped("Wyman: Now there's a merchandise stand right over st"))
        assertTrue(GtOriginalInputGuard.looksClipped("Wyman: if you wanna go, get yourselves another set of clo"))
        assertFalse(GtOriginalInputGuard.looksClipped("Clerk: Only thing worse than a crash is a crash with your dick and balls out."))
    }
    @Test fun speakerNamesStayOutOfTheTranslationRequest() {
        assertEquals("Clerk" to "Hey dude!", GtOriginalInputGuard.splitSpeaker("Clerk: Hey dude!"))
        assertEquals("Wyman" to "What's new?", GtOriginalInputGuard.splitSpeaker("Wyman: What's new?"))
        assertEquals(null to "Leave the store", GtOriginalInputGuard.splitSpeaker("Leave the store"))
    }
    @Test fun goodDialogueIsNotLostToLegacyNoiseClassifier() {
        assertTrue(GtOriginalInputGuard.recoverableSpokenLine(
            "Wyman: Hey, one of youtwo mind drivin' us down there?"))
        assertFalse(GtOriginalInputGuard.recoverableSpokenLine("BUY NEW OUTFIT"))
        assertFalse(GtOriginalInputGuard.recoverableSpokenLine("Wyman: m%% #*$ S}} ab3"))
    }
    @Test fun badIdiomsGetScopedReplacements() {
        assertEquals("Jason: İşte bu cesur bir tercih.",
            GtOriginalQualityGuard.polish("Jason: Now that's a choice.", "Jason: İşte bu bir seçim."))
        assertEquals("Billy: Bu işte artık epey tecrübeli.",
            GtOriginalQualityGuard.polish("Billy: She's basically a vet at this point.", "Billy: Bu konuda bir veteriner."))
        assertEquals("Clerk: Yardım edebilirim.",
            GtOriginalQualityGuard.polish("Clerk: I can help.", "Clerk: Yardım edebilirim."))
    }
}
