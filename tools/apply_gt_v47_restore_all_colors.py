#!/usr/bin/env python3
"""4.7: RESTORE FULL v4.4 translations and color the translated text.
No OCR scope, overlay position, translation engine, or lifetime logic changes.
Apply after v4.4, never after v4.5's disabled-translations patch.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main/java/com/example/altyazi'
cap=src/'CaptureService.kt'
view=src/'GtExactOverlay.kt'
contract=src/'Overlay.kt'
build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
for f in (cap,view,contract,build,src/'GtSelectedMapPanel.kt'):
    if not f.is_file():raise RuntimeError('GameLingoPro 4.4 source missing: '+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Wrong app package')
if 'if(!gtMapPanelMode && processGameNotice(full,noticeProbe))return' not in cap.read_text():
    raise RuntimeError('Full 4.4 notice/menu/subtitle processing must be active')
if 'gtQuestBoxesOnly' in cap.read_text() or 'val useRect=card.fitSourceBox' not in view.read_text():
    raise RuntimeError('Refusing disabled-translation or mismatched renderer')

def once(file,old,new):
    s=file.read_text(encoding='utf8')
    if s.count(old)!=1:raise RuntimeError(f'{file.name}: expected one anchor, found {s.count(old)}: {old[:85]}')
    file.write_text(s.replace(old,new,1),encoding='utf8')

once(contract,
'''        val fitSourceBox: Boolean = false''',
'''        val fitSourceBox: Boolean = false,
        val questHeading: Boolean = false,
        val questObjective: Boolean = false''')
once(cap,
'''                ready.add(titleBox.copy(text=title))''',
'''                ready.add(titleBox.copy(text=title,questHeading=true))''')
once(cap,
'''                ready.add(rect.copy(text=body))''',
'''                ready.add(rect.copy(text=body,questHeading=false))''')
once(cap,
'''            ready.add(instruction.copy(text=gtObjectiveText))''',
'''            ready.add(instruction.copy(text=gtObjectiveText,questObjective=true))''')

once(view,
'''            subtitleStyle(target)
            target.text=speakerColor(value)''',
'''            subtitleStyle(target)
            target.setTextColor(Color.rgb(111,235,244)) // translated caption
            target.text=speakerColor(value)''')
once(view,
'''                } else {
                    tv.setPadding(dp(4),dp(2),dp(4),dp(2))
                }
                tv.setLineSpacing(0f,1.05f)''',
'''                } else {
                    tv.setTextColor(Color.rgb(105,232,242)) // translated HUD
                    tv.setPadding(dp(4),dp(2),dp(4),dp(2))
                }
                tv.setLineSpacing(0f,1.05f)''')
once(view,
'''                if(useRect) {
                    // GameTranslator-like dark panel; no black floating pill.
                    tv.setTextColor(if(card.lightNotice)Color.rgb(38,48,72)
                        else Color.rgb(233,238,247))
                    tv.background=GradientDrawable().apply {
                        cornerRadius=dp(1).toFloat()
                        setColor(if(card.lightNotice)Color.rgb(235,241,248)
                            else Color.rgb(36,39,56))
                    }''',
'''                if(useRect) {
                    // Visual colors only; preserve all original OCR geometry.
                    tv.setTextColor(when {
                        card.questHeading -> Color.rgb(255,203,86) // amber
                        card.questObjective -> Color.rgb(178,242,125) // green
                        card.lightNotice -> Color.rgb(22,106,125)
                        else -> Color.rgb(105,232,242) // turquoise
                    })
                    tv.background=GradientDrawable().apply {
                        cornerRadius=dp(1).toFloat()
                        setColor(if(card.lightNotice)Color.rgb(236,242,248)
                            else Color.rgb(17,24,38)) // opaque dark
                    }''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtColorsAllTranslation47Test.kt').write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtColorsAllTranslation47Test {
    @Test fun allTranslatedAreasUseDistinctColors() {
        val code=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(code.contains("Color.rgb(255,203,86) // amber"))
        assertTrue(code.contains("Color.rgb(105,232,242) // turquoise"))
        assertTrue(code.contains("Color.rgb(178,242,125) // green"))
        assertTrue(code.contains("Color.rgb(111,235,244)"))
        assertTrue(code.contains("Color.rgb(17,24,38)"))
    }
    @Test fun subtitlesSmsMapAndOtherHudRemainEnabled() {
        val code=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(code.contains("processSubtitle(full)"))
        assertTrue(code.contains("processGameNotice(full,noticeProbe)"))
        assertTrue(code.contains("processMapDetailPanels(full,noticeProbe)"))
        assertTrue(code.contains("GtAllHud.group"))
        assertFalse(code.contains("gtQuestBoxesOnly()"))
    }
    @Test fun originalOcrGeometryIsNotAltered() {
        val code=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(code.contains("val useRect=card.fitSourceBox"))
        assertTrue(code.contains("val sourceW=if(useRect)originalWidth.coerceAtMost(w)"))
        assertTrue(code.contains("val sourceH=if(useRect)originalHeight.coerceAtMost(h)"))
    }
    @Test fun titleAndObjectiveRolesAreIndependentAndOptional() {
        assertTrue(Overlay.Label("Başlık",0,0,questHeading=true).questHeading)
        assertTrue(Overlay.Label("Hedef",0,0,questObjective=true).questObjective)
        assertFalse(Overlay.Label("Normal",0,0).questHeading)
    }
}
''',encoding='utf8')

version=build.read_text(encoding='utf8')
version,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261219',version,count=1)
if n!=1:raise RuntimeError('Missing versionCode')
version,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-4.7-AllTranslations-Colored"',version,count=1)
if n!=1:raise RuntimeError('Missing versionName')
build.write_text(version,encoding='utf8')
print('4.7: all 4.4 translations remain active; color changes only')
