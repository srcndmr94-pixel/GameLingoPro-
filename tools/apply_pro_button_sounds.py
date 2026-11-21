#!/usr/bin/env python3
"""Add unobtrusive GameLingoPro button sounds to extracted Android sources."""
from pathlib import Path
import math, struct, wave, re
import xml.etree.ElementTree as ET

root=Path("app/src/main")
java=root/"java/com/example/altyazi"
layout=root/"res/layout/activity_main.xml"
raw=root/"res/raw"
raw.mkdir(parents=True,exist_ok=True)

# Two original neon clicks (mono WAV), not licensed third-party sounds.
for kind,seconds,freq in [("click",.075,880),("confirm",.115,1040)]:
    b=bytearray()
    for i in range(int(22050*seconds)):
        t=i/22050
        p=t/seconds
        env=min(1.,t/.004)*(1-p)**2.5
        value=.36*env*(math.sin(2*math.pi*(freq*t-125*t*t/seconds))+
                          .14*math.sin(2*math.pi*freq*2*t))
        b.extend(struct.pack("<h",int(max(-1.,min(1.,value))*32767)))
    with wave.open(str(raw/("pro_ui_"+kind+".wav")),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050);w.writeframes(b)

java.joinpath("ProClickFeedback.kt").write_text(r"""package com.example.altyazi

import android.app.Activity
import android.content.Context
import android.graphics.Rect
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.SoundPool
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.ViewGroup
import android.webkit.WebView
import android.widget.EditText
import kotlin.math.abs

/** Independent feedback for GameLingo Pro. Leaves existing click listeners untouched. */
internal class ProClickFeedback(private val activity: Activity) {
    private val audio = activity.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val slop = ViewConfiguration.get(activity).scaledTouchSlop.toFloat()
    private val pool = SoundPool.Builder().setMaxStreams(2).setAudioAttributes(
        AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()
    ).build()
    private var clickId = 0
    private var confirmId = 0
    private var clickReady = false
    private var confirmReady = false
    private var tracking = false
    private var x = 0f
    private var y = 0f

    init {
        pool.setOnLoadCompleteListener { _, id, status ->
            if (status == 0) {
                if (id == clickId) clickReady = true
                if (id == confirmId) confirmReady = true
            }
        }
        clickId = pool.load(activity, R.raw.pro_ui_click, 1)
        confirmId = pool.load(activity, R.raw.pro_ui_confirm, 1)
    }

    fun onTouch(e: MotionEvent) {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                x = e.rawX
                y = e.rawY
                tracking = true
            }
            MotionEvent.ACTION_MOVE ->
                if (abs(x-e.rawX)>slop || abs(y-e.rawY)>slop) tracking=false
            MotionEvent.ACTION_CANCEL, MotionEvent.ACTION_POINTER_DOWN -> tracking=false
            MotionEvent.ACTION_UP -> {
                val tap=tracking && abs(x-e.rawX)<=slop && abs(y-e.rawY)<=slop
                tracking=false
                if (!tap || !enabled(activity) ||
                    audio.ringerMode != AudioManager.RINGER_MODE_NORMAL) return
                val target=findClickable(activity.window.decorView,e.rawX.toInt(),e.rawY.toInt()) ?: return
                val confirm=target.id == R.id.btnToggle
                if (confirm && confirmReady) pool.play(confirmId,.28f,.28f,1,0,1f)
                if (!confirm && clickReady) pool.play(clickId,.22f,.22f,1,0,1f)
            }
        }
    }

    private fun findClickable(view: View, x: Int, y: Int): View? {
        if (view.visibility != View.VISIBLE || !view.isEnabled || view.alpha <= 0f) return null
        val rect=Rect()
        if (!view.getGlobalVisibleRect(rect) || !rect.contains(x,y)) return null
        if (view is WebView || view is EditText) return null
        if (view is ViewGroup) for (i in view.childCount-1 downTo 0) {
            val hit=findClickable(view.getChildAt(i),x,y)
            if (hit != null) return hit
        }
        return if (view.isClickable) view else null
    }

    fun release() = pool.release()

    companion object {
        private const val FILE="gamelingo_pro_feedback"
        private const val KEY="button_sounds_enabled"
        fun enabled(c:Context)=c.getSharedPreferences(FILE,Context.MODE_PRIVATE).getBoolean(KEY,true)
        fun save(c:Context,on:Boolean) {
            c.getSharedPreferences(FILE,Context.MODE_PRIVATE).edit().putBoolean(KEY,on).apply()
        }
    }
}
""",encoding="utf-8")

xml=layout.read_text(encoding="utf-8")
if "cbProButtonSfx" not in xml:
    mark="<!-- ===================== AYAR MENÜSÜ (10.54) ===================== -->"
    if mark not in xml: raise SystemExit("Settings marker not found; no files silently patched")
    widget="""<LinearLayout android:layout_width="match_parent"
        android:layout_height="wrap_content" android:orientation="vertical"
        android:layout_marginStart="16dp" android:layout_marginEnd="16dp"
        android:paddingStart="12dp" android:paddingEnd="12dp">
        <CheckBox android:id="@+id/cbProButtonSfx"
            android:layout_width="match_parent" android:layout_height="wrap_content"
            android:text="Tuş sesleri" android:textStyle="bold"
            android:buttonTint="#2DE6DB" />
        <TextView android:layout_width="match_parent"
            android:layout_height="wrap_content" android:paddingStart="32dp"
            android:text="Neon tıklama sesi · Sessiz modda kapalı"
            android:textSize="12sp" />
    </LinearLayout>
    """
    xml=xml.replace(mark,widget+mark,1)
    layout.write_text(xml,encoding="utf-8")
ET.parse(layout)

def patch(path):
    if not path.exists():return
    s=path.read_text(encoding="utf-8")
    if "ProClickFeedback(this)" in s:return
    init=re.search(r"override fun onCreate\(savedInstanceState:\s*Bundle\?\)\s*\{\s*super\.onCreate\(savedInstanceState\)",s)
    cls=re.search(r"class\s+\w+\s*:\s*[^{]+\{",s)
    if not init or not cls:raise SystemExit("Unable to patch "+str(path))
    s=s[:init.end()]+"\n        proClickFeedback = ProClickFeedback(this)"+s[init.end():]
    cls=re.search(r"class\s+\w+\s*:\s*[^{]+\{",s)
    s=s[:cls.end()]+"\n    private var proClickFeedback: ProClickFeedback? = null\n"+s[cls.end():]
    dispatch="""
    override fun dispatchTouchEvent(e: android.view.MotionEvent): Boolean {
        val handled = super.dispatchTouchEvent(e)
        if (handled) proClickFeedback?.onTouch(e)
        return handled
    }
    """
    destroy=re.search(r"override fun onDestroy\s*\(\s*\)\s*\{",s)
    if destroy:
        s=s[:destroy.start()]+dispatch+"\n    "+s[destroy.start():]
        destroy=re.search(r"override fun onDestroy\s*\(\s*\)\s*\{",s)
        s=s[:destroy.end()]+"\n        proClickFeedback?.release()"+s[destroy.end():]
    else:
        create=re.search(r"override fun onCreate\s*\(",s)
        s=s[:create.start()]+dispatch+"""
    override fun onDestroy() {
        proClickFeedback?.release()
        super.onDestroy()
    }
    """+s[create.start():]
    path.write_text(s,encoding="utf-8")

for act in ["MainActivity","ConsoleSettingsActivity","RegionActivity","PsnAuthActivity","ProIntroActivity"]:
    patch(java/(act+".kt"))
p=java/"MainActivity.kt"
s=p.read_text(encoding="utf-8")
if "R.id.cbProButtonSfx)" not in s:
    target="prefs = Prefs(this)"
    if target not in s:raise SystemExit("MainActivity settings hook unavailable")
    s=s.replace(target,target+"""
        findViewById<android.widget.CheckBox>(R.id.cbProButtonSfx).apply {
            isChecked = ProClickFeedback.enabled(this@MainActivity)
            setOnCheckedChangeListener { _, enabled ->
                ProClickFeedback.save(this@MainActivity,enabled)
            }
        }
    """,1)
    p.write_text(s,encoding="utf-8")
print("GameLingoPro button audio, on/off setting and original WAV resources installed")
