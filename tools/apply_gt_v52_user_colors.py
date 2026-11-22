#!/usr/bin/env python3
"""GameLingoPro 5.2: live user-selected translation colors, reliable preview,
short-dialogue sense correction, and conservative right-bottom game alerts.

Apply after successful GameLingoPro 5.1 native UI patch. Translation engines,
OCR region selection, spoken captions, map boxes, TV/webOS/PS tools unchanged.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
tests=root/'app/src/test/java/com/example/altyazi'
view=src/'GtExactOverlay.kt'
main=src/'MainActivity.kt'
notice=src/'GtGameNotice.kt'
quality=src/'GtDialogueQuality.kt'
capture=src/'CaptureService.kt'
build=root/'app/build.gradle.kts'
for file in (view,main,notice,quality,capture,build):
    if not file.is_file(): raise RuntimeError('5.1 complete source missing '+str(file))
if 'GameLingoPro-5.1-CleanUI' not in build.read_text():
    raise RuntimeError('Expected 5.1 base')
if 'gtQuestBoxesOnly' in capture.read_text():
    raise RuntimeError('Translation scopes must remain enabled')
if 'GoogleGtxTranslator' not in (src/'GtNativeEngine.kt').read_text():
    raise RuntimeError('GT/GTX translator chain missing')

def once(file,old,new):
    s=file.read_text(encoding='utf-8')
    n=s.count(old)
    if n!=1:raise RuntimeError(f'{file.name}: expected one match, got {n}: {old[:110]}')
    file.write_text(s.replace(old,new,1),encoding='utf-8')

# 4.7 hardcoded a cyan caption and role-dependent HUD colors. They overrode
# Preferences on *every redraw*, making user-selected white/green/yellow inert.
once(view,
    '            target.setTextColor(Color.rgb(111,235,244)) // translated caption',
    '            target.setTextColor(style.yaziRengi) // live user-selected color')
once(view,
    '                    tv.setTextColor(Color.rgb(105,232,242)) // translated HUD',
    '                    tv.setTextColor(style.yaziRengi) // live HUD color')
once(view,
'''                    tv.setTextColor(when {
                        card.questHeading -> Color.rgb(255,203,86) // amber
                        card.questObjective -> Color.rgb(178,242,125) // green
                        card.lightNotice -> Color.rgb(22,106,125)
                        else -> Color.rgb(105,232,242) // turquoise
                    })''',
'''                    // Respect selected white/yellow/green/turquoise on all
                    // source-positioned game, mission and objective labels.
                    tv.setTextColor(style.yaziRengi)
                    tv.typeface=Typeface.create("sans-serif-medium",
                        if(card.questHeading)Typeface.BOLD else Typeface.NORMAL)''')
once(view,
'''                    tv.setTextColor(if(light)Color.rgb(40,53,83) else Color.WHITE)
                    tv.background=GradientDrawable().apply{
                        cornerRadius=dp(3).toFloat()
                        setColor(if(light)Color.rgb(233,240,248) else Color.rgb(51,49,65))
                    }''',
'''                    // Dark backdrop keeps all user-selected light font colors
                    // readable even when the original game notice was pale.
                    tv.setTextColor(style.yaziRengi)
                    tv.background=GradientDrawable().apply{
                        cornerRadius=dp(3).toFloat()
                        setColor(Color.argb(248,17,24,38))
                    }''')
once(view,
'''                        setColor(if(card.lightNotice)Color.argb(248,236,242,248)
                            else Color.argb(248,17,24,38)) // masked translucent''',
'''                        setColor(Color.argb(248,17,24,38)) // readable mask
                        // Background color remains independent of text color.''')

# Color preview formerly supported only yellow vs white. Use same mapping as
# the overlay and persist the color on click (no restart/save button needed).
once(main,
'''        tvPreview.setTextColor(if (renkSecim == Prefs.COLOR_YELLOW)
            android.graphics.Color.YELLOW else android.graphics.Color.WHITE)''',
'''        tvPreview.setTextColor(SubtitleStyle.yaziRengi(renkSecim))''')
once(main,
'''        cgSubColor.setOnCheckedStateChangeListener(onizlemeDinleyici)''',
'''        cgSubColor.setOnCheckedStateChangeListener { _, _ ->
            // Apply selected color immediately even if user returns straight
            // to the game without pressing Start or leaving Settings.
            prefs.subtitleColor=when(cgSubColor.checkedChipId) {
                R.id.chColYellow -> Prefs.COLOR_YELLOW
                R.id.chColGreen -> Prefs.COLOR_GREEN
                R.id.chColCyan -> Prefs.COLOR_CYAN
                else -> Prefs.COLOR_WHITE
            }
            onizlemeyiGuncelle()
        }''')

# Prior corner notifier accepted any single English sentence ending in "!",
# so the last spoken line of a video after rotation became a "game notice".
s=notice.read_text(encoding='utf-8')
begin=s.index('            val cornerCue=Regex(')
end=s.index('\n            if(body.length>=25',begin)
s=s[:begin]+'''            val cornerCue=Regex(
                """(?i)\\b(?:objective|mission|new|reward|complete|available|""" +
                """collect|meet|drive|reach|find|delivered)\\b""")
'''.rstrip('\n')+s[end:]
notice.write_text(s,encoding='utf-8')
once(notice,
'''            if(body.length>=25 && (gameEnglish(body) ||
                    cornerCue.containsMatchIn(body)) &&
                !psShell.containsMatchIn(body) &&
                (rows.size>=2 || body.any{it=='.'||it=='!'||it=='?'})) {''',
'''            if(w>h && body.length>=25 && (gameEnglish(body) ||
                    cornerCue.containsMatchIn(body)) &&
                !psShell.containsMatchIn(body) &&
                // Generic speech is not a game notification. Single-line
                // notices need an explicit game objective/action cue.
                (rows.size>=2 || cornerCue.containsMatchIn(body))) {''')

# Explicit recorded mistranslation; no global grammatical rewrite.
once(quality,
'''        if(english.matches(Regex("""don't sweat[.!…]*""")))
            return "Takma kafana."''',
'''        if(english.matches(Regex("""don't sweat[.!…]*""")))
            return "Takma kafana."
        if(english.matches(Regex("""i wouldn['’]t try that(?:,?\\s+my dear)?[.!…]*"""))) {
            return if(english.contains("my dear")) "Yerinde olsam bunu denemezdim, canım."
                else "Yerinde olsam bunu denemezdim."
        }''')

# Previously introduced tests pinned hardcoded colors. Keep coverage, but
# assert that all categories use preference-derived color instead.
test=tests/'GtColorsAllTranslation47Test.kt'
old=test.read_text(encoding='utf-8')
a=old.index('    @Test fun allTranslatedAreasUseDistinctColors()')
b=old.index('    @Test fun subtitlesSmsMapAndOtherHudRemainEnabled()',a)
new='''    @Test fun allTranslatedAreasUseUserSelectedColors() {
        val code=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(code.contains("target.setTextColor(style.yaziRengi)"))
        assertTrue(code.contains("tv.setTextColor(style.yaziRengi)"))
        assertFalse(code.contains("Color.rgb(111,235,244)"))
        assertFalse(code.contains("Color.rgb(105,232,242)"))
        assertTrue(code.contains("Color.argb(248,17,24,38)"))
    }
'''
test.write_text(old[:a]+new+old[b:],encoding='utf-8')

# Existing 5.0 regressions check old fixed headings and custom styles;
# update assertions to verify role distinction with selected user colors.
for name in ('GtCornerNotice50Test.kt','GtObservedLog49Test.kt','GtColorsAllTranslation47Test.kt'):
    f=tests/name
    old=f.read_text(encoding='utf8')
    old=old.replace(
        'v.contains("questHeading -> Color.rgb(255,203,86)")',
        'v.contains("if(card.questHeading)Typeface.BOLD else Typeface.NORMAL")')
    old=old.replace(
        'renderer.contains("Color.rgb(255,203,86)")',
        'renderer.contains("if(card.questHeading)Typeface.BOLD else Typeface.NORMAL")')
    old=old.replace(
        'renderer.contains("Color.rgb(105,232,242)")',
        'renderer.contains("tv.setTextColor(style.yaziRengi)")')
    f.write_text(old,encoding='utf8')
# 4.7-era color tests were not the only old static-color assumptions.
for f in tests.glob('*.kt'):
    if f.name in ('GtColorsAllTranslation47Test.kt','GtObservedLog49Test.kt','GtCornerNotice50Test.kt'):
        continue
    content=f.read_text(encoding='utf8')
    for value in ('Color.rgb(255,203,86)','Color.rgb(105,232,242)',
                  'Color.rgb(111,235,244)','Color.rgb(178,242,125)'):
        if value in content:
            raise RuntimeError('Unmigrated fixed-color test '+str(f)+': '+value)

(tests/'GtUserColor52Test.kt').write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtUserColor52Test {
    @Test fun selectedColorActuallyReachesCaptionAndEveryTranslatedHudLabel() {
        val ui=java.io.File("src/main/java/com/example/altyazi/MainActivity.kt").readText()
        val renderer=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        val prefs=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(ui.contains("prefs.subtitleColor=when(cgSubColor.checkedChipId)"))
        assertTrue(ui.contains("tvPreview.setTextColor(SubtitleStyle.yaziRengi(renkSecim))"))
        assertTrue(renderer.contains("target.setTextColor(style.yaziRengi)"))
        assertTrue(renderer.contains("tv.setTextColor(style.yaziRengi)"))
        assertFalse(renderer.contains("Color.rgb(111,235,244)"))
        assertFalse(renderer.contains("Color.rgb(105,232,242)"))
        assertTrue(prefs.contains("SubtitleStyle.yaziRengi(prefs.subtitleColor)"))
    }
    @Test fun subtitleAfterOrientationChangeNotMisclassifiedAsSingleLineNotice() {
        val speech=GtGameNotice.find(listOf(
            GtAllHud.Line("Or... Charlie can come back to absolutely nothing!",
                650,1400,920,1440)), 960,2142)
        assertNull(speech)
        val single=GtGameNotice.find(listOf(
            GtAllHud.Line("Or... Charlie can come back to absolutely nothing!",
                1040,580,1450,605)), 1536,690)
        assertNull(single)
    }
    @Test fun genuineGameMissionNoticeStillDetected() {
        val notice=GtGameNotice.find(listOf(
            GtAllHud.Line("New objective available",1040,545,1350,570),
            GtAllHud.Line("Meet your contact at the docks.",1040,574,1370,600)),
            1536,690)
        assertNotNull(notice)
        assertEquals("corner",notice!!.kind)
    }
    @Test fun naturalSpokenWarningDoesNotSwitchSubject() {
        assertEquals("Yerinde olsam bunu denemezdim, canım.",
            GtDialogueQuality.polish("I wouldn't try that my dear.",
                "Bunu denemeyeceğim canım."))
    }
    @Test fun allTranslationCategoriesAndStyledUiAreStillActive() {
        val capture=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val ui=java.io.File("src/main/java/com/example/altyazi/MainActivity.kt").readText()
        assertTrue(capture.contains("processSubtitle(full)"))
        assertTrue(capture.contains("processGameNotice(full,noticeProbe)"))
        assertTrue(capture.contains("processMapDetailPanels(full,noticeProbe)"))
        assertTrue(ui.contains("private fun showUiPage(settings:Boolean)"))
        assertFalse(capture.contains("gtQuestBoxesOnly"))
    }
}
''',encoding='utf-8')
v=build.read_text(encoding='utf-8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
    r'\g<1>versionCode = 20261224',v,count=1)
if n!=1:raise RuntimeError('version code not found')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-5.2-UserColors"',v,count=1)
if n!=1:raise RuntimeError('version name not found')
build.write_text(v,encoding='utf-8')
print('GameLingoPro 5.2: user colors apply to subtitle, HUD and menu; right corner false positives reduced')
