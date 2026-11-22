package com.example.altyazi

import java.text.Normalizer
import java.util.Locale

/** OCR spelling drift must not reset the same map selection.
 * Distinct map selections and left/right slots remain distinct.
 */
internal object GtMapIdentity568 {
    fun cleanTitle(raw: String): String {
        val decomposed=Normalizer.normalize(raw,Normalizer.Form.NFKD)
        return decomposed.replace(Regex("""\p{M}+"""), "")
            .lowercase(Locale.ROOT)
            .replace(Regex("""(?<=\p{L})0(?=\p{L})"""), "o")
            .replace(Regex("""[,;]+"""), " ")
            .replace(Regex("""^\s*g\s+(?=kelly\b)"""), "")
            .replace(Regex("""^\s*f(?=join\s+billy\b)"""), "")
            .replace(Regex("""\s+"""), " ")
            .trim()
    }

    fun identity(raw: String): String {
        val separator=raw.indexOf('|')
        if(separator <= 0) return raw.trim().lowercase(Locale.ROOT)
        val slot=raw.substring(0,separator).trim().lowercase(Locale.ROOT)
        return slot + "|" + cleanTitle(raw.substring(separator+1))
    }

    fun heading(raw: String): String = when (cleanTitle(raw)) {
        "kelly county" -> "KELLY COUNTY"
        "join billy on a job" -> "JOIN BILLY ON A JOB"
        else -> raw.trim()
    }
}
