#!/usr/bin/env python3
"""4.6: color translated quest HEADING amber, BODY cyan with opaque masking.
Only presentation changes; keep 4.5 selected map-card scope and clearing.
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
for f in (cap,view,contract,build,src/'GtMapBoxOnly.kt'):
    if not f.is_file():raise RuntimeError('GameLingoPro 4.5 source missing: '+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Wrong app package')
if 'if(gtQuestBoxesOnly())' not in cap.read_text() or 'val useRect=card.fitSourceBox' not in view.read_text():
    raise RuntimeError('Only v4.5 exact boxed mission renderer accepted')

def once(file,old,new):
    s=file.read_text(encoding='utf8')
    if s.count(old)!=1:raise RuntimeError(f'{file.name}: expected one anchor, found {s.count(old)}: {old[:85]}')
    file.write_text(s.replace(old,new,1),encoding='utf8')

once(contract,
'''        val fitSourceBox: Boolean = false''',
'''        val fitSourceBox: Boolean = false,
        val questHeading: Boolean = false''')
once(cap,
'''                ready.add(titleBox.copy(text=title))''',
'''                ready.add(titleBox.copy(text=title,questHeading=true))''')
once(cap,
'''                ready.add(rect.copy(text=body))''',
'''                ready.add(rect.copy(text=body,questHeading=false))''')

once(view,
'''                if(useRect) {
                    // GameTranslator-like dark panel; no black floating pill.
                    tv.setTextColor(if(card.lightNotice)Color.rgb(38,48,72)
                        else Color.rgb(233,238,247))
                    tv.background=GradientDrawable().apply {
                        cornerRadius=dp(1).toFloat()
                        setColor(if(card.lightNotice)Color.rgb(235,241,248)
                            else Color.rgb(36,39,56))
                    }
                    tv.setPadding(dp(1),0,dp(1),0)
                    tv.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
                    tv.setLineSpacing(0f,1f)
                    tv.maxLines=card.sourceLines.coerceIn(1,8)+1
                    tv.ellipsize=android.text.TextUtils.TruncateAt.END
                }''',
'''                if(useRect) {
                    // Original English is white/gray. Turkish mission
                    // heading is AMBER; description is TURQUOISE.
                    // Fully opaque rectangle hides source glyphs beneath it.
                    tv.text=card.text
                    tv.setTextColor(if(card.questHeading)Color.rgb(255,202,92)
                        else Color.rgb(105,232,242))
                    tv.typeface=Typeface.create("sans-serif-medium",
                        if(card.questHeading)Typeface.BOLD else Typeface.NORMAL)
                    tv.background=GradientDrawable().apply {
                        cornerRadius=dp(1).toFloat()
                        setColor(Color.rgb(17,23,37)) // opaque
                    }
                    tv.setPadding(dp(2),0,dp(2),0)
                    tv.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
                    tv.setLineSpacing(0f,1f)
                    tv.maxLines=if(card.questHeading)1 else card.sourceLines.coerceIn(1,8)+1
                    tv.ellipsize=android.text.TextUtils.TruncateAt.END
                }''')
once(view,
'''                val sourceW=if(useRect)originalWidth.coerceAtMost(w)
                    else GtSourceBox.width(originalWidth,w,dp(8)).coerceAtLeast(dp(38))
                val sourceH=if(useRect)originalHeight.coerceAtMost(h)
                    else (originalHeight+dp(7)).coerceAtLeast(dp(17))''',
'''                val sourceW=if(useRect)(originalWidth+dp(4)).coerceAtMost(w)
                    else GtSourceBox.width(originalWidth,w,dp(8)).coerceAtLeast(dp(38))
                val sourceH=if(useRect)(originalHeight+dp(3)).coerceAtMost(h)
                    else (originalHeight+dp(7)).coerceAtLeast(dp(17))''')
once(view,
'''                val x=(if(useRect)sourceX else sourceX-dp(4))
                    .coerceIn(0,(w-sourceW).coerceAtLeast(0))
                val y=(if(useRect)sourceY else sourceY-dp(2))
                    .coerceIn(0,(h-measuredH).coerceAtLeast(0))''',
'''                val x=(if(useRect)sourceX-dp(2) else sourceX-dp(4))
                    .coerceIn(0,(w-sourceW).coerceAtLeast(0))
                val y=(if(useRect)sourceY-dp(1) else sourceY-dp(2))
                    .coerceIn(0,(h-measuredH).coerceAtLeast(0))''')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtQuestColor46Test.kt').write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtQuestColor46Test {
    @Test fun headingAndBodyAreDistinctAndOpaque() {
        val code=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(code.contains("if(card.questHeading)Color.rgb(255,202,92)"))
        assertTrue(code.contains("else Color.rgb(105,232,242)"))
        assertTrue(code.contains("setColor(Color.rgb(17,23,37))"))
        assertTrue(code.contains("val sourceW=if(useRect)(originalWidth+dp(4))"))
        assertTrue(code.contains("val sourceH=if(useRect)(originalHeight+dp(3))"))
    }
    @Test fun mapBoxScopeAndOriginalGeometryArePreserved() {
        val code=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(code.contains("if(gtQuestBoxesOnly())"))
        assertTrue(code.contains("ready.add(titleBox.copy(text=title,questHeading=true))"))
        assertTrue(code.contains("ready.add(rect.copy(text=body,questHeading=false))"))
        assertTrue(code.contains("processMapDetailPanels(full,noticeProbe)"))
        assertFalse(code.contains("val obj=GtSelectedMapPanel.objective(lines,width,height)"))
    }
    @Test fun otherLabelsHaveNoQuestHeadingRoleByDefault() {
        assertFalse(Overlay.Label("A",0,0).questHeading)
        assertTrue(Overlay.Label("Görev",0,0,questHeading=true).questHeading)
    }
}
''',encoding='utf8')
version=build.read_text(encoding='utf8')
version,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261218',version,count=1)
if n!=1:raise RuntimeError('Missing versionCode')
version,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-4.6-ColoredQuestBoxes"',version,count=1)
if n!=1:raise RuntimeError('Missing versionName')
build.write_text(version,encoding='utf8')
print('4.6: amber heading, cyan text, opaque source rectangle; scope unchanged')
