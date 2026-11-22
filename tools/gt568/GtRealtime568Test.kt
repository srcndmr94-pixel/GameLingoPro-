package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtRealtime568Test {
  @Test fun normalizeSameMapEntityAcrossOcrNoise() {
    val variants=listOf("left|kęlly, county","left|kelly, county","left|kelly;c0unty","left|g kelly,county")
    assertEquals(1, variants.map(GtMapIdentity568::identity).distinct().size)
    assertEquals("right|join billy on a job",GtMapIdentity568.identity("right|fjoin billy on a job"))
    assertNotEquals(GtMapIdentity568.identity("right|vice-dale county"),
                    GtMapIdentity568.identity("right|leonard county"))
    assertNotEquals(GtMapIdentity568.identity("left|kelly county"),
                    GtMapIdentity568.identity("right|kelly county"))
    assertEquals("JOIN BILLY ON A JOB", GtMapIdentity568.heading("FJOIN BILLY ON A JOB"))
  }
  @Test fun fixContextualIdiomsAndPreserveNames() {
    assertEquals("Lucia: Vay be.",GtOriginalQualityGuard.polish("Lucia: Damn.","Lucia: Lanet etmek."))
    assertEquals("Vicki: Kişi başı en az beş haneli bir meblağ!",
      GtOriginalQualityGuard.polish("Vicki: Uh, five figures each... at least!","Vicki: Her biri beş rakamlı."))
    assertEquals("Vicki: Birlikte çalışırsak Delight's hepimiz için büyük bir fırsat olabilir.",
      GtOriginalQualityGuard.polish("Vicki: Delight's could be big for all of us if we work together.",
        "Vicki: Birlikte çalışırsak mutluluklar büyük olabilir."))
    assertEquals("Vicki: Frankie'ye bir kez olsun kazık atabileceksem...",
      GtOriginalQualityGuard.polish("Vicki: if it meant I could fuck over Frankie even once...",
        "Vicki: eğer Frankie'yi bir kez bile sikebilirsem..."))
    assertEquals("Vicki: Merhaba.",
      GtOriginalQualityGuard.polish("Vicki: Hello.", "Vicki: Merhaba."))
  }
}
