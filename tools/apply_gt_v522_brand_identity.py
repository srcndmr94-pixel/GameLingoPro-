#!/usr/bin/env python3
"""GameLingoPro 5.2.2: correct accidental GameTranslator app labels.

GameTranslator v1.8.49 copyright/license/source attribution remains intact.
ONLY user-facing application branding changes; no engine/OCR/UI navigation edit.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
src=root/'app/src/main'
ui=src/'res/layout/activity_main.xml'
strings=src/'res/values/strings.xml'
main=src/'java/com/example/altyazi/MainActivity.kt'
service=src/'java/com/example/altyazi/CaptureService.kt'
tests=root/'app/src/test/java/com/example/altyazi'
gradle=root/'app/build.gradle.kts'
for p in (ui,strings,main,service,gradle):
    if not p.is_file(): raise RuntimeError('Missing expected source file '+str(p))
if 'GameLingoPro-5.2.1-CleanQA' not in gradle.read_text():
    raise RuntimeError('Only audited 5.2.1 base is supported')
def once(p,a,b):
    s=p.read_text(encoding='utf8')
    n=s.count(a)
    if n!=1:raise RuntimeError(f'{p.name}: expected one anchor {a[:75]!r} got {n}')
    p.write_text(s.replace(a,b,1),encoding='utf8')

once(ui,'android:text="GAMETRANSLATOR ALANLARI"','android:text="GAMELINGOPRO · ALTYAZI ALANLARI"')
once(ui,'GameTranslator otomatik tarama: alt konuşma altyazısı, sol görev ve ipuçları, sağ bildirimler, köşe mesajları ve oyun menüleri. Ekrandan alan seçmen gerekmez.',
    'GameLingoPro otomatik tarama: konuşma altyazıları, görev ve ipuçları, oyun bildirimleri, köşe mesajları ve menüler. Alanlar otomatik algılanır.')
once(ui,'android:text="GameTranslator · yazı rengi"','android:text="GameLingoPro · yazı rengi"')
once(ui,'android:text="GameTranslator · siyah zemin"','android:text="GameLingoPro · koyu arka plan"')
once(ui,'android:text="GameLingo Pro"','android:text="GameLingoPro"')
once(strings,'<string name="app_name">GameLingo Pro</string>',
     '<string name="app_name">GameLingoPro</string>')
once(main,'cbGoogle.text="GameTranslator · Google GTX → ML Kit (otomatik)"',
     'cbGoogle.text="GameLingoPro · Google GTX → ML Kit (otomatik)"')
once(main,'.setTitle("GameLingo Pro")','.setTitle("GameLingoPro")')
once(service,'prefs.googleCeviri -> "GameTranslator v1.8.49: Google GTX → ML Kit"',
     'prefs.googleCeviri -> "Google GTX → ML Kit (GameTranslator v1.8.49 uyarlaması)"')
once(service,'overlay.setSubtitle("GameLingo çalışıyor…", dp(80))',
     'overlay.setSubtitle("GameLingoPro çalışıyor…", dp(80))')

# Keep the old attribution and licence in the package for compliance.
licence=src/'assets/GameTranslator-LICENSE.txt'
notice=src/'assets/GameTranslator-NOTICE.txt'
if not licence.is_file() or not notice.is_file():
    raise RuntimeError('Source attribution/license is required and must remain intact')
if 'GameTranslator' in ui.read_text() or 'cbGoogle.text="GameTranslator' in main.read_text():
    raise RuntimeError('User-visible incorrect label still exists')

# A previous regression test looked for the legacy space-separated name.
legacy=tests/'GameLingoUi51Test.kt'
once(legacy,'xml.contains("GameLingo Pro")',
            'xml.contains("GameLingoPro")')

(tests/'GtBrandIdentity522Test.kt').write_text(r'''package com.example.altyazi

import org.junit.Assert.*
import org.junit.Test
import java.io.File

class GtBrandIdentity522Test {
    @Test fun applicationScreenHasOnlyGameLingoProBrand() {
        val xml=File("src/main/res/layout/activity_main.xml").readText()
        assertTrue(xml.contains("GAMELINGOPRO · ALTYAZI ALANLARI"))
        assertTrue(xml.contains("GameLingoPro otomatik tarama"))
        assertTrue(xml.contains("GameLingoPro · yazı rengi"))
        assertTrue(xml.contains("GameLingoPro · koyu arka plan"))
        assertFalse(xml.contains("GAMETRANSLATOR ALANLARI"))
        assertFalse(xml.contains("GameTranslator otomatik tarama"))
        assertFalse(xml.contains("GameTranslator ·"))
    }
    @Test fun otherUserFacingLabelsAgreeWithProductName() {
        val activity=File("src/main/java/com/example/altyazi/MainActivity.kt").readText()
        val service=File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        val strings=File("src/main/res/values/strings.xml").readText()
        assertTrue(strings.contains("<string name=\"app_name\">GameLingoPro</string>"))
        assertTrue(activity.contains("cbGoogle.text=\"GameLingoPro · Google GTX"))
        assertTrue(service.contains("GameLingoPro çalışıyor…"))
    }
    @Test fun licensedEngineProvenanceIsPreserved() {
        assertTrue(File("src/main/assets/GameTranslator-LICENSE.txt").exists())
        assertTrue(File("src/main/assets/GameTranslator-NOTICE.txt").exists())
        val source=File("src/main/java/com/example/altyazi/GtNativeEngine.kt").readText()
        assertTrue(source.contains("GameTranslator v1.8.49"))
        val service=File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(service.contains("Google GTX → ML Kit"))
        assertTrue(service.contains("processSubtitle(full)"))
        assertTrue(service.contains("processMapDetailPanels(full"))
    }
}
''',encoding='utf8')
g=gradle.read_text(encoding='utf8')
g,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
    r'\g<1>versionCode = 20261226',g,count=1)
if n!=1:raise RuntimeError('versionCode absent')
g,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-5.2.2-BrandFix"',g,count=1)
if n!=1:raise RuntimeError('versionName absent')
gradle.write_text(g,encoding='utf8')
print('GameLingoPro 5.2.2: app labels corrected, engine source attribution preserved')
