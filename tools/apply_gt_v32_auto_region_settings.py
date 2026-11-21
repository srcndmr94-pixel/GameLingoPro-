#!/usr/bin/env python3
"""GameLingoPro GT-only: replace outdated manual screen-area UI with automatic zones.
Keep legacy views mounted (hidden) so MainActivity bindings and existing settings
remain compatible; native runtime uses GtAllHud, GtMenuUi, GtExactOverlay.
"""
from pathlib import Path
import re,sys
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
res=root/"app/src/main/res/layout/activity_main.xml"
main=root/"app/src/main/java/com/example/altyazi/MainActivity.kt"
cap=root/"app/src/main/java/com/example/altyazi/CaptureService.kt"
build=root/"app/build.gradle.kts"
if not all(f.exists() for f in (res,main,cap,build)):
    raise RuntimeError("Original GameLingoPro source missing")
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Not original GameLingoPro")
c=cap.read_text()
if "overlay = GtExactOverlay(this)" not in c:
    raise RuntimeError("GT-only renderer is not active")
if "GtMenuUi.group" not in c or "GtAllHud.group" not in c:
    raise RuntimeError("GT automatic HUD/menu scan is not enabled")
s=res.read_text(encoding="utf-8")
first="        <!-- ======================= ALTYAZI BÖLGESİ ======================= -->"
last="        <!-- ======================= ALTYAZI GÖRÜNÜMÜ ======================= -->"
a=s.find(first); b=s.find(last,a+len(first))
if a<0 or b<0:raise RuntimeError("Screen-area XML section missing")
section=s[a:b]
needle='''                <TextView
                    android:id="@+id/tvRegion"'''
if section.count(needle)!=1:
    raise RuntimeError("Region settings anchor changed")
replacement='''                <TextView
                    style="@style/LingoHint"
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginTop="8dp"
                    android:text="Otomatik GameTranslator taraması: konuşma altyazısı, sol görev ve ipuçları, sağ bildirimler, alt köşe mesajları ve oyun menüleri. Alan seçmen gerekmez." />

                <!-- Compatibility-only bindings; no longer exposed to users. -->
                <LinearLayout
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:orientation="vertical"
                    android:visibility="gone">

'''
section=section.replace(needle,replacement+needle,1)
end='''            </LinearLayout>
        </com.google.android.material.card.MaterialCardView>'''
if section.count(end)!=1:raise RuntimeError("Region card end changed")
section=section.replace(end,'''                </LinearLayout>
            </LinearLayout>
        </com.google.android.material.card.MaterialCardView>''',1)
section=section.replace('android:text="Nereye bakılsın"',
                        'android:text="GAMETRANSLATOR ALANLARI"',1)
section=section.replace('android:text="Altyazı bölgesi"',
                        'android:text="Otomatik ekran taraması"',1)
s=s[:a]+section+s[b:]
s=s.replace('android:text="Ekran alanı"',
            'android:text="Otomatik OCR alanları"',1)
s=s.replace('android:text="Altyazı bölgesi ve yan yazı alanı"',
            'android:text="Altyazı · sol/sağ görev · bildirim · menü"',1)
ET.fromstring(s)
for view in ("cbMenu","cbYanSol","cbYanSag","sbTop","sbBottom",
             "tvRegion","btnRegion","btnMenuAlan","cbSpeaker"):
    if '@+id/'+view not in section:
        raise RuntimeError("Settings binding lost: "+view)
res.write_text(s,encoding="utf-8")
m=main.read_text(encoding="utf-8")
old='"Ekran alanı", "Yazı ve görünüm"'
if m.count(old)!=1:raise RuntimeError("Settings navigation title changed")
main.write_text(m.replace(old,'"Otomatik OCR alanları", "Yazı ve görünüm"',1),
                encoding="utf-8")
v=build.read_text(encoding="utf-8")
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
            r'\g<1>versionCode = 20261205',v,count=1)
if n!=1:raise RuntimeError("versionCode missing")
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-3.2-GT-AutoRegions"',v,count=1)
if n!=1:raise RuntimeError("versionName missing")
build.write_text(v,encoding="utf-8")
print("GameLingoPro GT-only: manual region UI hidden, automatic zone view installed")
