from pathlib import Path
import xml.etree.ElementTree as ET
root=Path("app/src/main")
layout=root/"res/layout/activity_main.xml"
text=layout.read_text()
# Distinct Pro brand; keep existing IDs and functional widgets intact.
text=text.replace('android:text="Game"','android:text="GameLingo"').replace('android:text="Lingo"','android:text=" PRO"')
text=text.replace('android:text="Oyunları kendi dilinde yaşa"','android:text="GAME • TRANSLATE • CONNECT"')
text=text.replace('android:background="@drawable/bg_logo"','android:background="@drawable/pro_neon_logo"')
text=text.replace('android:background="@drawable/bg_seg_track"','android:background="@drawable/pro_neon_panel"')
text=text.replace('android:background="@drawable/bg_seg_on"','android:background="@drawable/pro_neon_selected"')
text=text.replace('android:background="@drawable/bg_seg_off"','android:background="@drawable/pro_neon_panel"')
# Pro navigation row: informational only; do not misrepresent it as HDMI integration.
marker='        <!-- ======================= TELEFON / TV ======================= -->'
extra='''        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginStart="16dp"
            android:layout_marginTop="14dp"
            android:layout_marginEnd="16dp"
            android:background="@drawable/pro_neon_panel"
            android:orientation="vertical"
            android:padding="14dp">
            <TextView
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:text="GAMELINGO PRO  •  BAĞLANTI MERKEZİ"
                android:textColor="#D878FF"
                android:textStyle="bold"
                android:letterSpacing="0.10"
                android:textSize="13sp"/>
            <TextView
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:layout_marginTop="8dp"
                android:text="TELEFON  •  TV  •  webOS  •  PS REMOTE PLAY"
                android:textColor="#E6F5FF"
                android:textSize="13sp"/>
            <TextView
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:layout_marginTop="5dp"
                android:text="webOS ve Remote Play bağlantıları cihaz desteğine bağlıdır."
                android:textColor="#A3A9C4"
                android:textSize="11sp"/>
        </LinearLayout>
'''
if marker not in text: raise SystemExit("Layout marker missing")
text=text.replace(marker,extra+marker)
layout.write_text(text)
draw=root/"res/drawable"
draw.mkdir(exist_ok=True)
for name,stroke,fill in [
 ("pro_neon_logo","#31E6EC","#101A33"),
 ("pro_neon_panel","#9E52FF","#10182B"),
 ("pro_neon_selected","#2DE6DB","#14314A")]:
 (draw/(name+".xml")).write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
 <solid android:color="{fill}"/>
 <corners android:radius="20dp"/>
 <stroke android:width="2dp" android:color="{stroke}"/>
 <padding android:left="8dp" android:right="8dp" android:top="6dp" android:bottom="6dp"/>
</shape>''')
build=Path("app/build.gradle.kts")
b=build.read_text().replace('versionName = "10.60-pro-preview"','versionName = "GameLingoPro-1.0"')
build.write_text(b)
ET.parse(layout)
for p in draw.glob("pro_neon_*.xml"): ET.parse(p)
print("Pro layout + resources validated")
