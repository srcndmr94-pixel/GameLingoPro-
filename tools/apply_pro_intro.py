#!/usr/bin/env python3
"""Install GameLingoPro animated neon launch screen; no NDK, assets or external dependencies."""
from pathlib import Path
from xml.etree import ElementTree as ET
import math, struct, wave
root=Path("app/src/main")
manifest=root/"AndroidManifest.xml"
java=root/"java/com/example/altyazi"
raw=root/"res/raw"
main=java/"MainActivity.kt"
if not all(x.is_file() for x in [manifest,main,Path("app/build.gradle.kts")]):
    raise SystemExit("Missing Android source; cannot install intro")
raw.mkdir(parents=True,exist_ok=True)

# Original 5-second electronic introduction, synthesized at build time.
rate=22050
notes=[(0.,554.37),(.48,659.25),(.96,830.61),(1.44,1108.73),
       (2.03,830.61),(2.62,659.25),(3.18,987.77),(3.80,1108.73)]
samples=bytearray()
for i in range(rate*5):
    t=i/rate
    v=0.
    for at,freq in notes:
        dt=t-at
        if 0<=dt<1.20:
            env=(1-math.exp(-dt*35))*math.exp(-dt*3.8)
            v+=.16*env*(math.sin(2*math.pi*freq*dt)+.25*math.sin(4*math.pi*freq*dt))
    fade=max(0,min(1,t/.4,(5-t)/.65))
    v+=.023*fade*math.sin(2*math.pi*138.59*t)
    samples+=struct.pack("<h",int(max(-1,min(1,v))*32767))
with wave.open(str(raw/"pro_intro_theme.wav"),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(samples)

intro=r'''package com.example.altyazi

import android.app.Activity
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.LinearGradient
import android.graphics.Shader
import android.media.MediaPlayer
import android.os.Bundle
import android.os.SystemClock
import android.view.Gravity
import android.view.View
import android.view.MotionEvent
import android.widget.FrameLayout
import android.widget.TextView
import android.graphics.Typeface
import java.util.concurrent.atomic.AtomicBoolean

/** Original neon motion sequence for GameLingo Pro. Skippable, optional music, offline. */
class ProIntroActivity : Activity() {
    private val ended=AtomicBoolean(false)
    private var music:MediaPlayer?=null
    private var clicks:ProClickFeedback?=null
    private val durationMs=5000L
    private val preferences by lazy { getSharedPreferences("gamelingo_pro_intro",MODE_PRIVATE) }
    private val finishIntro=Runnable { enterApplication() }

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        clicks=ProClickFeedback(this)
        window.decorView.systemUiVisibility=(View.SYSTEM_UI_FLAG_FULLSCREEN or
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
        val root=FrameLayout(this).apply { setBackgroundColor(Color.rgb(2,3,15)) }
        root.addView(Artwork(),FrameLayout.LayoutParams(-1,-1))
        val skip=TextView(this).apply {
            text="ATLA";textSize=13f;setTextColor(Color.WHITE);gravity=Gravity.CENTER
            setBackgroundColor(Color.argb(156,9,22,46))
            setOnClickListener { enterApplication() }
        }
        val sound=TextView(this).apply {
            textSize=20f;setTextColor(Color.WHITE);gravity=Gravity.CENTER
            setBackgroundColor(Color.argb(156,9,22,46))
            text=if(preferences.getBoolean("intro_music",true)) "♫" else "×"
            setOnClickListener {
                val next=!preferences.getBoolean("intro_music",true)
                preferences.edit().putBoolean("intro_music",next).apply()
                text=if(next) "♫" else "×"
                if(next) playAudio() else stopAudio()
            }
        }
        val density=resources.displayMetrics.density
        fun dip(n:Float)=(n*density).toInt()
        root.addView(skip,FrameLayout.LayoutParams(dip(68f),dip(40f),Gravity.TOP or Gravity.END).apply {
            setMargins(0,dip(40f),dip(18f),0)
        })
        root.addView(sound,FrameLayout.LayoutParams(dip(40f),dip(40f),Gravity.TOP or Gravity.START).apply {
            setMargins(dip(18f),dip(40f),0,0)
        })
        setContentView(root)
        playAudio()
        window.decorView.postDelayed(finishIntro,durationMs)
    }
    private fun playAudio() {
        if(ended.get() || !preferences.getBoolean("intro_music",true)) return
        stopAudio()
        try {
            music=MediaPlayer.create(this,R.raw.pro_intro_theme)?.apply {
                isLooping=false;setVolume(.55f,.55f);start()
            }
        } catch (_:Exception) { stopAudio() }
    }
    private fun stopAudio() {
        try {music?.stop()} catch (_:Exception) {}
        try {music?.release()} catch (_:Exception) {}
        music=null
    }
    private fun enterApplication() {
        if(!ended.compareAndSet(false,true)) return
        window.decorView.removeCallbacks(finishIntro)
        stopAudio()
        startActivity(Intent(this,MainActivity::class.java))
        @Suppress("DEPRECATION")
        overridePendingTransition(android.R.anim.fade_in,android.R.anim.fade_out)
        finish()
    }
    override fun dispatchTouchEvent(ev:MotionEvent):Boolean {
        val consumed=super.dispatchTouchEvent(ev)
        if(consumed) clicks?.onTouch(ev)
        return consumed
    }
    override fun onPause() {stopAudio();super.onPause()}
    override fun onDestroy() {
        window.decorView.removeCallbacks(finishIntro)
        clicks?.release();stopAudio();super.onDestroy()
    }
    private inner class Artwork:View(this@ProIntroActivity) {
        private val began=SystemClock.uptimeMillis()
        private val p=Paint(Paint.ANTI_ALIAS_FLAG)
        private val turquoise=Color.rgb(6,231,244)
        private val violet=Color.rgb(182,54,252)
        init {setLayerType(View.LAYER_TYPE_SOFTWARE,null)}
        private fun neon(c:Canvas,path:Path,color:Int,weight:Float) {
            p.reset();p.isAntiAlias=true;p.style=Paint.Style.STROKE
            p.strokeWidth=weight;p.strokeCap=Paint.Cap.ROUND;p.strokeJoin=Paint.Join.ROUND
            p.color=color;p.setShadowLayer(17f,0f,0f,color)
            c.drawPath(path,p);p.clearShadowLayer()
        }
        private fun title(c:Canvas,value:String,x:Float,y:Float,size:Float,color:Int) {
            p.reset();p.isAntiAlias=true;p.color=color;p.textSize=size
            p.typeface=Typeface.DEFAULT_BOLD
            c.drawText(value,x,y,p)
        }
        override fun onDraw(canvas:Canvas) {
            val t=(SystemClock.uptimeMillis()-began).coerceAtLeast(0)
            canvas.drawColor(Color.rgb(2,3,15))
            canvas.save()
            canvas.scale(width/360f,height/800f)
            // Two glowing swooshes reproduce the turquoise-violet opening palette.
            neon(canvas,Path().apply {
                moveTo(32f,240f);cubicTo(115f,145f,252f,192f,328f,68f)
            },turquoise,2.7f)
            neon(canvas,Path().apply {
                moveTo(-30f,716f);cubicTo(121f,578f,204f,716f,391f,552f)
            },violet,3.3f)
            neon(canvas,Path().apply {
                moveTo(-24f,690f);cubicTo(123f,640f,202f,710f,383f,592f)
            },turquoise,1.8f)
            val stage=when {t<780->0;t<1770->1;t<2950->2;else->3}
            if(stage>=1) {
                val pad=Path().apply {
                    moveTo(133f,320f);cubicTo(119f,309f,108f,319f,105f,332f)
                    lineTo(96f,372f);cubicTo(92f,389f,107f,402f,121f,394f)
                    lineTo(148f,380f);lineTo(209f,380f);lineTo(239f,394f)
                    cubicTo(255f,402f,269f,386f,264f,370f)
                    lineTo(253f,329f);cubicTo(250f,315f,237f,312f,226f,320f)
                    close()
                }
                neon(canvas,pad,turquoise,5f);neon(canvas,pad,violet,1.5f)
                title(canvas,"+",119f,361f,41f,turquoise)
                for ((x,y) in listOf(218f to 342f,238f to 352f,218f to 368f,201f to 352f)) {
                    p.reset();p.isAntiAlias=true;p.color=turquoise
                    p.setShadowLayer(9f,0f,0f,turquoise)
                    canvas.drawCircle(x,y,3.6f,p)
                }
                val bubble=Path().apply {
                    moveTo(196f,270f);lineTo(258f,270f)
                    quadTo(270f,270f,270f,282f);lineTo(269f,309f)
                    quadTo(269f,320f,258f,320f);lineTo(223f,320f)
                    lineTo(203f,333f);lineTo(205f,317f);lineTo(195f,317f)
                    quadTo(186f,317f,187f,306f);lineTo(190f,280f);close()
                }
                neon(canvas,bubble,violet,4.3f);neon(canvas,bubble,turquoise,1.5f)
                title(canvas,"A 文",196f,307f,25f,Color.WHITE)
            }
            if(stage>=2) {
                title(canvas,"GameLingo",72f,455f,34f,Color.WHITE)
                title(canvas,"Pro",259f,455f,34f,turquoise)
            }
            if(stage==2) {
                p.reset();p.isAntiAlias=true
                p.shader=LinearGradient(91f,0f,267f,0f,turquoise,violet,Shader.TileMode.CLAMP)
                p.setShadowLayer(13f,0f,0f,turquoise)
                canvas.drawRoundRect(90f,515f,270f,526f,6f,6f,p)
                p.clearShadowLayer();p.shader=null
                for(i in 0..2) {
                    p.color=if(i==0) turquoise else Color.rgb(21,78,145)
                    canvas.drawCircle(163f+i*17f,549f,3.5f,p)
                }
            }
            canvas.restore()
            if(t<durationMs && !ended.get()) postInvalidateDelayed(32L)
        }
    }
}
'''
java.mkdir(parents=True,exist_ok=True)
(java/"ProIntroActivity.kt").write_text(intro,encoding="utf-8")
ET.register_namespace("android","http://schemas.android.com/apk/res/android")
ns="{http://schemas.android.com/apk/res/android}"
tree=ET.parse(manifest)
app=tree.getroot().find("application")
if app is None:raise SystemExit("No manifest application")
for a in list(app.findall("activity")):
    if a.get(ns+"name")==".ProIntroActivity":
        app.remove(a)
        continue
    if a.get(ns+"name")==".MainActivity":
        for flt in list(a.findall("intent-filter")):
            if any(c.get(ns+"name")=="android.intent.category.LAUNCHER" for c in flt.findall("category")):
                a.remove(flt)
        a.set(ns+"exported","false")
a=ET.SubElement(app,"activity",{
    ns+"name":".ProIntroActivity",ns+"exported":"true",
    ns+"screenOrientation":"portrait",ns+"label":"@string/app_name",
    ns+"theme":"@style/Theme.Lingo"
})
flt=ET.SubElement(a,"intent-filter")
ET.SubElement(flt,"action",{ns+"name":"android.intent.action.MAIN"})
ET.SubElement(flt,"category",{ns+"name":"android.intent.category.LAUNCHER"})
tree.write(manifest,encoding="unicode",xml_declaration=True)

# The previous in-activity entrance must not run a second time after splash.
s=main.read_text(encoding="utf-8")
s=s.replace("try { GirisAnimasyonu.goster(this) } catch (_: Throwable) {}",
            "// GameLingo Pro entrance handled by ProIntroActivity")
main.write_text(s,encoding="utf-8")
strings=root/"res/values/strings.xml"
if strings.exists():
    st=ET.parse(strings)
    for el in st.getroot().findall("string"):
        if el.get("name")=="app_name":el.text="GameLingo Pro"
    st.write(strings,encoding="unicode",xml_declaration=True)
launchers=[]
for act in ET.parse(manifest).getroot().find("application").findall("activity"):
    for filt in act.findall("intent-filter"):
        if any(c.get(ns+"name")=="android.intent.category.LAUNCHER" for c in filt.findall("category")):
            launchers.append(act.get(ns+"name"))
assert launchers==[".ProIntroActivity"],launchers
assert 'applicationId = "com.gamelingo.pro"' in Path("app/build.gradle.kts").read_text()
print("Animated neon launcher and original electronic sound installed:",launchers[0])
