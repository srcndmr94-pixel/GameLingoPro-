#!/usr/bin/env python3
"""Prepare user's v1.8.49-based GameLingoPro Android tree for Flutter build.

Requires the v1.8.49 source, verified against hashes from the uploaded archive.
All upstream PSN/Remote Play/TV feature screens are retained. Applies the
standalone left/right HUD patch from this repository; no placeholder UI.
"""
from pathlib import Path
import hashlib
import zipfile
import subprocess
import shutil
import sys
import re

checkout=Path(sys.argv[1]).resolve()
repo=Path(__file__).resolve().parents[1]
expected={
 "mobile/pubspec.yaml":"11581231d287ccd46f54726d2761a030bc6cf15164ee726191384457fde06392",
 "mobile/lib/settings_page.dart":"dac2c7d85f5e78758ee4984c7e3c6cc99d6f8cd5df545425bb6dccb563244076",
 "mobile/android/app/src/main/cpp/gt_native.c":"288e32d51793265624888bbca4cb83d00496509f68b6e54fc572ee0731c5baa4"
}
for rel,h in expected.items():
    p=checkout/rel
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:
        raise SystemExit("Source mismatch for "+rel+"; refusing to substitute a different GameTranslator version.")

mobile=checkout/"mobile"
pub=mobile/"pubspec.yaml"
s=pub.read_text(encoding="utf-8")
s=s.replace("name: gametranslator_mobile","name: gamelingopro_mobile")
pub.write_text(s,encoding="utf-8")
for p in (mobile/"lib").rglob("*.dart"):
    text=p.read_text(encoding="utf-8")
    text=text.replace("package:gametranslator_mobile/","package:gamelingopro_mobile/")
    text=text.replace("GameTranslator", "GameLingoPro")
    text=text.replace("Color(0xFF0A84FF)","Color(0xFF28DEE6)")
    text=text.replace("Color(0xFFBF5AF2)","Color(0xFFB35CFF)")
    p.write_text(text,encoding="utf-8")

gradle=mobile/"android/app/build.gradle.kts"
s=gradle.read_text(encoding="utf-8")
s=s.replace('applicationId = "com.gametranslator.gametranslator_mobile"',
            'applicationId = "com.gamelingo.pro"')
gradle.write_text(s,encoding="utf-8")
manifest=mobile/"android/app/src/main/AndroidManifest.xml"
s=manifest.read_text(encoding="utf-8").replace('android:label="GameTranslator"','android:label="GameLingoPro"')
manifest.write_text(s,encoding="utf-8")

for p in (checkout/"tv/webos").glob("*.js"):
    text=p.read_text(encoding="utf-8",errors="replace")
    text=text.replace("GameTranslator","GameLingoPro")
    p.write_text(text,encoding="utf-8")

# Apply the user's requested GameTranslator left-mission/right-HUD implementation
# to real Flutter + Kotlin + SSE webOS sources (not the old unrelated Kotlin app).
work=checkout.parent
pre=work/"GameLingoPro-pre-hud.zip"
with zipfile.ZipFile(pre,"w",zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for p in checkout.rglob("*"):
        if p.is_file() and ".git" not in p.relative_to(checkout).parts and "third-party" not in p.relative_to(checkout).parts:
            z.write(p,arcname=str(Path("GameLingoPro")/p.relative_to(checkout)))
patched=work/"GameLingoPro-HUD.zip"
subprocess.run([sys.executable,str(repo/"tools/gametranslator_1849_hud/apply_hud_patch.py"),str(pre),str(patched)],check=True)
with zipfile.ZipFile(patched) as z:
    for name in z.namelist():
        if name.endswith("/"):continue
        dest=checkout/Path(name).relative_to("GameLingoPro")
        if not dest.exists() or name.endswith((
           "HudRegionPipeline.kt","SubtitleServer.kt","Store.kt","bridge.dart",
           "settings_page.dart","Engine.kt","app.js")):
            dest.parent.mkdir(parents=True,exist_ok=True)
            if name.endswith(("HudRegionPipeline.kt","SubtitleServer.kt","Store.kt","bridge.dart",
                              "settings_page.dart","Engine.kt","app.js")):
                dest.write_bytes(z.read(name))
assert 'sideHudEnabled' in (checkout/"mobile/lib/settings_page.dart").read_text()
assert 'com.gamelingo.pro' in gradle.read_text()
print("Ready: full source-matched GameLingoPro native mobile + TV + side HUD")
