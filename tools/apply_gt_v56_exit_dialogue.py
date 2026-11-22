#!/usr/bin/env python3
"""GameLingoPro 5.6: sticky map exit via visual evidence + spoken idiom fixes.
Apply after 5.5, keeping original GameTranslator GTX -> ML Kit engines.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt";quality=src/"GtDialogueQuality.kt"
visual=src/"GtMapVisual56.kt";build=root/"app/build.gradle.kts"
assert "GameLingoPro-5.5-MapStay" in build.read_text(), "Apply 5.5 first"
def once(file,a,b):
    s=file.read_text(encoding="utf-8")
    if s.count(a)!=1:raise RuntimeError(f"{file.name}: anchor count {s.count(a)}: {a[:80]!r}")
    file.write_text(s.replace(a,b,1),encoding="utf-8")
visual.write_text("""package com.example.altyazi
import kotlin.math.abs
/** Pure Kotlin fingerprint while translation overlays are temporarily hidden. */
internal object GtMapVisual56 {
    private const val COLS=9
    private const val ROWS=7
    fun fingerprint(width:Int,height:Int,pixel:(Int,Int)->Int):IntArray {
        if(width<100 || height<100)return intArrayOf()
        val out=IntArray(COLS*ROWS)
        for(row in 0 until ROWS) for(col in 0 until COLS) {
            val x=(width*(.14+(col+.5)*.72/COLS)).toInt().coerceIn(0,width-1)
            val y=(height*(.16+(row+.5)*.68/ROWS)).toInt().coerceIn(0,height-1)
            out[row*COLS+col]=pixel(x,y)
        }
        return out
    }
    fun changed(reference:IntArray?,current:IntArray):Boolean {
        if(reference==null || reference.size!=COLS*ROWS || current.size!=reference.size)
            return false
        var changed=0
        var total=0L
        for(i in current.indices) {
            val a=reference[i]
            val b=current[i]
            val diff=abs((a shr 16 and 255)-(b shr 16 and 255)) +
                abs((a shr 8 and 255)-(b shr 8 and 255)) +
                abs((a and 255)-(b and 255))
            total+=diff
            if(diff>=129)changed++
        }
        return changed*100>=current.size*40 && total>=current.size*3L*42L
    }
}
""",encoding="utf-8")
once(cap,'    private var gtMapMisses=0','''    private var gtMapMisses=0
    private var gtMapVisualReference56:IntArray?=null''')
once(cap,'                        gtMapPanelMode=false\n                        gtNoticeMode=false','''                        gtMapPanelMode=false
                        gtMapVisualReference56=null
                        gtNoticeMode=false''')
once(cap,'    private fun resetMapDetailPanels() {\n        gtPanelJobs.values.forEach{it.cancel()}','''    private fun resetMapDetailPanels() {
        gtMapVisualReference56=null
        gtPanelJobs.values.forEach{it.cancel()}''')
once(cap,'''        val isMap=GtSelectedMapPanel.isMap(lines,width,height) ||''','''        val visual56=GtMapVisual56.fingerprint(full.width,full.height) { x,y ->
            full.getPixel(x,y)
        }
        val isMap=GtSelectedMapPanel.isMap(lines,width,height) ||''')
once(cap,'''            gtMapMisses++
            if(!GtMapStay55.shouldExitMap(prefs.mapKeepVisible,gtMapMisses,
                    GtMapStay55.differentScreenEvidence(lines,width,height))) {''','''            gtMapMisses++
            val differentScreen=GtMapStay55.differentScreenEvidence(lines,width,height)
            val visualExit=GtMapVisual56.changed(gtMapVisualReference56,visual56)
            if(!GtMapStay55.shouldExitMap(prefs.mapKeepVisible,gtMapMisses,
                    differentScreen || visualExit)) {''')
once(cap,'''            gtMapPanelMode=false
            gtMapMisses=0
            resetMapDetailPanels()
            log("HARİTA MENÜSÜ KAPANDI: görev çevirisi silindi")''','''            gtMapPanelMode=false
            gtMapMisses=0
            resetMapDetailPanels()
            log("HARİTA MENÜSÜ KAPANDI: görev çevirisi silindi"+
                if(visualExit)" · ekran değişimi" else " · OCR menü değişimi")''')
once(cap,'''            showSubtitle(null)
        }

        val obj=GtSelectedMapPanel.objective''','''            showSubtitle(null)
        }
        gtMapVisualReference56=visual56

        val obj=GtSelectedMapPanel.objective''')
once(cap,'''            if(gtObjectiveMissing>=2 && gtObjectiveSource.isNotBlank()) {''','''            if(gtObjectiveMissing>=2 && gtObjectiveSource.isNotBlank() &&
               !prefs.mapKeepVisible) {''')
once(cap,'''                       gtPanelSources[slot]==(gtPanelSources[slot]?:source) &&
                       !GtMapMotion50.newBody(gtPanelSources[slot]?:source,source)) {''','''                       gtPanelSources[slot]==source) {''')
once(quality,'''        var result=turkish
        if(english.contains("pound it"))''','''        var result=turkish
        if(Regex("""\\bokay\\b""").containsMatchIn(english) &&
           !Regex("""\\b(?:babe|baby|honey|darling|sweetheart|love)\\b""").containsMatchIn(english)) {
            result=result.replace(Regex("""(?iu)\\b(tamam|peki)[,!. ]+"""+
                """(aşkım|sevgilim|canım)\\b"""),"$1")
        }
        if(Regex("""\\blet me vent\\b""").containsMatchIn(english)) {
            result=result.replace(Regex("""(?iu)beni\\s+havalandırmam[aı]\\s+izin"""),
                "içimi dökmeme izin")
        }
        if(english.contains("pound it"))''')
s=build.read_text(encoding="utf-8")
assert s.count('versionCode = 20261229')==1
assert s.count('versionName = "GameLingoPro-5.5-MapStay"')==1
s=s.replace('versionCode = 20261229','versionCode = 20261230',1)
s=s.replace('versionName = "GameLingoPro-5.5-MapStay"','versionName = "GameLingoPro-5.6-MapExitQA"',1)
build.write_text(s,encoding="utf-8")
print("GameLingoPro 5.6: map visual exit, sticky objective and context-aware dialogue applied")
