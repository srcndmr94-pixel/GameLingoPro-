#!/usr/bin/env python3
"""Fix the final, active subtitle text-size override in native GameLingoPro.

Applies after apply_gt_v29_adjustable_style.py. Never replace the app.
"""
from pathlib import Path
import re, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
ov=src/"Overlay.kt"
build=root/"app/build.gradle.kts"
assert 'applicationId = "com.gamelingo.pro"' in build.read_text()
s=ov.read_text(encoding="utf8")
old='''            val gtSize = if (context.resources.configuration.orientation ==
                Configuration.ORIENTATION_LANDSCAPE) 15.5f else 16f
            t.setTextSize(TypedValue.COMPLEX_UNIT_SP,
                (gtSize * scale).coerceAtLeast(11f))'''
new='''            // Real subtitle must honour the chosen size. The old GT 15.5sp
            // override ran AFTER stiliUygula() and silently undid the slider.
            t.setTextSize(TypedValue.COMPLEX_UNIT_SP,
                stil.boyutSp.coerceIn(12f, 60f))'''
if s.count(old)!=1:raise RuntimeError("Could not locate the active GT text-size override")
s=s.replace(old,new,1)
old_labels=[
  '(stil.boyutSp * .78f).coerceIn(12f, 32f)',
  '(stil.boyutSp*.78f).coerceIn(12f,32f)'
]
for old in old_labels:
    if old not in s:raise RuntimeError("Missing HUD label size mapping: "+old)
    s=s.replace(old,old.replace('.78f','.90f').replace('12f, 32f','14f, 48f').replace('12f,32f','14f,48f'))
ov.write_text(s,encoding="utf8")
assert '15.5f' not in s
assert 'gtSize' not in s
assert 'stil.boyutSp.coerceIn(12f, 60f)' in s
b=build.read_text(encoding="utf8")
b,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261201',b,count=1)
if n!=1:raise RuntimeError("Version code missing")
b,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-2.9.1-GT-SizeFix"',b,count=1)
if n!=1:raise RuntimeError("Version name missing")
build.write_text(b,encoding="utf8")
test=root/"app/src/test/java/com/example/altyazi/GtRenderedSizeTest.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtRenderedSizeTest {
  private val overlay by lazy {
    java.io.File("src/main/java/com/example/altyazi/Overlay.kt").readText()
  }
  @Test fun noHardcodedSmallSubtitleSizes() {
    assertFalse(overlay.contains("val gtSize"))
    assertFalse(overlay.contains("15.5f"))
    assertTrue(overlay.contains("stil.boyutSp.coerceIn(12f, 60f)"))
    assertTrue(overlay.contains("t.setTextColor(stil.yaziRengi)"))
    assertTrue(overlay.contains("Color.red(stil.arkaRenk)"))
  }
  @Test fun everyHudCardReadsSelectedSize() {
    assertTrue(overlay.contains("stil.boyutSp * .90f"))
    assertTrue(overlay.contains("stil.boyutSp*.90f"))
  }
}
''',encoding="utf8")
# Update the previous version's assertion: intentionally enlarged HUD cards.
previous_test=root/"app/src/test/java/com/example/altyazi/GtActualAppearanceTest.kt"
if not previous_test.exists():raise RuntimeError("Previous appearance test not found")
old_test=previous_test.read_text(encoding="utf8")
if ".78f" not in old_test:raise RuntimeError("Previous test expectation changed")
previous_test.write_text(old_test.replace(".78f",".90f"),encoding="utf8")
print("PASS: GameLingoPro actual caption size/color and HUD size use saved selections")
