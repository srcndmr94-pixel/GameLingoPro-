#!/usr/bin/env python3
"""Replace procedural fallback with the four user-provided neon frames.

Run only after apply_pro_intro.py. Image assets are stored as base64 ZIP in the
repository so GitHub Actions can assemble the Android app independently.
"""
from pathlib import Path
import base64,io,zipfile
from xml.etree import ElementTree as ET
root=Path("app/src/main")
source=Path("tools/pro_intro_frames.b64")
if not source.exists():raise SystemExit("Original splash artwork is missing")
d=root/"res/drawable-nodpi"
d.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(source.read_text().strip()))) as z:
    expected={f"intro_phase{i}.webp" for i in range(1,5)}
    if set(z.namelist())!=expected:raise SystemExit("Unexpected splash artwork entries")
    for name in sorted(expected):
        (d/name).write_bytes(z.read(name))
java=root/"java/com/example/altyazi"
kt=r'''package com.example.altyazi

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.MotionEvent
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import java.util.concurrent.atomic.AtomicBoolean

/** The four frames come from the user's GameLingoPro neon design. */
class ProIntroActivity : Activity() {
    private val ended=AtomicBoolean(false)
    private val handler=Handler(Looper.getMainLooper())
    private var music:MediaPlayer?=null
    private var clicks:ProClickFeedback?=null
    private val settings by lazy {getSharedPreferences("gamelingo_pro_intro",MODE_PRIVATE)}
    private val end=Runnable {openMain()}

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        clicks=ProClickFeedback(this)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility=(View.SYSTEM_UI_FLAG_FULLSCREEN or
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
        val root=FrameLayout(this).apply {setBackgroundColor(Color.rgb(2,3,15))}
        val images=intArrayOf(R.drawable.intro_phase1,R.drawable.intro_phase2,
            R.drawable.intro_phase3,R.drawable.intro_phase4)
        val layers=images.mapIndexed {i,id->
            ImageView(this).apply {
                setImageResource(id)
                scaleType=ImageView.ScaleType.CENTER_CROP
                alpha=if(i==0) 1f else 0f
                contentDescription="GameLingo Pro neon animasyonu"
                root.addView(this,FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT))
            }
        }
        val skip=TextView(this).apply {
            text="ATLA";textSize=13f;setTextColor(Color.WHITE);gravity=Gravity.CENTER
            setBackgroundColor(Color.argb(170,12,23,41))
            setOnClickListener {openMain()}
        }
        val mute=TextView(this).apply {
            textSize=22f;setTextColor(Color.WHITE);gravity=Gravity.CENTER
            setBackgroundColor(Color.argb(170,12,23,41))
            text=if(settings.getBoolean("intro_music",true)) "♫" else "×"
            setOnClickListener {
                val on=!settings.getBoolean("intro_music",true)
                settings.edit().putBoolean("intro_music",on).apply()
                text=if(on) "♫" else "×"
                if(on) playMusic() else stopMusic()
            }
        }
        val scale=resources.displayMetrics.density
        fun px(dp:Float)=(dp*scale).toInt()
        root.addView(skip,FrameLayout.LayoutParams(px(68f),px(40f),Gravity.TOP or Gravity.END).apply {
            setMargins(0,px(42f),px(18f),0)
        })
        root.addView(mute,FrameLayout.LayoutParams(px(40f),px(40f),Gravity.TOP or Gravity.START).apply {
            setMargins(px(18f),px(42f),0,0)
        })
        setContentView(root)
        playMusic()
        listOf(780L,1770L,2950L).forEachIndexed {idx,delay ->
            handler.postDelayed({
                if(!ended.get()) {
                    layers[idx+1].animate().alpha(1f).setDuration(480L).start()
                }
            },delay)
        }
        handler.postDelayed(end,5000L)
    }
    private fun playMusic() {
        if(ended.get() || !settings.getBoolean("intro_music",true)) return
        stopMusic()
        try {
            music=MediaPlayer.create(this,R.raw.pro_intro_theme)?.apply {
                isLooping=false;setVolume(.55f,.55f);start()
            }
        } catch (_:Exception) {stopMusic()}
    }
    private fun stopMusic() {
        try {music?.stop()} catch (_:Exception) {}
        try {music?.release()} catch (_:Exception) {}
        music=null
    }
    private fun openMain() {
        if(!ended.compareAndSet(false,true)) return
        handler.removeCallbacksAndMessages(null)
        stopMusic()
        startActivity(Intent(this,MainActivity::class.java))
        @Suppress("DEPRECATION")
        overridePendingTransition(android.R.anim.fade_in,android.R.anim.fade_out)
        finish()
    }
    override fun dispatchTouchEvent(ev:MotionEvent):Boolean {
        val handled=super.dispatchTouchEvent(ev)
        if(handled) clicks?.onTouch(ev)
        return handled
    }
    override fun onPause() {stopMusic();super.onPause()}
    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        clicks?.release();stopMusic();super.onDestroy()
    }
}
'''
(java/"ProIntroActivity.kt").write_text(kt,encoding="utf-8")
ET.parse(root/"AndroidManifest.xml")
assert (root/"res/raw/pro_intro_theme.wav").exists()
assert all((d/f"intro_phase{i}.webp").stat().st_size>1000 for i in range(1,5))
print("Four custom neon frames successfully wired into the GameLingoPro startup Activity")
