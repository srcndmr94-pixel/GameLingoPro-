#!/usr/bin/env python3
"""Implement Android screen-sharing / OCR -> left/right mission/HUD webOS
using the genuine GameLingoPro Kotlin project, preserving its engines and UI.

No GameTranslator app sources are substituted. This updates only the native
app's own bridge, overlay geometry, existing PS Remote Play entry, and webOS.
"""
from pathlib import Path
import re
import sys
import json
import xml.etree.ElementTree as ET

root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('.')
app=root/'app/src/main'
src=app/'java/com/example/altyazi'
web=root/'webos/index.html'
bridge=src/'PhoneBridge.kt'
cap=src/'CaptureService.kt'
overlay=src/'Overlay.kt'
main=src/'MainActivity.kt'
for p in [web,bridge,cap,overlay,main,root/'app/build.gradle.kts']:
    if not p.exists():raise SystemExit(f'Not a GameLingoPro source tree: {p}')
if 'applicationId = "com.gamelingo.pro"' not in (root/'app/build.gradle.kts').read_text():
    raise SystemExit('Refusing to change a project other than GameLingoPro')

def patch(p,a,b):
    t=p.read_text(encoding='utf-8')
    if b in t:return
    if a not in t:raise RuntimeError(f'GameLingoPro source mismatch: {p} :: {a[:90]!r}')
    p.write_text(t.replace(a,b,1),encoding='utf-8')

def replace_span(p,start,end,new):
    t=p.read_text(encoding='utf-8')
    a=t.find(start);b=t.find(end,a+len(start))
    if a<0 or b<0:raise RuntimeError(f'Unrecognized layout or method in {p}: {start[:60]}')
    p.write_text(t[:a]+new+t[b:],encoding='utf-8')

# Pure geometry-only helper: needs no external dependencies, used by app and tests.
(src/'ProHudRegion.kt').write_text('''package com.example.altyazi

/** Normalized translated box from GameLingoPro's own OCR. */
internal data class ProHudRegion(
    val id: String, val text: String,
    val x: Double, val y: Double, val right: Double, val side: String
)

internal object ProHudRegions {
    fun convert(labels: List<Overlay.Label>, width: Int, height: Int): List<ProHudRegion> {
        if (width < 1 || height < 1) return emptyList()
        var left = 0
        var right = 0
        return labels.asSequence().filter { it.text.isNotBlank() }
            .sortedWith(compareBy<Overlay.Label> { it.y }.thenBy { it.x })
            .mapNotNull { label ->
                val isRight = label.x >= width / 2
                val slot = if (isRight) right++ else left++
                if (slot >= 7) null else {
                    val side = if (isRight) "right" else "left"
                    val x = (label.x.toDouble() / width).coerceIn(0.0,1.0)
                    val y = (label.y.toDouble() / height).coerceIn(0.0,1.0)
                    val last = ((label.rightX ?: label.x).toDouble() / width).coerceIn(x,1.0)
                    ProHudRegion("hud_${side}_${slot}",label.text.trim().take(400),x,y,last,side)
                }
            }.toList()
    }
}
''',encoding='utf-8')

# 1. Keep original PhoneBridgeService and 4-digit PIN / HTTP port / PC protocol.
patch(bridge,'import java.util.concurrent.atomic.AtomicInteger',
      'import java.util.concurrent.atomic.AtomicInteger\nimport org.json.JSONObject\nimport org.json.JSONArray')
patch(bridge,'        @Volatile var subtitleTime: Long = 0L', '''        @Volatile var subtitleTime: Long = 0L
        @Volatile private var hudRegions: List<ProHudRegion> = emptyList()
        @Volatile private var hudTime: Long = 0L
        /** Updated by the existing GameLingoPro OCR pipeline; not a new translation engine. */
        fun publishHud(labels: List<Overlay.Label>, width: Int, height: Int) {
            hudRegions = ProHudRegions.convert(labels,width,height)
            hudTime = System.currentTimeMillis()
        }
        fun clearHud() { hudRegions = emptyList(); hudTime = System.currentTimeMillis() }
        private fun hudJson(now: Long): JSONArray {
            val array = JSONArray()
            if (now - hudTime >= 8_000L) return array
            hudRegions.forEach { item ->
                array.put(JSONObject().put("id",item.id).put("text",item.text)
                    .put("x",item.x).put("y",item.y).put("right",item.right)
                    .put("side",item.side))
            }
            return array
        }''')
patch(bridge,'                                val json = if (ok) "{\\"subtitle\\":$escaped}" else "{\\"error\\":\\"unauthorized\\"}"', '''                                val json = if (ok) JSONObject().put("subtitle",body)
                                    .put("regions",hudJson(System.currentTimeMillis())).toString()
                                    else "{\\"error\\":\\"unauthorized\\"}"''')
patch(bridge,'        CaptureService.log("TV köprüsü kapandı")',
      '        clearHud()\n        CaptureService.log("GameLingoPro TV köprüsü kapandı")')

# 2. Correct right-edge clamping on the PHONE overlay, preserving existing labels.
patch(overlay,'    data class Label(val text: String, val x: Int, val y: Int)',
      '    data class Label(val text: String, val x: Int, val y: Int, val rightX: Int? = null)')
patch(overlay,'''                val lp = tv.layoutParams as FrameLayout.LayoutParams
                lp.leftMargin = label.x.coerceAtLeast(0)
                lp.topMargin = label.y.coerceAtLeast(0)
                tv.layoutParams = lp
                tv.text = label.text
                tv.visibility = View.VISIBLE''','''                val screenWidth = container.width.takeIf { it > 0 } ?: context.resources.displayMetrics.widthPixels
                val screenHeight = container.height.takeIf { it > 0 } ?: context.resources.displayMetrics.heightPixels
                val margin = dp(8)
                val maximum = (screenWidth * .47f).toInt().coerceAtLeast(dp(110))
                tv.maxWidth = maximum
                tv.text = label.text
                tv.measure(View.MeasureSpec.makeMeasureSpec(maximum, View.MeasureSpec.AT_MOST),
                    View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                val width = tv.measuredWidth.coerceAtLeast(dp(36))
                val height = tv.measuredHeight.coerceAtLeast(dp(24))
                val rightSide = label.x >= screenWidth / 2
                val desiredX = if (rightSide) (label.rightX ?: label.x) - width else label.x
                val lp = tv.layoutParams as FrameLayout.LayoutParams
                lp.leftMargin = desiredX.coerceIn(margin, (screenWidth - width - margin).coerceAtLeast(margin))
                lp.topMargin = label.y.coerceIn(margin, (screenHeight - height - margin).coerceAtLeast(margin))
                lp.rightMargin = 0
                tv.layoutParams = lp
                tv.visibility = View.VISIBLE''')

# 3. Existing menu/side OCR -> PHONE and webOS. Keep unchanged subtitle pipeline.
patch(cap,'    private var lastMenuKey = ""','''    private var lastMenuKey = ""
    private var lastHudLabels: List<Overlay.Label> = emptyList()''')
patch(cap,'if (!isTv && prefs.menuTranslate && cycle % MENU_EVERY == 0L',
      'if (!isTv && (prefs.menuTranslate || PhoneBridgeService.running) && cycle % MENU_EVERY == 0L')
patch(cap,'        val found = ArrayList<Triple<String, Int, Int>>()',
      '        val found = ArrayList<Overlay.Label>()')
patch(cap,'                if (!yanYaziAlaninda(relX, relY, subtitleTop)) continue','''                val byPreferences = yanYaziAlaninda(relX, relY, subtitleTop)
                // When the user starts TV sharing, scan mission and HUD edges
                // even if the standalone menu-translation option is disabled.
                val tvSide = PhoneBridgeService.running && relY in .07f..minOf(.88f,subtitleTop) &&
                    (relX <= .43f || relX >= .57f)
                if (!byPreferences && !tvSide) continue''')
patch(cap,'''                val screenY = (box.bottom.toFloat() / small.height * screenHeight).toInt()
                found.add(Triple(raw, screenX, screenY))''','''                val screenY = (box.top.toFloat() / small.height * screenHeight).toInt()
                val right = (box.right.toFloat() / small.width * screenWidth).toInt()
                found.add(Overlay.Label(raw, screenX, screenY, right))''')
patch(cap,'        val key = found.joinToString("|") { it.first }\n        if (key == lastMenuKey) return','''        val key = found.joinToString("|") {
            "${it.text}:${it.x / 20}:${it.y / 20}:${(it.rightX ?: it.x) / 20}"
        }
        if (key == lastMenuKey) {
            PhoneBridgeService.publishHud(lastHudLabels, screenWidth, screenHeight)
            return
        }''')
patch(cap,'            overlay.clearLabels()\n            return','''            overlay.clearLabels()
            lastHudLabels = emptyList()
            PhoneBridgeService.clearHud()
            return''')
patch(cap,'''        for ((text, x, y) in found) {
            val translated = translateMenuText(text) ?: continue
            labels.add(Overlay.Label(translated, x, y))''','''        for (item in found) {
            val translated = translateMenuText(item.text) ?: continue
            labels.add(item.copy(text = translated))''')
patch(cap,'        overlay.setLabels(labels)\n    }','''        overlay.setLabels(labels)
        lastHudLabels = labels.toList()
        PhoneBridgeService.publishHud(labels, screenWidth, screenHeight)
    }''')

# 4. Existing Pro UI only: a real screen-sharing dialog + real webOS bridge setup.
# No fake PSN login; continue using user's installed PS Remote Play app if available.
old='''        findViewById<android.view.View>(R.id.btnProWebOs).setOnClickListener {
            TvMode.setManual(this, prefs, true)
            tvSecimiGoster()
            tvKilavuzu()
        }'''
new='''        findViewById<android.view.View>(R.id.btnProWebOs).setOnClickListener {
            val ip = PhoneBridge.localIp()
            val code = PhoneBridgeService.pinFor(this)
            AlertDialog.Builder(this)
                .setTitle("GameLingoPro · webOS bağlantısı")
                .setMessage("Telefon IP: ${if(ip.isBlank()) "Wi-Fi bağlantısı bulunamadı" else ip}\\n" +
                    "Bağlantı kodu: $code\\nPort: 47323\\n\\n" +
                    "LG webOS alıcısına bu bilgileri gir. Telefon ve TV aynı yerel ağda olsun. " +
                    "Sonra Ekranı Paylaş ile istediğin uygulamayı seç. Soldaki görevler ve " +
                    "sağdaki bildirimler ayrı kutularda yayınlanır.")
                .setPositiveButton(if (PhoneBridgeService.running) "Bağlantı açık" else "Altyazı yayınını aç") { _, _ ->
                    if (!PhoneBridgeService.running) {
                        ContextCompat.startForegroundService(this,
                            Intent(this,PhoneBridgeService::class.java).setAction(PhoneBridgeService.ACTION_START))
                    }
                }
                .setNeutralButton("Ekranı paylaş") { _, _ -> save(); start() }
                .setNegativeButton("Kapat",null).show()
        }'''
patch(main,old,new)
old='''        findViewById<android.view.View>(R.id.btnProRemote).setOnClickListener {
            val remotePackage = "com.playstation.remoteplay"
            val launch = packageManager.getLaunchIntentForPackage(remotePackage)
            if (launch != null) {
                try {
                    startActivity(launch)
                } catch (error: Exception) {
                    Toast.makeText(this, "Remote Play açılamadı: ${error.message}", Toast.LENGTH_LONG).show()
                }
            } else {
                AlertDialog.Builder(this)
                    .setTitle("PS Remote Play")
                    .setMessage("PS Remote Play telefonda kurulu değil. Play Store sayfasını açmak ister misin?")
                    .setPositiveButton("Play Store") { _, _ ->
                        val uri = android.net.Uri.parse("market://details?id=$remotePackage")
                        try { startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, uri)) }
                        catch (_: Exception) {
                            startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,
                                android.net.Uri.parse("https://play.google.com/store/apps/details?id=$remotePackage")))
                        }
                    }
                    .setNegativeButton("Vazgeç", null)
                    .show()
            }
        }'''
new='''        findViewById<android.view.View>(R.id.btnProRemote).setOnClickListener {
            val remotePackage = "com.playstation.remoteplay"
            AlertDialog.Builder(this)
                .setTitle("GameLingoPro · PS Remote Play")
                .setItems(arrayOf("Ekranı paylaş · uygulama seç", "PS Remote Play uygulamasını aç")) { _, selected ->
                    if (selected == 0) {
                        save()
                        start() // Android 14+ app-selection MediaProjection dialog
                    } else {
                        val launch = packageManager.getLaunchIntentForPackage(remotePackage)
                        if (launch != null) startActivity(launch)
                        else {
                            val uri = android.net.Uri.parse("market://details?id=$remotePackage")
                            try { startActivity(Intent(Intent.ACTION_VIEW,uri)) }
                            catch (_: Exception) { startActivity(Intent(Intent.ACTION_VIEW,
                                android.net.Uri.parse("https://play.google.com/store/apps/details?id=$remotePackage"))) }
                        }
                    }
                }
                .setNegativeButton("Kapat", null)
                .show()
        }'''
patch(main,old,new)

# 5. Real HDMI-in-app input, not a speculative background system overlay.
# Preserve 4-digit PIN, port 47323 and all existing Pro fonts/colors.
web.write_text('''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameLingoPro · webOS</title>
<style>
:root{--bg:#080d1b;--turquoise:#36eadf;--purple:#9b66ff;--text:#eff7ff}
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font:25px/1.35 Arial,sans-serif}
video#hdmi{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}
#control{position:absolute;z-index:5;top:6%;left:23%;width:54%;padding:36px;border:2px solid #483776;border-radius:24px;background:rgba(12,17,38,.97)}
h1{margin:0 0 15px;color:var(--turquoise);text-shadow:0 0 17px #00c6ce;font-size:37px}
label{display:block;margin-top:16px}input,button,select{width:100%;font:inherit;padding:12px;margin-top:6px;border-radius:12px;border:2px solid #514784;color:var(--text);background:#141b30}
button{background:#0f746d;border-color:var(--turquoise);cursor:pointer}button:focus,input:focus,select:focus{outline:3px solid var(--turquoise)}
#state{color:#c5b7ff;max-width:90%;white-space:pre-line}
#caption{position:absolute;z-index:2;left:50%;bottom:7%;transform:translateX(-50%);max-width:84%;padding:12px 22px;border-radius:12px;background:rgba(7,10,19,.84);color:white;text-align:center;font-size:42px;font-weight:bold;text-shadow:0 2px 5px #000;pointer-events:none;white-space:pre-wrap}
#caption:empty{display:none}#hud{position:absolute;z-index:3;inset:0;overflow:hidden;pointer-events:none}
.hud-card{position:absolute;max-width:43%;min-width:10%;width:max-content;padding:10px 16px;border-radius:13px;border:2px solid rgba(54,234,223,.78);background:rgba(8,12,25,.88);color:#fff;line-height:1.28;font-weight:650;font-size:clamp(18px,2.15vw,34px);text-shadow:0 2px 5px #000;overflow-wrap:anywhere;white-space:pre-wrap}
.hud-card.right{border-color:rgba(166,102,255,.85);text-align:right}
#status{position:absolute;z-index:4;top:1%;left:50%;transform:translateX(-50%);font-size:20px;color:var(--turquoise);background:rgba(4,8,19,.8);border-radius:8px;padding:8px 12px}
[hidden]{display:none!important}
</style></head><body>
<video id="hdmi" autoplay playsinline></video>
<div id="caption"></div><div id="hud"></div><div id="status" hidden></div>
<section id="control"><h1>GameLingoPro · webOS</h1>
<p>Telefon ve webOS aynı Wi-Fi ağında olmalı. GameLingoPro uygulamasında webOS → Altyazı yayınını aç seç.</p>
<label>Telefon IP adresi<input id="ip" placeholder="192.168.1.10" inputmode="decimal"></label>
<label>4 haneli bağlantı kodu<input id="pin" placeholder="4 haneli kod" maxlength="4" inputmode="numeric"></label>
<label>HDMI görüntüsü (LG modeline bağlı)<select id="input"><option value="0">Yalnız altyazı</option><option value="1">HDMI 1</option><option value="2">HDMI 2</option><option value="3">HDMI 3</option><option value="4">HDMI 4</option></select></label>
<button id="connect">Bağlan</button><button id="disconnect">Bağlantıyı kes</button>
<p id="state">Bağlantı bekleniyor</p>
<p style="font-size:18px;opacity:.75">HDMI görüntüsünün webOS uygulaması içinde açılması cihaz desteğine bağlıdır.</p></section>
<script>
(function(){'use strict';
var timer=null,active=null,fail=0,session=0;var hud=new Map();
var ip=document.getElementById('ip'),pin=document.getElementById('pin');
var state=document.getElementById('state'),sub=document.getElementById('caption'),video=document.getElementById('hdmi'),control=document.getElementById('control'),status=document.getElementById('status'),select=document.getElementById('input');
try{ip.value=localStorage.getItem('glp_ip')||'';pin.value=localStorage.getItem('glp_pin')||'';select.value=localStorage.getItem('glp_input')||'0';}catch(e){}
function msg(s){state.textContent=s;status.textContent=s;}
function clearHud(){hud.forEach(function(n){n.remove();});hud.clear();}
function validIp(s){var p=s.split('.');return p.length===4&&p.every(function(v){return /^\\d{1,3}$/.test(v)&&Number(v)<=255;});}
function drawHud(regions){if(!Array.isArray(regions))return;
 var present=new Set();regions.slice(0,14).forEach(function(r){
  if(!r||typeof r.id!=='string'||!/^hud_(left|right)_\\d+$/.test(r.id)||typeof r.text!=='string')return;
  if(![r.x,r.y,r.right].every(function(n){return typeof n==='number'&&isFinite(n);}))return;
  var id=r.id,right=r.side==='right',x=Math.max(.01,Math.min(.97,r.x)),y=Math.max(.01,Math.min(.94,r.y)),end=Math.max(x,Math.min(.98,r.right));
  present.add(id);var n=hud.get(id);if(!n){n=document.createElement('div');document.getElementById('hud').appendChild(n);hud.set(id,n);}
  n.className='hud-card'+(right?' right':'');n.textContent=r.text;n.style.top=(y*100).toFixed(2)+'%';
  if(right){n.style.left='auto';n.style.right=((1-end)*100).toFixed(2)+'%';n.style.maxWidth=Math.max(15,Math.min(43,end*100-2))+'%';}
  else{n.style.right='auto';n.style.left=(x*100).toFixed(2)+'%';n.style.maxWidth=Math.max(15,Math.min(43,98-x*100))+'%';}
 });hud.forEach(function(n,id){if(!present.has(id)){n.remove();hud.delete(id);}});
}
function hdmi(){video.replaceChildren();if(select.value==='0'){video.pause();return;}
 try{var s=document.createElement('source');s.type='service/webos-external';s.src='ext://hdmi:'+select.value;video.appendChild(s);video.load();video.play().catch(function(){msg('HDMI gösterilemiyor; yalnız çeviri kutuları kullanılabilir.');});}
 catch(e){msg('HDMI bu webOS cihazında kullanılamıyor.');}}
function stop(){session++;if(timer){clearTimeout(timer);timer=null;}if(active){active.abort();active=null;}clearHud();sub.textContent='';control.hidden=false;status.hidden=true;video.pause();video.replaceChildren();msg('Bağlantı kesildi');}
function schedule(id,ms){if(id===session)timer=setTimeout(function(){poll(id);},ms);}
function poll(id){if(id!==session)return;var xhr=new XMLHttpRequest();active=xhr;
 xhr.open('GET','http://'+ip.value.trim()+':47323/subtitle?pin='+encodeURIComponent(pin.value.trim())+'&t='+Date.now(),true);xhr.timeout=2200;
 function finish(ok,data){if(id!==session)return;active=null;if(ok){fail=0;if(!control.hidden){control.hidden=true;status.hidden=false;hdmi();}sub.textContent=data.subtitle;drawHud(data.regions);msg('GameLingoPro bağlı');}
 else{fail++;if(fail>=3){clearHud();sub.textContent='';msg('Telefon bağlantısı kesildi · IP, kod ve Wi-Fi kontrol et');}}schedule(id,ok?700:1500);}
 xhr.onload=function(){if(xhr.status===200){try{var d=JSON.parse(xhr.responseText);if(typeof d.subtitle!=='string')throw Error();finish(true,d);}catch(e){finish(false,{});}}
 else if(xhr.status===403){stop();msg('Bağlantı kodu geçersiz');}
 else finish(false,{});};xhr.onerror=function(){finish(false,{})};xhr.ontimeout=function(){finish(false,{})};
 try{xhr.send()}catch(e){finish(false,{})}}
document.getElementById('connect').onclick=function(){stop();if(!validIp(ip.value.trim())||!/^\\d{4}$/.test(pin.value.trim())){msg('Geçerli IP ve 4 haneli kod gir');return;}
 try{localStorage.setItem('glp_ip',ip.value.trim());localStorage.setItem('glp_pin',pin.value.trim());localStorage.setItem('glp_input',select.value)}catch(e){}
 fail=0;msg('Bağlanıyor…');poll(session)};
document.getElementById('disconnect').onclick=stop;
document.addEventListener('keydown',function(e){if(e.keyCode===461||e.key==='Escape'){if(control.hidden){e.preventDefault();stop();}else if(window.webOS&&webOS.platformBack)webOS.platformBack();}});
})();
</script></body></html>
''',encoding='utf-8')
# Bump only the independently installed GameLingoPro build.
build=root/'app/build.gradle.kts'
b=build.read_text(encoding='utf-8')
b=re.sub(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261121',b,count=1)
b=re.sub(r'(?m)^(\s*)versionName\s*=\s*\"[^\"]+\"',r'\g<1>versionName = \"GameLingoPro-2.0-HUD\"',b,count=1)
b=b.replace('\\"','\"')
build.write_text(b,encoding='utf-8')
webinfo=root/'webos/appinfo.json'
info=json.loads(webinfo.read_text(encoding='utf-8'))
info['title']='GameLingoPro · webOS';info['version']='1.1.0'
webinfo.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
ET.parse(app/'AndroidManifest.xml')
assert 'applicationId = "com.gamelingo.pro"' in (root/'app/build.gradle.kts').read_text()
assert 'com.gamelingo.pro.webos' in (root/'webos/appinfo.json').read_text()
print('GameLingoPro original Kotlin/Android translation preserved, native side HUD/webOS and screen share integrated')