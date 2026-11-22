package com.example.altyazi.v6

import org.junit.Assert.*
import org.junit.Test
import java.io.BufferedReader
import java.io.InputStreamReader
import java.nio.charset.StandardCharsets

class V6CaptionAuditTest {
    @Test fun replayRecordedAndSyntheticCorpus() {
        val stream = checkNotNull(javaClass.getResourceAsStream("/v6-caption-cases.tsv")) {
            "V6 golden corpus missing"
        }
        val data = BufferedReader(InputStreamReader(stream,StandardCharsets.UTF_8))
            .readLines().filter { it.isNotBlank() && !it.startsWith("#") }
        assertTrue("At least 30 fixtures are required", data.size >= 30)
        for (line in data) {
            val columns = line.split('\t')
            assertEquals("Malformed fixture: $line",4,columns.size)
            val (id,kind,raw,expected) = columns
            val result = V6CaptionAudit.inspect(raw)
            assertEquals("kind: $id",kind,V6CaptionAudit.Kind.valueOf(kind).name)
            assertEquals("candidate: $id",expected,result.candidate)
        }
    }

    @Test fun doNotTreatQuotedNamesAsSpeakerCues() {
        assertEquals(V6CaptionAudit.Kind.OBJECTIVE,
            V6CaptionAudit.inspect("Join Billy on a job").kind)
        assertEquals("Lucia",V6CaptionAudit.inspect("Lucia: Damn.").speaker)
        assertEquals("Jason: We'll think about it.",
            V6CaptionAudit.inspect("Vicki: Come with us. Jason: We'll think about it.").candidate)
    }
}
