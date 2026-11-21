#!/usr/bin/env python3
"""Replace old manual ROI controls with GT automatic-region information.
Keep hidden compatibility views so all existing MainActivity bindings survive.
"""
from pathlib import Path
import re,sys
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
res=root/"app/src/main/res/layout/activity_main.xml"
main=root/"app/src/main/java/com/example/altyazi/MainActivity.kt"
cap=root/"app/src/main/java/com/example/altyazi/CaptureService.kt"
build=root/"app/build.gradle.kts"
for file in (res,main,cap,build):
    if not file.is_file():raise RuntimeError("Missing original GameLingoPro file "+str(file))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Wrong application")
c=cap.read_text()
for marker in ("overlay = GtExactOverlay(this)","GtMenuUi.group","GtAllHud.group"):
    if marker not in c:raise RuntimeError("GT-only renderer or auto area scan not enabled: "+marker)

ns="{http://schemas.android.com/apk/res/android}"
ET.register_namespace("android","http://schemas.android.com/apk/res/android")
ET.register_namespace("app","http://schemas.android.com/apk/res-auto")
tree=ET.parse(res)
document=tree.getroot()
def view(id):
    items=[node for node in document.iter() if node.get(ns+"id")==id]
    if len(items)!=1:raise RuntimeError("Expected one Android view: "+id)
    return items[0]

section=view("@+id/secRegion")
container=next((c for c in section if c.tag=="LinearLayout"),None)
if container is None:raise RuntimeError("Legacy region container missing")
label=next((node for node in container if node.tag=="TextView" and
    node.get(ns+"text")=="Nereye bakılsın"),None)
title=next((node for node in container if node.tag=="TextView" and
    node.get(ns+"text")=="Altyazı bölgesi"),None)
if label is None or title is None:raise RuntimeError("Region heading changed")
label.set(ns+"text","GAMETRANSLATOR ALANLARI")
title.set(ns+"text","Otomatik ekran taraması")

def add(parent,tag,attributes):
    element=ET.SubElement(parent,tag)
    for key,value in attributes.items():
        element.set(ns+key,value)
    return element

hidden=ET.Element("LinearLayout")
hidden.set(ns+"layout_width","match_parent")
hidden.set(ns+"layout_height","wrap_content")
hidden.set(ns+"orientation","vertical")
hidden.set(ns+"visibility","gone")
for child in list(container):
    if child is label or child is title:continue
    container.remove(child)
    hidden.append(child)
add(container,"TextView",dict(layout_width="match_parent",
    layout_height="wrap_content",layout_marginTop="10dp",
    text="GameTranslator otomatik tarama: alt konuşma altyazısı, sol görev ve ipuçları, sağ bildirimler, köşe mesajları ve oyun menüleri. Ekrandan alan seçmen gerekmez."))
container.append(hidden)

row=view("@+id/ayarSatir1")
heading=next((e for e in row.iter() if e.tag=="TextView" and
    e.get(ns+"text") not in (None,"›")),None)
if heading is None:raise RuntimeError("Settings section label not found")
heading.set(ns+"text","Otomatik OCR alanları")
view("@+id/ayarOzet1").set(ns+"text","Altyazı · sol/sağ görev · bildirim · menü")

# Crucial: legacy setting IDs are preserved for old MainActivity listeners,
# but their common parent is GONE and no manual ROI controls appear.
legacy={"@+id/cbMenu","@+id/cbYanSol","@+id/cbYanSag",
        "@+id/sbTop","@+id/sbBottom","@+id/tvRegion",
        "@+id/btnRegion","@+id/btnMenuAlan","@+id/cbSpeaker"}
ids={node.get(ns+"id") for node in hidden.iter()}
if not legacy.issubset(ids):raise RuntimeError("Legacy binding IDs lost")

ET.indent(tree,space="    ")
tree.write(res,encoding="utf-8",xml_declaration=True)
ET.parse(res)

s=main.read_text(encoding="utf-8")
old='"Ekran alanı", "Yazı ve görünüm"'
if s.count(old)!=1:raise RuntimeError("MainActivity settings list changed")
main.write_text(s.replace(old,'"Otomatik OCR alanları", "Yazı ve görünüm"',1),
    encoding="utf-8")
v=build.read_text(encoding="utf-8")
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
            r'\g<1>versionCode = 20261205',v,count=1)
if n!=1:raise RuntimeError("versionCode missing")
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-3.2-GT-AutoRegions"',v,count=1)
if n!=1:raise RuntimeError("versionName missing")
build.write_text(v,encoding="utf-8")
print("GameLingoPro 3.2 GT automatic area settings installed; old view IDs retained but hidden")
