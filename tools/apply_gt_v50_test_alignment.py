#!/usr/bin/env python3
"""Retain legacy regression coverage while checking upgraded 5.0 geometry."""
from pathlib import Path
root=Path("app/src/test/java/com/example/altyazi")
colors=root/"GtColorsAllTranslation47Test.kt"
layout=root/"GtExactMapRegions44Test.kt"
for p in (colors,layout):
    if not p.is_file():raise RuntimeError("Missing existing test "+str(p))
s=colors.read_text(encoding="utf8")
old='code.contains("Color.rgb(17,24,38)")'
new='code.contains("Color.argb(248,17,24,38)")'
if s.count(old)!=1:raise RuntimeError("Unexpected source color regression test")
colors.write_text(s.replace(old,new,1),encoding="utf8")
s=layout.read_text(encoding="utf8")
start=s.find("@Test fun labelsUseCaptureFrameNotGuessedPhoneScreenWidth()")
if start<0:raise RuntimeError("Expected map geometry regression missing")
brace=s.find("{",start)
level=0;end=-1
for i in range(brace,len(s)):
    if s[i]=="{":level+=1
    elif s[i]=="}":
        level-=1
        if level==0:
            end=i+1
            break
if end<0:raise RuntimeError("Unbalanced original test")
replacement='''@Test fun labelsUseCaptureFrameNotGuessedPhoneScreenWidth() {
        val view=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        val service=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        // The capture frame is the source of truth; never guessed phone metrics.
        assertTrue(view.contains("card.frameWidth>0 && card.frameHeight>0"))
        assertTrue(view.contains("w.toFloat()/card.frameWidth"))
        assertTrue(view.contains("h.toFloat()/card.frameHeight"))
        assertTrue(view.contains("val displayW=if(useRect)"))
        assertTrue(view.contains("val displayH=if(useRect)"))
        assertTrue(view.contains("lp.width=displayW"))
        assertTrue(view.contains("if(useRect || card.gameNotice)displayH"))
        assertTrue(service.contains("frameWidth=width,frameHeight=height,fitSourceBox=true"))
    }'''
layout.write_text(s[:start]+replacement+s[end:],encoding="utf8")
print("Updated 4.4 frame-mapping and 4.7 color regressions for 5.0 geometry; no tests disabled")
