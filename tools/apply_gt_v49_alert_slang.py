#!/usr/bin/env python3
"""GameLingoPro 4.9: stop PS5 shell notifications being mistaken for game SMS,
and repair selected slang mistranslations from the user's 4.8 runtime log.

Apply after 4.8, preserving colors, all OCR regions, engine order and dedup.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
engine=src/'GtDialogueQuality.kt'
notice=src/'GtGameNotice.kt'
capture=src/'CaptureService.kt'
view=src/'GtExactOverlay.kt'
native=src/'GtNativeEngine.kt'
build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
for f in (engine,notice,capture,view,native,build):
    if not f.is_file(): raise RuntimeError('GameLingoPro 4.8 source missing: '+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Incorrect original applicationId')
if 'Color.rgb(255,203,86)' not in view.read_text():
    raise RuntimeError('Original 4.7 colors must remain active')
if 'GtDialogueQuality.polish(body,translated)' not in native.read_text():
    raise RuntimeError('Expected 4.8 dialogue quality chain missing')
if 'gtQuestBoxesOnly' in capture.read_text():
    raise RuntimeError('Refusing disabled-translations baseline')

def once(path,old,new):
    s=path.read_text(encoding='utf8')
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f'{path.name}: expected one anchor, found {count}: {old[:95]}')
    path.write_text(s.replace(old,new,1),encoding='utf8')

# The old 4.3 detector accepted any generic title plus adjacent lines.  It
# logged "FIFA", "Güç", and Turkish "PS5 sisteminiz..." as game notifications.
once(notice,
'''    private val excluded=setOf("map","brief","progress","game","store",
        "settings","inventory","features","standard","recenter",
        "exit","sms","message","messages","subtitle","mission")''',
'''    private val excluded=setOf("map","brief","progress","game","store",
        "settings","inventory","features","standard","recenter",
        "exit","sms","message","messages","subtitle","mission",
        "fifa","güç","guc","power","ps5","playstation","dualsense",
        "system","sistem","notifications","bildirimler")
    // A PlayStation notification can overlay the video frame.  It is not an
    // in-game SMS even when OCR geometry resembles the game's message box.
    private val psShell=Regex(
        """(?i)(?:\\bps5\\b|\\bplaystation\\b|\\bdualsense\\b|""" +
        """\\bsisteminiz\\b|\\bkapatılmaya\\b|\\bkapatilmaya\\b|""" +
        """\\bhazırlanıyor\\b|\\bhazirlaniyor\\b|\\bwireless controller\\b)""")
    private val englishCue=Regex(
        """(?i)\\b(?:the|they|them|their|your|you|we|our|he|she|""" +
        """this|that|when|what|where|why|how|can|could|would|should|""" +
        """will|was|were|are|is|have|has|had|with|from|for|in|""" +
        """don't|doesn't|won't|it's|i'm|i'll|me|my|out|take|need|""" +
        """them|some|to|and|be)\\b""")
    private fun gameEnglish(text:String):Boolean =
        !psShell.containsMatchIn(text) && englishCue.containsMatchIn(text)''')

once(notice,
'''        val valid=lines.filter{
            it.text.isNotBlank() && it.right>it.left && it.bottom>it.top
        }.sortedWith(compareBy<GtAllHud.Line>{it.top}.thenBy{it.left})''',
'''        val valid=lines.filter{
            it.text.isNotBlank() && it.right>it.left && it.bottom>it.top
        }.sortedWith(compareBy<GtAllHud.Line>{it.top}.thenBy{it.left})
        // Turkish platform UI is not source English, do not overlay/translate.
        if(valid.any{psShell.containsMatchIn(it.text)})return null''')
once(notice,
'''            if(source.length>=23) return Notice("sms",head.text.trim(),source,''',
'''            if(source.length>=23 && gameEnglish(source))
                return Notice("sms",head.text.trim(),source,''')
once(notice,
'''            if(rows.size>=2 && text.length>=48) return Notice(''',
'''            if(rows.size>=2 && text.length>=48 && gameEnglish(text))
                return Notice(''')

# Preserve engine, but fix *meaning* when a known English sense is rendered
# as a misleading literal phrase in the current GT/GTX output.
once(engine,
'''        return result
    }
}''',
'''        if(english.contains("client outreach") && english.contains("in-person"))
            result=result.replace("yüz yüze müşteri desteği",
                "müşterilerle yüz yüze görüşme",ignoreCase=true)

        if(english.contains("spaced out") && english.contains("saw"))
            result=result.replace("tamamen uzaklaştım",
                "aklım başımdan gitti",ignoreCase=true)

        if(english.contains("stoners"))
            result=result.replace(Regex("""(?i)\\btaşçı\\b"""),
                "ot içen insan")

        if(english.contains("tow your whip")) {
            result=result.replace("Kırbacını çekmelerini sağladım",
                "Arabanı çektirdim",ignoreCase=true)
            if(english.contains("ugly as fuck"))
                result=result.replace("O şey çok çirkindi",
                    "Zaten bok gibiydi",ignoreCase=true)
        }

        if(english.contains("book it to the impound") &&
           (result.contains("Hapishaneye",ignoreCase=true) ||
            result.contains("kayıt ettir",ignoreCase=true)))
            result="Aracın çekildiği otoparka koşmamız lazım!"

        if(english.contains("smoke boat")) {
            result=result.replace("duman teknemiz","ot arabamız",ignoreCase=true)
            result=result.replace("duman teknesini sıcak tellerle çevireceğim",
                "ot arabasına düz kontak yapacağım",ignoreCase=true)
            result=result.replace("duman teknesine tel çekeceğim",
                "ot arabasına düz kontak yapacağım",ignoreCase=true)
        }

        if(english.contains("slinging our shit"))
            result=result.replace("bokumuzu atacağız",
                "malımızı satacağız",ignoreCase=true)

        if(english.contains("pile of bud"))
            result=result.replace("tomurcuk yığını",
                "ot yığını",ignoreCase=true)

        if(english.matches(Regex("""sounds like a plan[.!…]*""")) &&
           result.contains("plana benziyor",ignoreCase=true))
            result="Mantıklıymış."

        return result
    }
}''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtObservedLog49Test.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtObservedLog49Test {
    private fun line(text:String,x:Int,y:Int,w:Int=350,h:Int=22)=
        GtAllHud.Line(text,x,y,x+w,y+h)

    @Test fun suppressesPlayStationSystemAndNativeTurkishAlerts() {
        assertNull(GtGameNotice.find(listOf(
            line("Güç",316,487,160),
            line("PS5 sisteminiz kapatilmaya hazırlanıyor.",220,539)),
            1536,690))
        assertNull(GtGameNotice.find(listOf(
            line("FIFA",316,487,160),
            line("PlayStation bildirimi görüntüleniyor.",220,539)),
            1536,690))
        assertNull(GtGameNotice.find(listOf(
            line("Güç",316,487,160),
            line("Konsolunuz kapanmaya hazırlanıyor.",220,539)),
            1536,690))
    }
    @Test fun originalEnglishMosesGameMessageStillWorks() {
        val notice=GtGameNotice.find(listOf(
            line("Moses",316,487,160),
            line("Clients stiffed me when it",220,539),
            line("was time to pay up. Trashed",219,571),
            line("my shop, too. They wanna...",222,603)),1536,690)
        assertNotNull(notice)
        assertEquals("sms",notice!!.kind)
        assertEquals("Moses",notice.title)
        assertTrue(notice.body.contains("stiffed me"))
    }
    @Test fun EnglishInGameTutorialStillWorks() {
        val n=GtGameNotice.find(listOf(
            line("Long guns can be stored",130,275,345),
            line("in your trunk and taken out",130,304,354),
            line("when you need them.",130,333,290)),1536,690)
        assertEquals("tip",n!!.kind)
    }
    @Test fun fixesDemonstratedIncorrectSlangWithoutChangingUnrelatedWords() {
        assertEquals("Dostum, ot arabamız nerede?",
            GtDialogueQuality.polish("Dude, where's our smoke boat?",
                "Dostum, duman teknemiz nerede?"))
        assertEquals("Arabanı çektirdim dostum. Zaten bok gibiydi!",
            GtDialogueQuality.polish(
                "I had them tow your whip, man. That thing was ugly as fuck!",
                "Kırbacını çekmelerini sağladım dostum. O şey çok çirkindi!"))
        assertEquals("Aracın çekildiği otoparka koşmamız lazım!",
            GtDialogueQuality.polish("We gotta book it to the impound!",
                "Hapishaneye kayıt ettirmeliyiz!"))
        assertEquals("Bir saat içinde malımızı satacağız!",
            GtDialogueQuality.polish("We'll be slinging our shit within the hour!",
                "Bir saat içinde bokumuzu atacağız!"))
        assertEquals("Bu bataklıkta çok sayıda ot içen insan var.",
            GtDialogueQuality.polish("There's plenty of stoners in this swamp.",
                "Bu bataklıkta çok sayıda taşçı var."))
        assertEquals("O büyük iguana memelerini görünce aklım başımdan gitti.",
            GtDialogueQuality.polish(
                "I totally spaced out when I saw them big iguana titties.",
                "O büyük iguana memelerini görünce tamamen uzaklaştım."))
        assertEquals("Mantıklıymış.",
            GtDialogueQuality.polish("Sounds like a plan.",
                "Bir plana benziyor."))
        assertEquals("Bu arabanın kırbacı değişmiş.",
            GtDialogueQuality.polish("This car's whip has changed.",
                "Bu arabanın kırbacı değişmiş."))
    }
    @Test fun colorsAndAllTranslationModesRemainActive() {
        val renderer=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        val capture=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val native=java.io.File("src/main/java/com/example/altyazi/GtNativeEngine.kt").readText()
        assertTrue(renderer.contains("Color.rgb(255,203,86)"))
        assertTrue(renderer.contains("Color.rgb(105,232,242)"))
        assertTrue(capture.contains("processGameNotice(full,noticeProbe)"))
        assertTrue(capture.contains("processMapDetailPanels(full,noticeProbe)"))
        assertTrue(capture.contains("processSubtitle(full)"))
        assertFalse(capture.contains("gtQuestBoxesOnly"))
        assertTrue(native.contains("GoogleGtxTranslator"))
        assertTrue(native.contains("MlKitTranslator"))
    }
}
''',encoding='utf8')

s=build.read_text(encoding='utf8')
s,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261221',s,count=1)
if n!=1: raise RuntimeError('Expected versionCode')
s,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-4.9-GameAlertSlangFix"',s,count=1)
if n!=1: raise RuntimeError('Expected versionName')
build.write_text(s,encoding='utf8')
print("4.9: PS5/system alerts excluded; game English SMS retained; selected slang fixed")
