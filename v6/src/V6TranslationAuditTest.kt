package com.example.altyazi.v6
import org.junit.Assert.*
import org.junit.Test

class V6TranslationAuditTest {
    @Test fun neverForceTurkishDiacritics() {
        assertTrue(V6TranslationAudit.check("Lucia: Right.", "Lucia: Aynen.").isEmpty())
        assertTrue(V6TranslationAudit.check("Jason: Hi!", "Jason: Selam!").isEmpty())
    }
    @Test fun knownFailuresAreReportedButNotDropped() {
        assertTrue(V6TranslationAudit.check("Lucia: Really?", "").contains(
            V6TranslationAudit.Issue.BLANK_OUTPUT))
        assertTrue(V6TranslationAudit.check("Vicki: What's up?", "Vicki: What's up?").contains(
            V6TranslationAudit.Issue.SOURCE_RETURNED))
        assertTrue(V6TranslationAudit.check("Clerk: Thank you.", "Katip: Teşekkürler.").contains(
            V6TranslationAudit.Issue.SPEAKER_CHANGED))
    }
    @Test fun validGameSlangShouldNotBeAutoCensored() {
        assertTrue(V6TranslationAudit.check("Local: Bitch, die!", "Local: Kaltak, öl!").isEmpty())
        assertTrue(V6TranslationAudit.check("Locals: Fuckin' pay attention!", "Locals: Dikkat etsene lan!").isEmpty())
    }
}
