#!/usr/bin/env python3
"""3.4: render GT HUD text in source OCR bounds and hold captions through OCR misses.
Original Kotlin GameLingoPro / GameTranslator engine, never a replacement app.
Apply after v3.3 patch on the original project.
"""
from pathlib import Path
import re
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
tests=root/"app/src/test/java/com/example/altyazi"
cap=src/"CaptureService.kt"
overlay=src/"GtExactOverlay.kt"
oldOverlay=src/"Overlay.kt"
hud=src/"GtAllHud.kt"
menu=src/"GtMenuUi.kt"
build=root/"app/build.gradle.kts"
for f in (cap,overlay,oldOverlay,hud,menu,build):
    if not f.is_file():raise RuntimeError("Original source missing: "+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Not original GameLingoPro")
if 'overlay = GtExactOverlay(this)' not in cap.read_text():
    raise RuntimeError("GT-only renderer required")
def once(path, old, new):
    text=path.read_text(encoding="utf-8")
    n=text.count(old)
    if n!=1:raise RuntimeError(str(path)+" expected one anchor, got "+str(n)+": "+old[:90])
    path.write_text(text.replace(old,new,1),encoding="utf-8")
def span(path, beginning, ending, replacement):
    text=path.read_text(encoding="utf-8")
    a=text.find(beginning)
    b=text.find(ending,a+len(beginning)) if a>=0 else -1
    if a<0 or b<0:raise RuntimeError("Cannot locate block in "+str(path))
    path.write_text(text[:a]+replacement+text[b:],encoding="utf-8")

# Existing Overlay.Label is only a data contract; GT renderer remains the ONE
# active layer. Pass the bottom pixel and actual source line count as geometry.
once(oldOverlay,
'''        val rightX: Int? = null, val bottomY: Int? = null''',
'''        val rightX: Int? = null, val bottomY: Int? = null,
        val sourceLines: Int = 1''')
once(hud,
'''    data class Card(val zone:String, val text:String, val left:Int, val top:Int, val right:Int, val bottom:Int)''',
'''    data class Card(val zone:String, val text:String, val left:Int, val top:Int, val right:Int,
                    val bottom:Int, val sourceLines:Int=1)''')
once(hud,
'''            left,top,right,bottom)
    }
    fun region(''',
'''            left,top,right,bottom,rows.size)
    }
    fun region(''')
once(menu,
'''                GtAllHud.Card(zone,text,left,top,right,bottom)''',
'''                GtAllHud.Card(zone,text,left,top,right,bottom,group.size)''')

# Pure Kotlin geometry and presence rules are covered by automated JUnit tests.
geometry='''package com.example.altyazi

/** Exact OCR rectangle based placement; all sizes are SCREEN PIXELS. */
internal object GtSourceBox {
    fun width(source:Int,viewport:Int,padding:Int):Int =
        (source.coerceAtLeast(1)+padding.coerceAtLeast(0))
            .coerceIn(1,(viewport*0.47f).toInt().coerceAtLeast(1))
    fun fontPx(sourceHeight:Int,lines:Int,density:Float):Float {
        val rowPx=sourceHeight.toFloat()/lines.coerceIn(1,8)
        return (rowPx/1.13f).coerceIn(6f*density.coerceAtLeast(1f),
            16f*density.coerceAtLeast(1f))
    }
    fun hold(misses:Int,sinceSeenMs:Long):Boolean =
        misses<5 || sinceSeenMs<120000L
    fun nearby(ax:Int,ay:Int,bx:Int,by:Int,screenWidth:Int,screenHeight:Int):Boolean =
        kotlin.math.abs(ax-bx)<= (screenWidth*.025f).toInt().coerceAtLeast(10) &&
        kotlin.math.abs(ay-by)<= (screenHeight*.032f).toInt().coerceAtLeast(12)
}

/** Only short unpunctuated game instructions, never full spoken dialogue. */
internal object GtObjectiveLine {
    private val verbs=Regex(
        """(?i)^(?:steal|collect|find|follow|reach|meet|escape|interact with|go to|talk to|head to|drive to|wait for|pick up|return to|take a|use the|enter the|locate)\b"""
    )
    fun matches(raw:String):Boolean {
        val s=raw.trim()
        return s.length in 6..63 && !s.contains(':') && !s.contains('?') &&
            !s.contains('!') && !s.contains('.') && verbs.containsMatchIn(s)
    }
}
'''
(src/"GtSourceBox.kt").write_text(geometry,encoding="utf-8")

# A game objective in the bottom middle is still a HUD label, not dialogue.
once(hud,
'''        if(x>=0.40f && x<=0.60f && y>=subtitleTop)return null''',
'''        if(x>=0.40f && x<=0.60f && y>=subtitleTop &&
            !GtObjectiveLine.matches(line.text))return null''')
once(hud,
'''            y<subtitleTop -> "center"''',
'''            y<subtitleTop -> "center"
            GtObjectiveLine.matches(line.text) -> "center-objective"''')
once(menu,
'''              (line.top+line.bottom)/2f>=height*subtitleTop)''',
'''              (line.top+line.bottom)/2f>=height*subtitleTop &&
              !GtObjectiveLine.matches(line.text))''')

# Never feed a pure bottom-center objective to the large, spoken-caption layer.
once(cap,
'''        val text = proSubtitleAssembler.accept(
            adiAyir(clean(raw)), android.os.SystemClock.elapsedRealtime())

        if (text.isEmpty()) {''',
'''        val text = proSubtitleAssembler.accept(
            adiAyir(clean(raw)), android.os.SystemClock.elapsedRealtime())
        if(GtObjectiveLine.matches(text)) {
            // HUD OCR will draw this at its source rectangle, never as a
            // large bottom-centred speech subtitle.
            if(GtObjectiveLine.matches(shownSource)) {
                shownSource=""
                showSubtitle(null)
            }
            return
        }

        if (text.isEmpty()) {''')

once(cap,
'''                        overlay.clearLabels()
                        lastMenuKey = ""''',
'''                        overlay.clearLabels()
                        lastMenuKey = ""
                        lastHudLabels=emptyList()
                        gtHeldLabels.clear()
                        gtHudMissingScans=0
                        gtHudLastConfirmedAtMs=0L
                        gtLastMenuMode=null''')

# An empty OCR pass is not evidence that original source text disappeared:
# our opaque replacement box may obstruct its English letters in a capture.
once(cap,
'''    private var lastHudLabels: List<Overlay.Label> = emptyList()''',
'''    private var lastHudLabels: List<Overlay.Label> = emptyList()
    private var gtHudLastConfirmedAtMs=0L
    private var gtHudMissingScans=0
    private data class GtHeldLabel(var value:Overlay.Label,var lastSeenMs:Long)
    private val gtHeldLabels=ArrayList<GtHeldLabel>()
    private var gtLastMenuMode:Boolean?=null''')

# Treat transiently absent OCR and changing key separately; only expire
# after multiple misses and two minutes without a confirmed source sample.
once(cap,
'''        val key = cards.joinToString("|") { item ->
            item.zone+":"+item.text+":"+item.left/25+":"+item.top/25
        }
        if (key != gtHudCandidateKey) {''',
'''        val key = cards.joinToString("|") { item ->
            item.zone+":"+item.text+":"+item.left/25+":"+item.top/25
        }
        val hudNow=android.os.SystemClock.elapsedRealtime()
        if(cards.isNotEmpty()) {
            gtHudMissingScans=0
            gtHudLastConfirmedAtMs=hudNow
        } else if(lastHudLabels.isNotEmpty()) {
            gtHudMissingScans++
            if(GtSourceBox.hold(gtHudMissingScans,
                hudNow-gtHudLastConfirmedAtMs)) {
                PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
                return
            }
        }
        if (key != gtHudCandidateKey) {''')
once(cap,
'''            PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
            return
        }
        lastMenuKey=key''',
'''            gtHeldLabels.forEach{it.lastSeenMs=hudNow}
            PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
            return
        }
        lastMenuKey=key''')
once(cap,
'''        if(cards.isEmpty()){
            overlay.clearLabels()
            lastHudLabels=emptyList()
            PhoneBridgeService.clearHud()
            return
        }''',
'''        if(cards.isEmpty()){
            overlay.clearLabels()
            lastHudLabels=emptyList()
            gtHeldLabels.clear()
            gtLastMenuMode=null
            PhoneBridgeService.clearHud()
            return
        }
        if(gtLastMenuMode!=null && gtLastMenuMode!=fullMenuDetected)
            gtHeldLabels.clear()
        gtLastMenuMode=fullMenuDetected''')
once(cap,
'''            labels.add(Overlay.Label(translated,x,y,right))''',
'''            val bottom=(card.bottom.toFloat()/
                smallHeightForHud(full.width,full.height)*screenHeight).toInt()
            labels.add(Overlay.Label(translated,x,y,right,bottom,card.sourceLines))''')

once(cap,
'''        overlay.setLabels(labels)
        lastHudLabels=labels.toList()
        PhoneBridgeService.publishHud(labels,screenWidth,screenHeight)''',
'''        // Preserve readable translations through occasional partial/blank
        // OCR results, but replace a previous card when new source takes over
        // the same rectangle. Stale cards expire only after 120 seconds.
        gtHeldLabels.removeAll{held->hudNow-held.lastSeenMs>120000L}
        for(label in labels) {
            val found=gtHeldLabels.indexOfFirst{held->
                GtSourceBox.nearby(held.value.x,held.value.y,label.x,label.y,
                    screenWidth,screenHeight)
            }
            if(found>=0) {
                gtHeldLabels[found].value=label
                gtHeldLabels[found].lastSeenMs=hudNow
            } else gtHeldLabels.add(GtHeldLabel(label,hudNow))
        }
        while(gtHeldLabels.size>32)gtHeldLabels.removeAt(0)
        val visible=gtHeldLabels.map{it.value}
        overlay.setLabels(visible)
        lastHudLabels=visible
        PhoneBridgeService.publishHud(visible,screenWidth,screenHeight)''')

# GT visual boxes use source bounds and adapt font in px; unrelated
# subtitle-size preferences no longer inflate mission/menu text.
renderer='''    fun setLabels(labels:List<Overlay.Label>) {
        val container=root?:return
        container.post {
            while(boxes.size<labels.size){
                val tv=TextView(context).apply{visibility=View.GONE}
                hudStyle(tv)
                container.addView(tv,FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.WRAP_CONTENT,
                    FrameLayout.LayoutParams.WRAP_CONTENT).apply{
                    gravity=Gravity.TOP or Gravity.START
                })
                boxes.add(tv)
            }
            val w=container.width.takeIf{it>0}?:context.resources.displayMetrics.widthPixels
            val h=container.height.takeIf{it>0}?:context.resources.displayMetrics.heightPixels
            val density=context.resources.displayMetrics.density
            for(i in boxes.indices) {
                val tv=boxes[i]
                val card=labels.getOrNull(i)
                if(card==null || card.text.isBlank()) {
                    tv.visibility=View.GONE
                    continue
                }
                hudStyle(tv)
                tv.gravity=Gravity.TOP or Gravity.START
                tv.setPadding(dp(4),dp(2),dp(4),dp(2))
                tv.setLineSpacing(0f,1.05f)
                tv.text=speakerColor(card.text)
                val originalWidth=((card.rightX?:card.x+dp(96))-card.x)
                    .coerceAtLeast(dp(28))
                val originalHeight=((card.bottomY?:card.y+dp(23))-card.y)
                    .coerceAtLeast(dp(10))
                val sourceW=GtSourceBox.width(originalWidth,w,dp(8))
                    .coerceAtLeast(dp(38))
                val sourceH=(originalHeight+dp(7)).coerceAtLeast(dp(17))
                val minPx=dp(6).toFloat()
                var fontPx=GtSourceBox.fontPx(originalHeight,card.sourceLines,density)
                tv.maxWidth=sourceW
                // Fit translated text WITHIN the source rectangle before
                // permitting any expansion; no forced 28sp HUD labels.
                for(n in 0 until 26) {
                    tv.setTextSize(TypedValue.COMPLEX_UNIT_PX,fontPx)
                    tv.measure(View.MeasureSpec.makeMeasureSpec(sourceW,
                        View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(0,
                        View.MeasureSpec.UNSPECIFIED))
                    if(tv.measuredHeight<=sourceH || fontPx<=minPx)break
                    fontPx=(fontPx-.7f).coerceAtLeast(minPx)
                }
                val measuredH=tv.measuredHeight.coerceAtLeast(dp(14))
                val x=(card.x-dp(4)).coerceIn(0,(w-sourceW).coerceAtLeast(0))
                val y=(card.y-dp(2)).coerceIn(0,(h-measuredH).coerceAtLeast(0))
                val lp=tv.layoutParams as FrameLayout.LayoutParams
                lp.width=sourceW
                lp.height=FrameLayout.LayoutParams.WRAP_CONTENT
                lp.leftMargin=x
                lp.topMargin=y
                lp.rightMargin=0
                tv.layoutParams=lp
                tv.visibility=View.VISIBLE
            }
        }
    }
'''
span(overlay,'    fun setLabels(labels:List<Overlay.Label>) {','    fun clearLabels()',renderer)

# Static source-geometry and presence tests, including the reported GT map.
tests.mkdir(parents=True,exist_ok=True)
(tests/"GtOriginalBoundsTest.kt").write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtOriginalBoundsTest {
    @Test fun originalSourceBoxDoesNotBecomeFullScreen() {
        assertEquals(328,GtSourceBox.width(320,2142,8))
        assertEquals(96,GtSourceBox.width(88,2142,8))
    }
    @Test fun fontIsBasedOnSourceHeightNotChosenSubtitleSize() {
        assertTrue(GtSourceBox.fontPx(72,3,2f)<28f)
        assertEquals(GtSourceBox.fontPx(72,3,2f),
            GtSourceBox.fontPx(72,3,2f),.001f)
    }
    @Test fun englishIsStillVisibleSoOcrMissKeepsTranslation() {
        assertTrue(GtSourceBox.hold(3,5500L))
        assertTrue(GtSourceBox.hold(50,30000L))
        assertFalse(GtSourceBox.hold(20,121000L))
    }
    @Test fun bottomObjectiveBelongsToGameHud() {
        assertTrue(GtObjectiveLine.matches("Steal a suitable vehicle"))
        assertFalse(GtObjectiveLine.matches("Are you stealing a suitable vehicle?"))
        val line=GtAllHud.Line("Steal a suitable vehicle",650,624,920,648)
        assertEquals("center-objective",
            GtAllHud.region(line,1536,700,.78f))
    }
    @Test fun differentCardsCannotOverwriteAcrossScreen() {
        assertFalse(GtSourceBox.nearby(220,170,1280,170,1536,690))
        assertTrue(GtSourceBox.nearby(220,170,223,171,1536,690))
    }
    @Test fun gtRendererReallyUsesRectanglesAndOneLayer() {
        val code=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(code.contains("card.bottomY"))
        assertTrue(code.contains("GtSourceBox.fontPx"))
        assertFalse(code.contains("overlay = Overlay(this)"))
    }
}
''',encoding="utf-8")

version=build.read_text()
version,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
                  r'\g<1>versionCode = 20261207',version,count=1)
if n!=1:raise RuntimeError("Missing versionCode")
version,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
                  r'\g<1>versionName = "GameLingoPro-3.4-GT-SourceBounds"',version,count=1)
if n!=1:raise RuntimeError("Missing versionName")
build.write_text(version,encoding="utf-8")
print("GameLingoPro 3.4: source-bound GT HUD, long OCR presence, objective routing")
