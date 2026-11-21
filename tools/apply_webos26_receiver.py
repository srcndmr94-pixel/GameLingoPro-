#!/usr/bin/env python3
"""Prepare real GameLingoPro Android for phone-hosted webOS26 browser receiver.
Execute AFTER all prior GT-only source patches, preserving native app identity.
"""
from pathlib import Path
import re,json,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
source=root/"tools/webos26_receiver.html"
phone=root/"app/src/main/java/com/example/altyazi/PhoneBridge.kt"
web=root/"webos/index.html"
info=root/"webos/appinfo.json"
build=root/"app/build.gradle.kts"
for f in (source,phone,web,info,build):
    if not f.is_file():raise RuntimeError("Missing original source: "+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Refusing unrelated Android application")
html=source.read_text(encoding="utf8")
assert "id=\"hud\"" in html and "id=\"sub\"" in html
asset=root/"app/src/main/assets/gamelingopro_webos26.html"
asset.parent.mkdir(parents=True,exist_ok=True)
asset.write_text(html,encoding="utf8")
web.write_text(html,encoding="utf8")
s=phone.read_text(encoding="utf8")
needle='                                val path = request.split(\' \').getOrNull(1) ?: ""'
if s.count(needle)!=1:raise RuntimeError("HTTP router anchor missing")
inject=r'''
                                // webOS26: phone-hosted browser receiver, no IPK for initial test.
                                if (path == "/" || path.startsWith("/index.html")) {
                                    val page = assets.open("gamelingopro_webos26.html")
                                        .bufferedReader(Charsets.UTF_8).use { it.readText() }
                                    val payload = page.toByteArray(Charsets.UTF_8)
                                    val hdr = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n" +
                                        "Cache-Control: no-store\r\nContent-Length: " + payload.size +
                                        "\r\nConnection: close\r\n\r\n"
                                    socket.getOutputStream().write(
                                        hdr.toByteArray(Charsets.UTF_8) + payload)
                                    socket.getOutputStream().flush()
                                    return@use
                                }
'''
phone.write_text(s.replace(needle,needle+inject,1),encoding="utf8")
obj=json.loads(info.read_text(encoding="utf8"))
obj["version"]="1.2.0";obj["title"]="GameLingoPro · webOS 26"
info.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
s=build.read_text(encoding="utf8")
s,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261204',s,count=1)
assert n==1
s,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',r'\g<1>versionName = "GameLingoPro-3.1-webOS26-Ready"',s,count=1)
assert n==1
build.write_text(s,encoding="utf8")
assert 'PhoneBridgeService.publishHud' in (root/"app/src/main/java/com/example/altyazi/CaptureService.kt").read_text()
print("GameLingoPro Android GT-only webOS26 browser receiver prepared")
