#!/usr/bin/env python3
"""GameLingoPro GT-only renderer 3.0.1: one display layer with working user settings.
Run after the v3.0 GT exact renderer source patch. The old Overlay is not instantiated.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
exact=src/"GtExactOverlay.kt"
prefs=src/"Prefs.kt"
build=root/"app/build.gradle.kts"
tests=root/"app/src/test/java/com/example/altyazi"
for path in (exact,prefs,build):
    if not path.is_file():raise RuntimeError("Missing original GameLingoPro source: "+str(path))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Not the original GameLingoPro application")

def once(text,old,new,name):
    n=text.count(old)
    if n!=1:raise RuntimeError(f"{name} expected exactly 1 anchor, got {n}: {old[:75]}")
    return text.replace(old,new,1)

def between(text,a,b,new,name):
    first=text.find(a)
    second=text.find(b,first+len(a)) if first>=0 else -1
    if first<0 or second<0:raise RuntimeError(f"{name} section boundary changed")
    return text[:first]+new+text[second:]

contract=r'''package com.example.altyazi

/** Pure Kotlin GT renderer sizes/alpha, testable without Android. */
internal object GtStyleContract {
    fun captionSp(chosen:Float):Float=chosen.coerceIn(12f,34f)
    fun hudSp(chosen:Float):Float=(chosen*.76f).coerceIn(11f,28f)
    fun subtitleAlpha(chosen:Int):Int=chosen.coerceIn(0,255)
    fun hudAlpha(chosen:Int):Int=if(chosen<=0)0 else
        maxOf(chosen.coerceAtMost(255),222)
}
'''
(src/"GtStyleContract.kt").write_text(contract,encoding="utf-8")
s=exact.read_text(encoding="utf-8")
s=once(s,"""    @Volatile private var style = Overlay.Stil()
    private val pink""","""    @Volatile private var style = Overlay.Stil()
    private var lastSubtitleValue: String? = null
    private var lastSubtitleTop: Int = 0
    private var lastSubtitleBottom: Int = -1
    private val pink""","renderer state")
s=once(s,"""        root?.post {
            caption?.let(::subtitleStyle)
            boxes.forEach(::hudStyle)
        }""","""        root?.post {
            caption?.let(::subtitleStyle)
            boxes.forEach(::hudStyle)
            if (!lastSubtitleValue.isNullOrBlank())
                setSubtitle(lastSubtitleValue,lastSubtitleTop,bottomPx=lastSubtitleBottom)
        }""","live refresh")
s=between(s,
    "    private fun shape(alpha:Int,radius:Int):GradientDrawable",
    "    private fun speakerColor(text:String):CharSequence",
    '''    private fun shape(alpha:Int,radius:Int):GradientDrawable = GradientDrawable().apply {
        cornerRadius=dp(radius).toFloat()
        setColor(Color.argb(alpha.coerceIn(0,255),
            Color.red(style.arkaRenk),Color.green(style.arkaRenk),
            Color.blue(style.arkaRenk)))
    }
''',"background color")
s=between(s,
    "    private fun subtitleStyle(tv:TextView)",
    "    private fun hudStyle(tv:TextView)",
    '''    private fun subtitleStyle(tv:TextView) {
        // Native GameTranslator look. No second/legacy yellow overlay.
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP,GtStyleContract.captionSp(style.boyutSp))
        tv.setTextColor(style.yaziRengi)
        tv.typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL)
        tv.gravity=Gravity.CENTER
        tv.setLineSpacing(0f,1.14f)
        tv.setPadding(dp(12),dp(5),dp(12),dp(5))
        tv.maxLines=Int.MAX_VALUE
        tv.ellipsize=null
        tv.background=shape(GtStyleContract.subtitleAlpha(style.arkaAlfa),10)
        if(style.kenarlik)
            tv.setShadowLayer(dp(1).toFloat(),0f,dp(1).toFloat(),Color.BLACK)
        else tv.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
    }
''',"subtitle style")
s=between(s,
    "    private fun hudStyle(tv:TextView)",
    "    fun show()",
    '''    private fun hudStyle(tv:TextView) {
        // The same GT renderer and chosen colors/background for all HUD areas.
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP,GtStyleContract.hudSp(style.boyutSp))
        tv.setTextColor(style.yaziRengi)
        tv.typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL)
        tv.gravity=Gravity.CENTER_VERTICAL or Gravity.START
        tv.setLineSpacing(0f,1.13f)
        tv.setPadding(dp(6),dp(3),dp(6),dp(3))
        tv.maxLines=Int.MAX_VALUE
        tv.ellipsize=null
        tv.background=shape(GtStyleContract.hudAlpha(style.arkaAlfa),6)
        if(style.kenarlik)
            tv.setShadowLayer(dp(1).toFloat(),0f,dp(1).toFloat(),Color.BLACK)
        else tv.setShadowLayer(0f,0f,0f,Color.TRANSPARENT)
    }
''',"HUD style")
s=once(s,
    """        val target=caption?:return
        target.post {
            if(value.isNullOrBlank())""",
    """        lastSubtitleValue=value
        lastSubtitleTop=topPx
        lastSubtitleBottom=bottomPx
        val target=caption?:return
        target.post {
            if(value.isNullOrBlank())""","reposition after settings")
s=once(s,
    """            val maxW=(w*.78f).toInt().coerceAtLeast(dp(210))""",
    """            val maxW=(w*.82f).toInt().coerceAtLeast(dp(210))""","text width")
s=once(s,
    """            lp.leftMargin=dp(8);lp.rightMargin=dp(8)""",
    """            val sideMargin=maxOf(dp(8),(w*style.kenarPayYuzde/100f).toInt())
            lp.leftMargin=sideMargin;lp.rightMargin=sideMargin""","display side margins")
s=once(s,
    """        root=null;caption=null;boxes.clear()""",
    """        root=null;caption=null;boxes.clear()
        lastSubtitleValue=null""","cleanup")
exact.write_text(s,encoding="utf-8")

# Keep existing saved user choices. The earlier exact patch silently reset
# yellow/28sp to white/16sp on first run; that was the reported regression.
p=prefs.read_text(encoding="utf-8")
start='''    init {
        if (!sp.getBoolean("gtExactRendererV30Reset", false)) {'''
end='''    var apiKey: String'''
first=p.find(start);last=p.find(end,first+len(start)) if first>=0 else -1
if first<0 or last<0:raise RuntimeError("GT v3.0 preference reset not found")
p=p[:first]+p[last:]
prefs.write_text(p,encoding="utf-8")

# Existing old Overlay class is retained only to supply the Stil/Label data
# contracts, not to draw anything. Runtime uses GtExactOverlay exclusively.
cap=(src/"CaptureService.kt").read_text(encoding="utf-8")
if cap.count("overlay = GtExactOverlay(this)")!=1 or "overlay = Overlay(this)" in cap:
    raise RuntimeError("Detected legacy renderer instance")

testFile=tests/"GtExactOverlayTest.kt"
t=testFile.read_text(encoding="utf-8")
t=t.replace('assertTrue(code.contains("shape(184,10)"))',
            'assertTrue(code.contains("GtStyleContract.subtitleAlpha(style.arkaAlfa)"))')
t=t.replace('assertTrue(code.contains("shape(247,6)"))',
            'assertTrue(code.contains("GtStyleContract.hudAlpha(style.arkaAlfa)"))')
t=t.replace('fun firstRunResetsOldYellowAndLargeText()', 'fun userSelectionsArePreserved()')
t=t.replace('assertTrue(prefs.contains("gtExactRendererV30Reset"))',
            'assertFalse(prefs.contains("gtExactRendererV30Reset"))')
testFile.write_text(t,encoding="utf-8")
tests.mkdir(parents=True,exist_ok=True)
(tests/"GtStyleContractTest.kt").write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtStyleContractTest {
 @Test fun chosenSizeIsNotOverridden() {
   assertEquals(28f,GtStyleContract.captionSp(28f),.001f)
   assertEquals(16f,GtStyleContract.captionSp(16f),.001f)
   assertTrue(GtStyleContract.hudSp(28f)>GtStyleContract.hudSp(16f))
 }
 @Test fun backgroundModesRemainDistinct() {
   assertEquals(0,GtStyleContract.subtitleAlpha(0))
   assertEquals(190,GtStyleContract.subtitleAlpha(190))
   assertEquals(255,GtStyleContract.subtitleAlpha(255))
   assertEquals(0,GtStyleContract.hudAlpha(0))
   assertEquals(255,GtStyleContract.hudAlpha(255))
   assertTrue(GtStyleContract.hudAlpha(190)<255)
 }
 @Test fun originalOverlayCannotBeCreated() {
   val cap=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
   assertTrue(cap.contains("overlay = GtExactOverlay(this)"))
   assertFalse(cap.contains("overlay = Overlay(this)"))
 }
 @Test fun selectedColorAndSizeActuallyReachRuntime() {
   val exact=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
   assertTrue(exact.contains("tv.setTextColor(style.yaziRengi)"))
   assertTrue(exact.contains("GtStyleContract.captionSp(style.boyutSp)"))
   assertTrue(exact.contains("GtStyleContract.hudSp(style.boyutSp)"))
   assertFalse(exact.contains("chosen=style.boyutSp.coerceIn(12f,26f)"))
 }
}
''',encoding="utf-8")

b=build.read_text(encoding="utf-8")
b,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
            r'\g<1>versionCode = 20261203',b,count=1)
if n!=1:raise RuntimeError("No versionCode")
b,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
            r'\g<1>versionName = "GameLingoPro-3.0.1-GT-Only"',b,count=1)
if n!=1:raise RuntimeError("No versionName")
build.write_text(b,encoding="utf-8")
print("GameLingoPro GT-only: original user color/size/background choices now reach the single active renderer")
