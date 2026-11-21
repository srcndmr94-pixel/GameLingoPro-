#!/usr/bin/env python3
"""Fix only GameLingoPro GT HUD/menu font size, independent of subtitle slider.

Run AFTER v3.2 GT automatic-region patches. Keep the original GameLingoPro
Kotlin app, GameTranslator renderer, colors, background, TV bridge and settings.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
tests=root/"app/src/test/java/com/example/altyazi"
contract=src/"GtStyleContract.kt"
renderer=src/"GtExactOverlay.kt"
capture=src/"CaptureService.kt"
build=root/"app/build.gradle.kts"

for file in (contract,renderer,capture,build):
    if not file.is_file():
        raise RuntimeError("Missing original GameLingoPro GT-only source: "+str(file))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text(encoding="utf-8"):
    raise RuntimeError("Wrong Android application; refusing update")
if "overlay = GtExactOverlay(this)" not in capture.read_text(encoding="utf-8"):
    raise RuntimeError("GT-only renderer is not active")

s=contract.read_text(encoding="utf-8")
old="fun hudSp(chosen:Float):Float=(chosen*.76f).coerceIn(11f,28f)"
new='fun hudSp(@Suppress("UNUSED_PARAMETER") chosen:Float):Float=12f'
if s.count(old)!=1:
    raise RuntimeError("GT HUD font contract has changed; found "+str(s.count(old)))
s=s.replace(old,new,1)
contract.write_text(s,encoding="utf-8")

overlay=renderer.read_text(encoding="utf-8")
if overlay.count("GtStyleContract.hudSp(style.boyutSp)")!=1:
    raise RuntimeError("HUD does not use the size contract exactly once")
if overlay.count("GtStyleContract.captionSp(style.boyutSp)")!=1:
    raise RuntimeError("Subtitle size contract missing")
# The actual HUD renderer uses hudSp() after each label update, so no
# per-label fontsize override is allowed.
hud=overlay.split("private fun hudStyle(tv:TextView)",1)[1].split("fun show()",1)[0]
if hud.count("setTextSize(")!=1:
    raise RuntimeError("More than one HUD fontsize override detected")
if "GtStyleContract.hudSp(style.boyutSp)" not in hud:
    raise RuntimeError("Fixed HUD contract is not applied by active renderer")

# The previous unit test explicitly required HUD size to grow with
# the subtitle slider. Replace that incorrect historical expectation.
previous=tests/"GtStyleContractTest.kt"
p=previous.read_text(encoding="utf-8")
old_assert='assertTrue(GtStyleContract.hudSp(28f)>GtStyleContract.hudSp(16f))'
if p.count(old_assert)!=1:
    raise RuntimeError("Legacy scaling assertion missing")
p=p.replace(old_assert,"""assertEquals(12f,GtStyleContract.hudSp(28f),.001f)
   assertEquals(12f,GtStyleContract.hudSp(16f),.001f)""",1)
previous.write_text(p,encoding="utf-8")

# Regression: changing the user-selected subtitle size must not change
# ANY left/right HUD/menu text. Tests use actual runtime contract.
tests.mkdir(parents=True,exist_ok=True)
(tests/"GtHudFixedFontTest.kt").write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtHudFixedFontTest {
    @Test fun everyGameHudCardUsesFixedSmallFont() {
        for (subtitleSize in listOf(12f, 16f, 20f, 28f, 34f, 60f)) {
            assertEquals(12f, GtStyleContract.hudSp(subtitleSize), .0001f)
        }
    }
    @Test fun bottomSubtitleKeepsSelectedSize() {
        assertEquals(14f, GtStyleContract.captionSp(14f), .0001f)
        assertEquals(28f, GtStyleContract.captionSp(28f), .0001f)
        assertEquals(34f, GtStyleContract.captionSp(60f), .0001f)
    }
    @Test fun liveRendererUsesIndependentContracts() {
        val code=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        val hud=code.substringAfter("private fun hudStyle(tv:TextView)")
            .substringBefore("fun show()")
        val subtitle=code.substringAfter("private fun subtitleStyle(tv:TextView)")
            .substringBefore("private fun hudStyle(tv:TextView)")
        assertTrue(hud.contains("GtStyleContract.hudSp(style.boyutSp)"))
        assertFalse(hud.contains("GtStyleContract.captionSp(style.boyutSp)"))
        assertTrue(subtitle.contains("GtStyleContract.captionSp(style.boyutSp)"))
        assertTrue(hud.contains("tv.setTextColor(style.yaziRengi)"))
    }
    @Test fun singleRendererStillActive() {
        val c=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(c.contains("overlay = GtExactOverlay(this)"))
        assertFalse(c.contains("overlay = Overlay(this)"))
    }
}
''',encoding="utf-8")

v=build.read_text(encoding="utf-8")
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
            r'\g<1>versionCode = 20261206',v,count=1)
if n!=1: raise RuntimeError("Missing versionCode")
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-3.3-GT-FixedHUD"',v,count=1)
if n!=1: raise RuntimeError("Missing versionName")
build.write_text(v,encoding="utf-8")

print("PASS: Fixed 12sp HUD/menu text independent of user subtitle size; caption size unchanged.")
