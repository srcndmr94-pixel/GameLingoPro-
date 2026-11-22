package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
import java.io.File

/** 10 independent cases; real image fingerprints from user-provided map/game screenshots. */
class GtMapExit56Test {
    private val mapPixels="1f273c1e2b3e21273d1d2a3d7eb89276c3cb1c2c462a2e4721293e20283d1d2a3d1d2a3da4aab678ae8cb0cfc98db5aa21293e252d441d283c21293e74a78874aa86779d882a2e3935404641535564bad56da582709f7f7ba28d75ab87edf2ec535428bcb07e1c252e98b7a76ca280b4c3bc6fa0806aa27f6da07f282c37353c463f4c5283a8a16ea07d6e9f7f70a27d6da07fe1edd96e9f7f9bb9c180af9da8bcd471a3801d283c1d2a3d2c324875ab877eaf9a83b49f83b09c84b5a0".chunked(6).map { it.toInt(16) }.toIntArray()
    private val gamePixels="27221e131718151515362b27130f0c1a12102020223626262e272127231a9e8d7d5856578068647a6e6065584f6f6357998375827161946d4e655c578c796b90786c735f5e61544e20232a2e2c2f2f2b2a73645d5c4f463c312de7d1c3998378585626d1be84292a2f927f707a6854a085702a1d17493c36a08b7a88776f846e60715b4d725b4bb09580b09a83271811453a348e86847f7472b69c8d6452488f7a65af9c95b19681564744e7dac7ab96858c786d5f493c7c6557937f74".chunked(6).map { it.toInt(16) }.toIntArray()

    @Test fun actualUserMapAndGameplayImagesShowClearSceneChange() {
        assertEquals(63,mapPixels.size)
        assertTrue(GtMapVisual56.changed(mapPixels,gamePixels))
    }
    @Test fun exactSameFrameNeverCountsAsMapExit() {
        assertFalse(GtMapVisual56.changed(mapPixels,mapPixels))
    }
    @Test fun minorOcrLayerOrPixelJitterDoesNotCountAsExit() {
        val noisy=mapPixels.map { p ->
            ((p shr 16 and 255)+5).coerceAtMost(255) shl 16 or
            (((p shr 8 and 255)+5).coerceAtMost(255) shl 8) or
            ((p and 255)+5).coerceAtMost(255)
        }.toIntArray()
        assertFalse(GtMapVisual56.changed(mapPixels,noisy))
    }
    @Test fun noSnapshotAndInvalidSampleCannotForceExit() {
        assertFalse(GtMapVisual56.changed(null,gamePixels))
        assertFalse(GtMapVisual56.changed(mapPixels,intArrayOf(2)))
        assertTrue(GtMapVisual56.fingerprint(0,0){_,_-> 0}.isEmpty())
    }
    @Test fun onlyFourConsecutiveMissingProbesWithProofCanExit() {
        assertFalse(GtMapStay55.shouldExitMap(true,3,true))
        assertTrue(GtMapStay55.shouldExitMap(true,4,true))
        assertFalse(GtMapStay55.shouldExitMap(true,200,false))
    }
    @Test fun gameplaySpeechAloneMustNeverClearUnchangedMap() {
        val justSpeech=listOf(GtAllHud.Line("Vicki: okay, sorry",400,400,720,430))
        assertFalse(GtMapStay55.differentScreenEvidence(justSpeech,1536,688))
    }
    @Test fun realMapTabsAreNotGameDialogueAndKeepSelectionIdentity() {
        val tabs=listOf(
            GtAllHud.Line("MAP",730,20,780,40),
            GtAllHud.Line("BRIEF",800,20,860,40),
            GtAllHud.Line("PROGRESS",890,20,970,40))
        assertTrue(GtSelectedMapPanel.isMap(tabs,1536,688))
        assertFalse(GtSelectedMapPanel.isMap(listOf(
            GtAllHud.Line("Vicki: Tell me about your day",500,450,900,475)),1536,688))
    }
    @Test fun mapExitAndQuestSourceAreWiredIntoOriginalCapture() {
        val src=File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(src.contains("differentScreen || visualExit"))
        assertTrue(src.contains("gtMapVisualReference56=visual56"))
        assertTrue(src.contains("gtPanelSources[slot]==source"))
        assertTrue(src.contains("!prefs.mapKeepVisible"))
        assertTrue(src.contains("processSubtitle(full) // caption always has priority"))
    }
    @Test fun okayInsideSentenceMustNotInventLoveWords() {
        val out=GtDialogueQuality.polish("Okay. yeah, i'm sorry, that was a little much. Okay.",
            "Tamam aşkım. evet kusura bakmayın bu biraz fazla oldu. Tamam aşkım.")
        assertFalse(out.contains("aşkım",ignoreCase=true))
        assertTrue(out.contains("Tamam"))
        assertEquals("Tamam aşkım",GtDialogueQuality.polish(
            "Okay babe", "Tamam aşkım"))
    }
    @Test fun ventMeansExpressFeelingsAndProfanityIsPreserved() {
        val out=GtDialogueQuality.polish(
            "Okay, are you gonna let me vent or what? Cause I can't afford therapy.",
            "Tamam, beni havalandırmama izin verecek misin? Çünkü terapiye param yetmiyor.")
        assertTrue(out.contains("içimi dökmeme"))
        assertFalse(out.contains("havalandırmama"))
        assertEquals("Resident: Tanrım, her neyse... siktir et!",
            GtDialogueQuality.polish("Resident: Lord, whatever... fuck it!",
                "Resident: Tanrım, her neyse... siktir et!"))
    }
}
