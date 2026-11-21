#!/usr/bin/env python3
"""GameLingoPro 4.1: selected map information boxes, not the changing map.
Apply after 4.0 to original GameLingoPro source. Does not replace the app.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
base=root/'app/src/main/java/com/example/altyazi'
cap=base/'CaptureService.kt'
build=root/'app/build.gradle.kts'
tests=root/'app/src/test/java/com/example/altyazi'
for p in [cap,build,base/'GtAllHud.kt',base/'GtExactOverlay.kt',base/'GtMenuUi.kt']:
    if not p.is_file():raise RuntimeError('GameLingoPro 4.0 source missing: '+str(p))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError('Not original GameLingoPro')
if 'GtMenuPriority.score(card' not in cap.read_text():
    raise RuntimeError('Version 4.0 must be applied first')

def once(p,old,new):
    c=p.read_text(encoding='utf8')
    n=c.count(old)
    if n!=1:raise RuntimeError(f'{p.name}: {n} anchors; expected one: {old[:80]}')
    p.write_text(c.replace(old,new,1),encoding='utf8')

(base/'GtSelectedMapPanel.kt').write_text(r'''package com.example.altyazi
import java.util.Locale

/** Read selected map box paragraphs by their untouched on-screen headers.
 * The header is not overlaid, so its disappearance can clear the translation.
 */
internal object GtSelectedMapPanel {
    data class Panel(val slot:String,val title:String,val body:String,
        val left:Int,val top:Int,val right:Int,val bottom:Int,val rows:Int) {
        val identity:String get()=slot+"|"+title.lowercase(Locale.ROOT).trim()
    }
    private val tabs=setOf("map","brief","progress")
    fun isMap(lines:List<GtAllHud.Line>,w:Int,h:Int):Boolean =
        w>=100 && h>=100 && lines.count {
            it.top.toFloat()/h<.12f &&
            it.text.lowercase(Locale.ROOT).trim() in tabs
        }>=2
    private fun heading(s:String):Boolean {
        val t=s.trim()
        val letters=t.filter{it.isLetter()}
        return t.length in 4..54 && letters.length>=4 &&
            letters.all{it.isUpperCase()} && '.' !in t && ':' !in t &&
            t.lowercase(Locale.ROOT) !in setOf("inventory","features",
                "standard","recenter","set destination","add marker",
                "exit","map","brief","progress","2d view","security")
    }
    private fun inBox(lines:List<GtAllHud.Line>,w:Int,h:Int,slot:String):Panel? {
        val right=slot=="right"
        val minX=if(right).50f else .15f
        val maxX=if(right).79f else .42f
        val minY=if(right).19f else .075f
        val maxY=if(right).66f else .39f
        val titles=lines.filter{ heading(it.text) &&
            it.left.toFloat()/w in minX..maxX &&
            it.top.toFloat()/h in minY..maxY
        }.sortedBy{it.top}
        for(head in titles) {
            val lower=lines.filter { row ->
                row.top>head.bottom &&
                row.top-head.bottom<=h*.30f &&
                row.left>=head.left-w*.025f &&
                row.left<=head.left+w*.055f &&
                row.right<=head.left+w*.295f &&
                row.text.any{it.isLowerCase()} &&
                row.text.length>=8
            }.sortedBy{it.top}
            val rows=ArrayList<GtAllHud.Line>()
            for(line in lower) {
                if(rows.isNotEmpty()) {
                    val gap=line.top-rows.last().bottom
                    if(gap>h*.055f || gap < -h*.04f)break
                }
                rows.add(line)
                if(rows.size>=9)break
            }
            if(rows.isNotEmpty()) {
                val text=rows.joinToString(" "){it.text.trim()}
                if(text.length>=12)return Panel(slot,head.text.trim(),text,
                    rows.minOf{it.left},rows.minOf{it.top},
                    rows.maxOf{it.right},rows.maxOf{it.bottom},rows.size)
            }
            // Body may now be covered by our translation. Keep header visible
            // and track source presence without inserting permanent text.
            return Panel(slot,head.text.trim(),"",head.left,head.bottom+3,
                head.right,head.bottom+22,1)
        }
        return null
    }
    fun panels(lines:List<GtAllHud.Line>,w:Int,h:Int):List<Panel> =
        listOfNotNull(inBox(lines,w,h,"right"),inBox(lines,w,h,"left"))
}
''',encoding='utf8')

once(cap,
'''    private var menuJob: Job? = null''',
'''    private var menuJob: Job? = null
    @Volatile private var gtMapPanelMode=false
    private var gtMapMisses=0
    private val gtPanelKeys=java.util.concurrent.ConcurrentHashMap<String,String>()
    private val gtPanelText=java.util.concurrent.ConcurrentHashMap<String,String>()
    private val gtPanelRects=java.util.concurrent.ConcurrentHashMap<String,Overlay.Label>()
    private val gtPanelJobs=java.util.concurrent.ConcurrentHashMap<String,Job>()
    private val gtPanelMisses=java.util.concurrent.ConcurrentHashMap<String,Int>()
    private val gtPanelCache=java.util.concurrent.ConcurrentHashMap<String,String>()
    private val gtPanelLastAttempt=java.util.concurrent.ConcurrentHashMap<String,Long>()''')

once(cap,
'''                        gtLastMenuMode=null
                        delay(250)''',
'''                        gtLastMenuMode=null
                        gtMapPanelMode=false
                        gtPanelJobs.values.forEach{it.cancel()}
                        gtPanelJobs.clear()
                        gtPanelKeys.clear()
                        gtPanelText.clear()
                        gtPanelRects.clear()
                        gtPanelMisses.clear()
                        gtPanelLastAttempt.clear()
                        gtMapMisses=0
                        delay(250)''')

once(cap,
'''                    processSubtitle(full)

                    // Menü çevirisi tüm ekranı okur, ağırdır: TV'de kapalı.
                    if (!isTv && cycle % MENU_EVERY == 0L && menuJob?.isActive != true) {''',
'''                    if(!gtMapPanelMode)processSubtitle(full)

                    // The selected map box has its own quick OCR flow.
                    if (!isTv && (gtMapPanelMode || cycle % MENU_EVERY == 0L) &&
                        menuJob?.isActive != true) {''')

once(cap,
'''    private suspend fun processMenu(full: Bitmap) {
        val scale = min(1f, MENU_WIDTH.toFloat() / max(full.width, 1))''',
'''    private suspend fun processMenu(full: Bitmap) {
        if(processMapDetailPanels(full))return
        val scale = min(1f, MENU_WIDTH.toFloat() / max(full.width, 1))''')

anchor='''    // The capture bitmap is scaled uniformly down to MENU_WIDTH.'''
code=r'''    private fun drawMapDetailPanels() {
        val ready=listOf("right","left").mapNotNull{slot->
            val text=gtPanelText[slot]?:return@mapNotNull null
            val geo=gtPanelRects[slot]?:return@mapNotNull null
            if(text.isBlank())null else Overlay.Label(
                text,geo.x,geo.y,geo.rightX,geo.bottomY,geo.sourceLines)
        }
        overlay.setLabels(ready)
        lastHudLabels=ready
        PhoneBridgeService.publishHud(ready,screenWidth,screenHeight)
    }

    private fun resetMapDetailPanels() {
        gtPanelJobs.values.forEach{it.cancel()}
        gtPanelJobs.clear()
        gtPanelKeys.clear()
        gtPanelText.clear()
        gtPanelRects.clear()
        gtPanelMisses.clear()
        gtPanelLastAttempt.clear()
        overlay.clearLabels()
        lastHudLabels=emptyList()
        gtHeldLabels.clear()
        PhoneBridgeService.clearHud()
    }

    private suspend fun processMapDetailPanels(full:Bitmap):Boolean {
        val factor=min(1f,MENU_WIDTH.toFloat()/max(full.width,1))
        val small=if(factor<1f)Bitmap.createScaledBitmap(full,
            max(2,(full.width*factor).toInt()),
            max(2,(full.height*factor).toInt()),true) else full
        val width=small.width
        val height=small.height
        val lines=try {
            ocrLines(small).mapNotNull{(t,box)->
                if(box==null || t.count(Char::isLetter)<2)null
                else GtAllHud.Line(t.trim(),box.left,box.top,box.right,box.bottom)
            }
        } finally {if(small!==full)small.recycle()}

        val isMap=GtSelectedMapPanel.isMap(lines,width,height)
        if(!isMap) {
            if(!gtMapPanelMode)return false
            gtMapMisses++
            if(gtMapMisses<2)return true
            gtMapPanelMode=false
            gtMapMisses=0
            resetMapDetailPanels()
            return false
        }
        gtMapMisses=0
        if(!gtMapPanelMode) {
            gtMapPanelMode=true
            resetMapDetailPanels()
            lastMenuKey=""
            gtHudCandidateKey=""
            if(shownSource.isNotBlank()) {
                shownSource=""
                translatingFor=""
                subtitleGeneration.invalidate()
            }
            showSubtitle(null)
        }

        val visible=GtSelectedMapPanel.panels(lines,width,height)
        for(slot in listOf("right","left")) {
            val panel=visible.firstOrNull{it.slot==slot}
            if(panel==null) {
                val missed=(gtPanelMisses[slot]?:0)+1
                gtPanelMisses[slot]=missed
                if(missed>=2) {
                    gtPanelJobs.remove(slot)?.cancel()
                    gtPanelKeys.remove(slot)
                    gtPanelText.remove(slot)
                    gtPanelRects.remove(slot)
                    drawMapDetailPanels()
                }
                continue
            }
            gtPanelMisses[slot]=0
            val identity=panel.identity
            if(gtPanelKeys[slot]!=identity) {
                gtPanelJobs.remove(slot)?.cancel()
                gtPanelKeys[slot]=identity
                gtPanelText.remove(slot)
                gtPanelRects.remove(slot)
                gtPanelLastAttempt.remove(slot)
                drawMapDetailPanels()
            }
            if(panel.body.isNotBlank()) {
                val scaleX=screenWidth.toFloat()/width
                val scaleY=screenHeight.toFloat()/height
                gtPanelRects[slot]=Overlay.Label("",
                    (panel.left*scaleX).toInt(),
                    (panel.top*scaleY).toInt(),
                    (panel.right*scaleX).toInt(),
                    (panel.bottom*scaleY).toInt(),panel.rows)
            }
            val source=panel.body.trim()
            if(source.isBlank())continue
            if(gtPanelText[slot]!=null)continue
            val cacheKey=identity+"|"+GtNativeEngine.normalize(source)
            val cached=gtPanelCache[cacheKey]
            if(cached!=null) {
                gtPanelText[slot]=cached
                drawMapDetailPanels()
                continue
            }
            if(gtPanelJobs[slot]?.isActive==true)continue
            val now=android.os.SystemClock.elapsedRealtime()
            if(now-(gtPanelLastAttempt[slot]?:0L)<1500L)continue
            gtPanelLastAttempt[slot]=now
            // No global stable-map test; each box translates in an independent
            // coroutine while OCR keeps observing its untouched English title.
            gtPanelJobs[slot]=scope.launch {
                val translated=kotlinx.coroutines.withTimeoutOrNull(3600L) {
                    translateMenuText(source)
                }?.trim()
                if(!translated.isNullOrBlank() &&
                   !translated.equals(source,ignoreCase=true) &&
                   gtMapPanelMode && gtPanelKeys[slot]==identity) {
                    gtPanelCache[cacheKey]=translated
                    gtPanelText[slot]=translated
                    drawMapDetailPanels()
                    log("HARİTA KUTUSU ÇEVRİLDİ: "+slot+" / "+panel.title)
                } else if(gtMapPanelMode && gtPanelKeys[slot]==identity) {
                    log("HARİTA KUTUSU ÇEVRİLEMEDİ: "+slot+" / "+panel.title)
                }
            }
        }
        return true
    }

'''
s=cap.read_text(encoding='utf8')
if s.count(anchor)!=1:raise RuntimeError('Map helper insertion point missing')
cap.write_text(s.replace(anchor,code+anchor,1),encoding='utf8')

tests.mkdir(parents=True,exist_ok=True)
(tests/'GtSelectedMapPanelTest.kt').write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test

class GtSelectedMapPanelTest {
    private fun line(t:String,x:Int,y:Int,w:Int=240,h:Int=19) =
        GtAllHud.Line(t,x,y,x+w,y+h)
    private val tabs=listOf(line("MAP",730,20),line("BRIEF",800,20),
        line("PROGRESS",890,20))
    @Test fun selectedPawnGunBoxOnly() {
        val screen=tabs+listOf(
            line("PAWN & GUN - PORT GELLHORN",825,280,300,22),
            line("Ammu-Nation distributor that stocks",827,321,308,21),
            line("guns, mods, ammo, and equipment.",827,346,310,21),
            line("INVENTORY",826,384,130),line("STANDARD",1070,384,115))
        assertTrue(GtSelectedMapPanel.isMap(screen,1536,690))
        val panel=GtSelectedMapPanel.panels(screen,1536,690).first()
        assertEquals("right",panel.slot)
        assertEquals("PAWN & GUN - PORT GELLHORN",panel.title)
        assertEquals("Ammu-Nation distributor that stocks guns, mods, ammo, and equipment.",panel.body)
        assertEquals(2,panel.rows)
    }
    @Test fun titleRemainsReadableWhenTranslatedBodyCoversEnglish() {
        val rows=tabs+listOf(line("NINE1NINE",826,285,160),
            line("FEATURES",826,405,115))
        val panel=GtSelectedMapPanel.panels(rows,1536,690).first()
        assertEquals("NINE1NINE",panel.title)
        assertEquals("",panel.body)
    }
    @Test fun unrelatedMapNamesDoNotChangeSelectedBoxIdentity() {
        val one=GtSelectedMapPanel.panels(tabs+listOf(
            line("RIDEOUT CUSTOMS",826,250,250),
            line("Mod shop known for custom rims",826,297,310)),1536,690)
        val two=GtSelectedMapPanel.panels(tabs+listOf(
            line("RIDEOUT CUSTOMS",826,250,250),
            line("Mod shop known for custom rims",826,297,310),
            line("Catalan Island",1260,400)),1536,690)
        assertEquals(one.first().identity,two.first().identity)
    }
    @Test fun gameplayWithoutMapDoesNotCreateBoxOverlay() {
        assertFalse(GtSelectedMapPanel.isMap(
            listOf(line("STEAL A VEHICLE",730,530)),1536,690))
    }
}
''',encoding='utf8')

v=build.read_text(encoding='utf8')
v,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261214',v,count=1)
if n!=1:raise RuntimeError('versionCode missing')
v,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-4.1-SelectedMapPanels"',v,count=1)
if n!=1:raise RuntimeError('versionName missing')
build.write_text(v,encoding='utf8')
print('GameLingoPro 4.1: only selected map information cards, independent translation; cleanup on title change')
