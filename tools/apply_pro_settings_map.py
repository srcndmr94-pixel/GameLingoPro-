from pathlib import Path
import xml.etree.ElementTree as ET

root=Path("app/src/main")
layout=root/"res/layout/activity_main.xml"
main=root/"java/com/example/altyazi/MainActivity.kt"
ns="{http://schemas.android.com/apk/res/android}"
ET.register_namespace("android","http://schemas.android.com/apk/res/android")
ET.register_namespace("app","http://schemas.android.com/apk/res-auto")
tree=ET.parse(layout)
menu=next((e for e in tree.getroot().iter() if e.get(ns+"id")=="@+id/ayarMenu"),None)
if menu is None:raise SystemExit("Missing settings menu")
box=next((e for e in menu if e.tag=="LinearLayout"),None)
if box is None:raise SystemExit("Missing menu content")
rows={}
for e in box:
    id=e.get(ns+"id","")
    if id.startswith("@+id/ayarSatir"):
        rows[int(id.removeprefix("@+id/ayarSatir"))]=e
if set(rows)!=set(range(1,9)):raise SystemExit("Settings IDs changed")
for e in list(box):box.remove(e)
def item(tag,attrs,par=box):
    e=ET.SubElement(par,tag)
    for k,v in attrs.items():e.set(ns+k,v)
    return e
def header(t):
    item("TextView",dict(layout_width="match_parent",layout_height="wrap_content",
        layout_marginTop="14dp",layout_marginBottom="6dp",text=t,
        textColor="#2DE6DB",textSize="12sp",textStyle="bold",letterSpacing="0.1"))
def divider():
    item("View",dict(layout_width="match_parent",layout_height="1dp",background="#26324C"))
def shortcut(id,t,d):
    r=item("LinearLayout",dict(id="@+id/"+id,layout_width="match_parent",
        layout_height="wrap_content",minHeight="64dp",orientation="vertical",
        paddingTop="12dp",paddingBottom="12dp",clickable="true",
        focusable="true",background="@drawable/tv_odak"))
    item("TextView",dict(layout_width="match_parent",layout_height="wrap_content",
        text=t,textSize="16sp",textStyle="bold"),r)
    item("TextView",dict(layout_width="match_parent",layout_height="wrap_content",
        text=d,textColor="#91A1B8",textSize="12sp"),r)
titles={1:"Altyazı bölgesi",2:"Yazı boyutu, rengi ve konumu",
    3:"Dil ve çeviri motorları",6:"TV, webOS ve telefon bağlantısı",
    7:"Terim ve özel ayarlar",8:"Günlük ve gelişmiş seçenekler"}
groups=[("ÇEVİRİ",[3,7]),("ALTYAZI BÖLGESİ",[1]),
    ("TV'DEKİ GÖRÜNÜM",[2]),("TV BAĞLANTISI",[6]),
    ("GAMELINGO PRO",[4,5,8])]
for group,ids in groups:
    header(group)
    for i,id in enumerate(ids):
        if i:divider()
        r=rows[id]
        if id in titles:
            for e in r.iter():
                if e.tag=="TextView" and e.get(ns+"text") not in (None,"›"):
                    e.set(ns+"text",titles[id]);break
        box.append(r)
    if group=="TV BAĞLANTISI":
        divider();shortcut("ayarTvKurulum","TV kurulum kılavuzu",
            "LG webOS ve Android TV bağlantısı")
        divider();shortcut("ayarEkranPaylas","PS Remote Play · Ekran paylaşımı",
            "Android uygulama seçicisini aç")
    if group=="GAMELINGO PRO":
        divider();shortcut("ayarHakkinda","Hakkında ve günlük",
            "Sürüm bilgisi, hata kaydı")
ET.indent(tree,space="    ")
tree.write(layout,encoding="utf-8",xml_declaration=True)
s=main.read_text(encoding="utf-8")
needle='        findViewById<View>(R.id.btnAyarGeri)?.setOnClickListener { ayarListesineDon() }'
if needle not in s:raise SystemExit("Settings wiring changed")
binding='''        findViewById<View>(R.id.ayarEkranPaylas)?.setOnClickListener {
            findViewById<View>(R.id.btnConsoleSettings)?.performClick()
        }
        findViewById<View>(R.id.ayarTvKurulum)?.setOnClickListener {
            findViewById<View>(R.id.btnTvGuide)?.performClick()
        }
        findViewById<View>(R.id.ayarHakkinda)?.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("GameLingo Pro")
                .setMessage("Android ekran paylaşımı, OCR, çeviri ve TV bağlantısı. PS Remote Play görüntüsünün yakalanması uygulama korumasına bağlıdır.")
                .setPositiveButton("Günlüğü kopyala") { _, _ ->
                    findViewById<View>(R.id.btnCopyLog)?.performClick()
                }
                .setNegativeButton("Kapat", null).show()
        }
'''
main.write_text(s.replace(needle,needle+"\n"+binding,1),encoding="utf-8")
ET.parse(layout)
print("GameTranslator-inspired settings grouping, working shortcuts, existing preferences preserved")
