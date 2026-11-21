#!/usr/bin/env python3
"""GameLingoPro native HUD: automatic multi-region OCR using GT text engine.
Keep GameLingoPro application, capture pipeline, TV bridge and GT glass overlay.
Run AFTER apply_gt_v27_engine.py and apply_gt_v27_subtitle_style.py.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"
prefs=src/"Prefs.kt"
overlay=src/"Overlay.kt"
build=root/"app/build.gradle.kts"
for f in [cap,prefs,overlay,build]:
    if not f.is_file(): raise RuntimeError("Original GameLingoPro source missing: "+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("Refusing to modify a different Android app")

helper=r'''// SPDX-License-Identifier: AGPL-3.0-only
package com.example.altyazi

/**
 * Region approach adapted from GameTranslator v1.8.49.
 * Unlike a single subtitle rectangle, game HUD texts can appear in all corners.
 * Pure Kotlin geometry; tested without an Android device.
 */
internal object GtAllHud {
    data class Line(val text:String, val left:Int, val top:Int, val right:Int, val bottom:Int)
    data class Card(val zone:String, val text:String, val left:Int, val top:Int, val right:Int, val bottom:Int)
    private data class MutableCard(
        val zone:String, val rows:MutableList<Line>, var left:Int,
        var top:Int, var right:Int, var bottom:Int
    ) {
        fun asCard():Card = Card(zone,rows.joinToString(" ") { it.text.trim() }.trim(),
            left,top,right,bottom)
    }
    fun region(line:Line, width:Int, height:Int, subtitleTop:Float):String? {
        if(width<=0||height<=0||line.bottom<=line.top)return null
        val x=(line.left+line.right).toFloat()/2/width
        val y=(line.top+line.bottom).toFloat()/2/height
        if(y<.065f||y>.985f)return null
        // The middle of the bottom strip belongs to the separate speech subtitle OCR.
        // BUT the left and right lower corners contain mission/inventory notifications.
        if(x>=0.40f && x<=0.60f && y>=subtitleTop)return null
        return when {
            x<=.44f && y>=.69f -> "left-bottom"
            x<=.44f -> "left-top"
            x>=.56f && y>=.69f -> "right-bottom"
            x>=.56f -> "right-top"
            y<subtitleTop -> "center"
            else -> null
        }
    }
    fun group(lines:List<Line>, width:Int, height:Int, subtitleTop:Float):List<Card> {
        val clean=lines.filter{
            it.text.count(Char::isLetter)>=3 &&
            it.right>it.left && it.bottom>it.top &&
            it.text.length<=340 && region(it,width,height,subtitleTop)!=null
        }.sortedWith(compareBy<Line>{it.top}.thenBy{it.left})
        val cards=mutableListOf<MutableCard>()
        for(line in clean) {
            val zone=region(line,width,height,subtitleTop)?:continue
            val heightOfLine=(line.bottom-line.top).coerceAtLeast(10)
            val match=cards.asReversed().firstOrNull { card ->
                if(card.zone!=zone || card.rows.size>=7)return@firstOrNull false
                val previous=card.rows.last()
                val gap=line.top-previous.bottom
                val h=(previous.bottom-previous.top).coerceAtLeast(10)
                val overlap=(minOf(line.right,card.right)-maxOf(line.left,card.left)).coerceAtLeast(0)
                val narrow=minOf(line.right-line.left,card.right-card.left).coerceAtLeast(1)
                val centerA=(line.left+line.right)/2
                val centerB=(card.left+card.right)/2
                gap >= -heightOfLine && gap<=maxOf(h,heightOfLine)*1.9f &&
                  (overlap>=narrow*.22f || kotlin.math.abs(centerA-centerB)<=width*.055f)
            }
            if(match==null)cards.add(MutableCard(zone,mutableListOf(line),
                line.left,line.top,line.right,line.bottom))
            else {
                match.rows.add(line)
                match.left=minOf(match.left,line.left)
                match.top=minOf(match.top,line.top)
                match.right=maxOf(match.right,line.right)
                match.bottom=maxOf(match.bottom,line.bottom)
            }
        }
        return cards.asSequence().map{it.asCard()}
            .filter{it.text.length>=5}
            .sortedWith(compareBy<Card>{it.zone}.thenBy{it.top}.thenBy{it.left})
            .take(6).toList()
    }
}
'''
(src/"GtAllHud.kt").write_text(helper,encoding="utf-8")

t=cap.read_text(encoding="utf-8")
start="    private suspend fun processMenu(full: Bitmap) {"
end="    /**\n     * Yan yazı alanı kararı;"
a=t.find(start)
b=t.find(end,a+len(start))
if a<0 or b<0:raise RuntimeError("Menu function anchors not found")
replacement=r'''    /**
     * GameTranslator-style complete HUD capture. Separate on-screen cards are
     * translated as ONE block, never sentence-by-sentence OCR fragments.
     * The speech subtitle is still handled by processSubtitle independently.
     */
    private suspend fun processMenu(full: Bitmap) {
        val scale = min(1f, MENU_WIDTH.toFloat() / max(full.width, 1))
        val small = if (scale < 1f)
            Bitmap.createScaledBitmap(full,
                max(2,(full.width*scale).toInt()),
                max(2,(full.height*scale).toInt()),true)
        else full

        val cards = try {
            val rawLines = ocrLines(small)
            val candidates = ArrayList<GtAllHud.Line>()
            for ((raw,box) in rawLines) {
                if (box == null) continue
                val text = raw.trim()
                if (text.length<3 || text.count(Char::isLetter)<3) continue
                if (isControllerLabel(text) || isOurOwnText(text)) continue
                if (displayed.contains(normalize(text))) continue
                candidates.add(GtAllHud.Line(text,box.left,box.top,box.right,box.bottom))
            }
            GtAllHud.group(candidates,small.width,small.height,
                prefs.topPct.coerceIn(0,98)/100f)
        } finally {
            if(small!==full)small.recycle()
        }

        // Two OCR passes protect against transient animated text, but the
        // scan must not be disabled just because the default preference was false.
        val key = cards.joinToString("|") { item ->
            item.zone+":"+item.text+":"+item.left/25+":"+item.top/25
        }
        if (key != gtHudCandidateKey) {
            gtHudCandidateKey=key
            gtHudCandidateSeen=1
            return
        }
        gtHudCandidateSeen++
        if(gtHudCandidateSeen<2)return
        if(key==lastMenuKey){
            PhoneBridgeService.publishHud(lastHudLabels,screenWidth,screenHeight)
            return
        }
        lastMenuKey=key
        if(cards.isEmpty()){
            overlay.clearLabels()
            lastHudLabels=emptyList()
            PhoneBridgeService.clearHud()
            return
        }

        val labels=ArrayList<Overlay.Label>()
        for(card in cards){
            val source = GtNativeEngine.normalize(card.text)
            if(source.isBlank() || isOurOwnText(source))continue
            val cacheKey=card.zone+"|"+source
            var translated=gtHudTranslatedCache[cacheKey]
            if(translated==null){
                translated=translateMenuText(source)?.trim()
                if(translated.isNullOrBlank())continue
                if(gtHudTranslatedCache.size>160)gtHudTranslatedCache.remove(
                    gtHudTranslatedCache.keys.first())
                gtHudTranslatedCache[cacheKey]=translated
            }
            val x=(card.left.toFloat()/smallWidthForHud(full.width)*screenWidth).toInt()
            val y=(card.top.toFloat()/smallHeightForHud(full.width,full.height)*screenHeight).toInt()
            val right=(card.right.toFloat()/smallWidthForHud(full.width)*screenWidth).toInt()
            labels.add(Overlay.Label(translated,x,y,right))
            displayed.add(normalize(translated))
        }
        overlay.setLabels(labels)
        lastHudLabels=labels.toList()
        PhoneBridgeService.publishHud(labels,screenWidth,screenHeight)
    }
    // The capture bitmap is scaled uniformly down to MENU_WIDTH.
    private fun smallWidthForHud(width:Int):Float =
        min(1f,MENU_WIDTH.toFloat()/max(width,1))*width
    private fun smallHeightForHud(width:Int,height:Int):Float =
        min(1f,MENU_WIDTH.toFloat()/max(width,1))*height

'''
t=t[:a]+replacement+t[b:]
anchor='    private var lastHudLabels: List<Overlay.Label> = emptyList()'
if t.count(anchor)!=1:raise RuntimeError("Missing existing PhoneBridge HUD state")
t=t.replace(anchor,anchor+'''
    private var gtHudCandidateKey=""
    private var gtHudCandidateSeen=0
    private val gtHudTranslatedCache=LinkedHashMap<String,String>()
''',1)
# Enabling the existing menu overlay option on existing installations only once
# preserves the user's ability to turn it back off manually.
p=prefs.read_text(encoding="utf-8")
needle='    var menuTranslate: Boolean'
if p.count(needle)!=1:raise RuntimeError("Menu preference anchor missing")
# Add a one-time migration separately from the previous defaults migration.
block='''    private val gtMultiHudPreferenceMigration: Boolean = run {
        if (!sp.getBoolean("gtMultiHudV28Configured", false)) {
            sp.edit().putBoolean("menuTranslate",true)
                .putBoolean("gtMultiHudV28Configured",true).apply()
        }
        true
    }

'''
cap.write_text(t,encoding="utf-8")
p=p.replace(needle,block+needle,1)
prefs.write_text(p,encoding="utf-8")
# Make the native GT HUD labels use the same rounded glass style, without
# reviving the old yellow overlay or covering the bottom speech subtitle.
o=overlay.read_text(encoding="utf-8")
if 'class Overlay(' not in o or 'fun setLabels(' not in o:raise RuntimeError("Wrong overlay")
# Right-edge clamp was already installed in the native HUD bridge patch.
if 'val desiredX = if (rightSide)' not in o:raise RuntimeError("Native right side HUD anchor missing")
o=o.replace('setColor(Color.argb(205, 0, 0, 0))',
            'setColor(Color.argb(226, 0, 0, 0))')
overlay.write_text(o,encoding="utf-8")
build_text=build.read_text(encoding="utf-8")
build_text,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',
    r'\g<1>versionCode = 20261129',build_text,count=1)
if n!=1:raise RuntimeError("Version code missing")
build_text,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-2.8-GT-AllHUD"',build_text,count=1)
if n!=1:raise RuntimeError("Version name missing")
build.write_text(build_text,encoding="utf-8")

tests=root/"app/src/test/java/com/example/altyazi/GtAllHudTest.kt"
tests.parent.mkdir(parents=True,exist_ok=True)
tests.write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtAllHudTest {
  @Test fun leftGameTipIsOneCard() {
    val lines=listOf(
      GtAllHud.Line("Tip: Suppressors and tactical",180,178,450,204),
      GtAllHud.Line("flashlights can be equipped and",182,205,460,229),
      GtAllHud.Line("removed in your loadout.",183,232,420,255))
    val cards=GtAllHud.group(lines,1536,700,.74f)
    assertEquals(1,cards.size)
    assertEquals("left-top",cards[0].zone)
    assertTrue(cards[0].text.contains("removed in your loadout"))
  }
  @Test fun rightBottomRewardIsNotIgnored() {
    val card=GtAllHud.Line("Bucked You $50",1120,612,1480,664)
    val out=GtAllHud.group(listOf(card),1536,700,.74f)
    assertEquals(1,out.size)
    assertEquals("right-bottom",out[0].zone)
  }
  @Test fun bottomCenterSpeechIsNotDuplicated() {
    val speech=GtAllHud.Line("This is a subtitle not a HUD notice.",420,622,1120,656)
    assertTrue(GtAllHud.group(listOf(speech),1536,700,.74f).isEmpty())
  }
  @Test fun nearbyRowsDoNotJoinAcrossSides() {
    val lines=listOf(GtAllHud.Line("Go to the docks",120,220,390,244),
       GtAllHud.Line("Inventory updated",1180,220,1490,244))
    assertEquals(2,GtAllHud.group(lines,1536,700,.74f).size)
  }
  @Test fun screenCenterHudWorksAboveSubtitle() {
    val line=GtAllHud.Line("Press E to interact",630,250,910,278)
    assertEquals("center",GtAllHud.group(listOf(line),1536,700,.74f).single().zone)
  }
}
''',encoding="utf-8")
assert 'GtAllHud.group' in cap.read_text()
assert 'gtMultiHudV28Configured' in prefs.read_text()
print("GameLingoPro native GameTranslator multi-HUD patch installed")
