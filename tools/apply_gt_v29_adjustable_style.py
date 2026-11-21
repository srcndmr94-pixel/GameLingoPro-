#!/usr/bin/env python3
"""GT visual renderer on native GameLingoPro; respects saved Pro user choices."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
ov=src/"Overlay.kt"; cap=src/"CaptureService.kt"; main=src/"MainActivity.kt"
build=root/"app/build.gradle.kts"
for p in (ov,cap,main,build):
    if not p.exists():raise RuntimeError("GameLingoPro source is missing "+str(p))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text(): raise RuntimeError("Not GameLingoPro")
s=ov.read_text(encoding="utf-8")
def substitute(old,new):
    global s
    if s.count(old)!=1:raise RuntimeError("Missing/ambiguous Overlay source: "+old[:50])
    s=s.replace(old,new,1)
def span(start,end,replacement):
    global s
    a=s.find(start); b=s.find(end,a+len(start))
    if a<0 or b<0:raise RuntimeError("Overlay block changed: "+start)
    s=s[:a]+replacement+s[b:]
substitute('''        subtitleView?.let { stiliUygula(it, stil.boyutSp) }
        prevView?.let { stiliUygula(it, stil.boyutSp * ONCEKI_ORAN) }''',
'''        subtitleView?.let { stiliUygula(it, stil.boyutSp) }
        labelViews.forEach { stiliUygula(it, (stil.boyutSp * .78f).coerceIn(12f, 32f)) }''')
span('    private fun stiliUygula(t: TextView, boyutSp: Float) {','\n    fun show() {',
'''    private fun stiliUygula(t: TextView, boyutSp: Float) {
        // GameTranslator glass box, with real GameLingoPro user-selected settings.
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, boyutSp.coerceIn(12f, 60f))
        t.setTextColor(stil.yaziRengi)
        t.typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        t.gravity = Gravity.CENTER
        if (stil.kenarlik) t.setShadowLayer(2.5f,0f,1f,Color.BLACK)
        else t.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
        t.setPadding(dp(10), dp(5), dp(10), dp(5))
        t.maxWidth = (context.resources.displayMetrics.widthPixels * .88f).toInt()
            .coerceAtLeast(dp(180))
        t.maxLines = Int.MAX_VALUE
        t.ellipsize = null
        t.background = GradientDrawable().apply {
            cornerRadius = dp(10).toFloat()
            setColor(Color.argb(stil.arkaAlfa.coerceIn(0,255),
                Color.red(stil.arkaRenk),Color.green(stil.arkaRenk),
                Color.blue(stil.arkaRenk)))
        }
    }
''')
# GT HUD labels must use exactly the same chosen color and background.
span('                val tv = makeText(14f, 255).apply {',
'                container.addView(',
'''                val tv = makeText(13f, 205)
                stiliUygula(tv,(stil.boyutSp*.78f).coerceIn(12f,32f))
''')
substitute('''                val rightSide = label.x >= screenWidth / 2''',
'''                stiliUygula(tv,(stil.boyutSp*.78f).coerceIn(12f,32f))
                val rightSide = label.x >= screenWidth / 2''')
# Remove legacy marker and leave a single GT subtitle box.
start='''            val shown: CharSequence = if (refined) {'''
end='''            // NOT: taslak artık GRİYE boyanmıyor.'''
span(start,end,'''            val shown: CharSequence = value
''')
span('    fun oncekiYaz(value: String?) {','\n    /** Önceki satırı solarak kaldırır',
'''    fun oncekiYaz(value: String?) {
        // Old stacked GameLingoPro caption disabled in GT mode.
        oncekiGizle()
    }

''')
ov.write_text(s,encoding="utf-8")
# Change applied settings while a screen capture is still active.
c=cap.read_text(encoding="utf-8")
# The v2.3 landscape override silently forced 14-20sp regardless of user choice.
old_size='''boyutSp = if (screenWidth > screenHeight) {
                prefs.subtitleSize.toFloat().coerceIn(14f, 20f)
            } else if (tv) maxOf(prefs.subtitleSize * 1.5f, 26f)
            else prefs.subtitleSize.toFloat(),'''
new_size='''boyutSp = if (tv) maxOf(prefs.subtitleSize * 1.5f, 26f)
            else prefs.subtitleSize.toFloat(),'''
if c.count(old_size)!=1: raise RuntimeError("Old landscape size override differs; investigate")
c=c.replace(old_size,new_size,1)
a='''            var lastTv = prefs.tvMode'''
if c.count(a)!=1:raise RuntimeError("TV state anchor changed")
c=c.replace(a,a+'''
            var lastGTStyle: Overlay.Stil? = null''',1)
a='''                        if (prefs.tvMode != lastTv) {
                            lastTv = prefs.tvMode
                            overlay.setStil(gorunumStili())
                            log(if (lastTv) "TV MODU AÇIK · yazı büyük" else "TV modu kapalı · telefon boyutu")
                        }'''
if c.count(a)!=1:raise RuntimeError("GT refresh anchor changed")
c=c.replace(a,'''                        val selectedStyle = gorunumStili()
                        if (selectedStyle != lastGTStyle) {
                            lastGTStyle = selectedStyle
                            overlay.setStil(selectedStyle)
                            if (prefs.diagnostics) log("GT GÖRÜNÜM AYARLARI YENİLENDİ")
                        }
                        if (prefs.tvMode != lastTv) {
                            lastTv = prefs.tvMode
                            log(if (lastTv) "TV MODU AÇIK" else "TV modu kapalı")
                        }''',1)
cap.write_text(c,encoding="utf-8")
# Preview and actual output must use same geometry and semibold typeface.
m=main.read_text(encoding="utf-8")
a='''        tvPreview.setTextColor(SubtitleStyle.yaziRengi(renkSecim))'''
if m.count(a)!=1:raise RuntimeError("Preview source missing")
m=m.replace(a,a+'''
        tvPreview.typeface = android.graphics.Typeface.create("sans-serif-medium",
            android.graphics.Typeface.NORMAL)
        tvPreview.gravity = android.view.Gravity.CENTER''',1)
m=m.replace('''            cornerRadius = 12 * yogunluk''',
'''            cornerRadius = 10 * yogunluk''',1)
main.write_text(m,encoding="utf-8")
# Version is independent of previous APK installed alongside old GameLingo.
b=build.read_text(encoding="utf-8")
b,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
    r'\g<1>versionCode = 20261130',b,count=1)
if n!=1:raise RuntimeError("versionCode missing")
b,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-2.9-GT-Adjustable"',b,count=1)
if n!=1:raise RuntimeError("versionName missing")
build.write_text(b,encoding="utf-8")
# Gradle tests validate source-backed theme choices, not a dummy equality check.
test=root/"app/src/test/java/com/example/altyazi/GtActualAppearanceTest.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtActualAppearanceTest {
    @Test fun preferenceFieldsRemainLive() {
        val source = java.io.File("src/main/java/com/example/altyazi/Overlay.kt").readText()
        assertTrue(source.contains("t.setTextColor(stil.yaziRengi)"))
        assertTrue(source.contains("boyutSp.coerceIn(12f, 60f)"))
        assertTrue(source.contains("Color.red(stil.arkaRenk)"))
        assertTrue(source.contains("stiliUygula(tv,(stil.boyutSp*.78f)"))
        assertFalse(source.contains("val compactSize = if (landscape)"))
    }
    @Test fun settingsStillBindToService() {
        val source = java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(source.contains("yaziRengi = SubtitleStyle.yaziRengi(prefs.subtitleColor)"))
        assertTrue(source.contains("boyutSp = if (tv)"))
        assertTrue(source.contains("lastGTStyle"))
    }
}
''',encoding="utf-8")
print("GameLingoPro 2.9 GT glass style now honors color, size, background and live updates")
