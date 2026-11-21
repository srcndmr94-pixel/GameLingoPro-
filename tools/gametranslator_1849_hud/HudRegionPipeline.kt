// SPDX-License-Identifier: AGPL-3.0-only
package com.gametranslator.gametranslator_mobile.core

import java.util.concurrent.Executor
import kotlin.math.max
import kotlin.math.min

/** OCR result in whole-frame normalized coordinates, not the subtitle-only crop. */
data class HudOcrLine(val text: String, val box: TextBox)
data class HudArea(val id: String, val source: String, val box: TextBox, val lineHeight: Double)

/** Left side: missions / hints. Right side: rewards / notifications / HUD. */
object HudRegionDetector {
    private fun normalize(b: TextBox): TextBox? {
        if (!listOf(b.left, b.top, b.right, b.bottom).all { it.isFinite() }) return null
        val l=b.left.coerceIn(0.0,1.0); val t=b.top.coerceIn(0.0,1.0)
        val r=b.right.coerceIn(0.0,1.0); val bottom=b.bottom.coerceIn(0.0,1.0)
        return if(r-l>.004 && bottom-t>.004) TextBox(l,t,r,bottom) else null
    }
    fun detect(lines: List<HudOcrLine>): List<HudArea> {
        val groups=linkedMapOf<String,MutableList<HudOcrLine>>()
        for (line in lines) {
            val b=normalize(line.box) ?: continue
            val txt=line.text.trim().replace(Regex("\\s+")," ")
            if (txt.length<3 || txt.length>220 || txt.count { it.isLetter() } < 3) continue
            val centerX=(b.left+b.right)/2
            val centerY=(b.top+b.bottom)/2
            if(centerY>0.98 || centerY<0.035) continue
            if(centerY>0.82 && centerX>0.22 && centerX<0.78) continue // keep lower-centre dialogue out of HUD
            val side=when {
                centerX < 0.47 && b.left < 0.40 -> "left"
                centerX > 0.53 && b.right > 0.60 -> "right"
                else -> continue
            }
            val band=when {
                centerY<0.29 -> "top"
                centerY<0.57 -> "middle"
                else -> "lower"
            }
            groups.getOrPut("hud_${side}_${band}"){mutableListOf()}.add(HudOcrLine(txt,b))
        }
        return groups.mapNotNull { (id, items) ->
            val sorted=items.sortedWith(compareBy<HudOcrLine>{it.box.top}.thenBy{it.box.left}).take(7)
            val source=sorted.joinToString("\n"){it.text}.take(580)
            if(source.count{it.isLetter()}<3) return@mapNotNull null
            val box=TextBox(
                sorted.minOf {it.box.left},sorted.minOf {it.box.top},
                sorted.maxOf {it.box.right},sorted.maxOf {it.box.bottom})
            HudArea(id,source,box,sorted.map{it.box.bottom-it.box.top}.average().coerceIn(.01,.10))
        }
    }
}

interface HudRegionSink {
    fun show(id: String, translated: String, box: TextBox, lineHeight: Double)
    fun hide(id: String)
    fun clear()
}

/** One stable slot per side/band: keeps left missions independent of right-side rewards. */
class HudRegionPipeline(
    private val translator: TextTranslator,
    private val sink: HudRegionSink,
    private val executor: Executor,
) {
    private data class Slot(
        var source:String, var box:TextBox, var height:Double,
        var stable:Int=1, var missing:Int=0, var version:Long=0,
        var waiting:Boolean=false, var translated:String?=null,
    )
    private val lock=Any()
    private val slots=linkedMapOf<String,Slot>()
    private val cache=object:LinkedHashMap<String,String>(80,.75f,true) {
        override fun removeEldestEntry(eldest:MutableMap.MutableEntry<String,String>?)=size>140
    }
    private var epoch=0L

    fun onRead(lines:List<HudOcrLine>) {
        val detected=HudRegionDetector.detect(lines).associateBy{it.id}
        val toClear=mutableListOf<String>()
        val toShow=mutableListOf<Triple<HudArea,String,Double>>()
        val toTranslate=mutableListOf<Triple<String,String,Long>>()
        synchronized(lock) {
            for ((id,old) in slots.toMap()) {
                if(id !in detected && ++old.missing>=2) {slots.remove(id);toClear.add(id)}
            }
            for ((id,area) in detected) {
                var slot=slots[id]
                if(slot==null) {
                    slot=Slot(area.source,area.box,area.lineHeight,version=++epoch)
                    slots[id]=slot
                } else if(slot.source!=area.source) {
                    slot.source=area.source;slot.stable=1;slot.waiting=false;slot.translated=null;slot.version=++epoch
                } else slot.stable++
                slot.box=area.box;slot.height=area.lineHeight;slot.missing=0
                if(slot.stable<2) continue // do not translate one-frame OCR noise
                val translation=slot.translated ?: cache[area.source]
                if(translation!=null) {
                    slot.translated=translation
                    toShow.add(Triple(area,translation,area.lineHeight))
                } else if(!slot.waiting) {
                    slot.waiting=true
                    toTranslate.add(Triple(id,area.source,slot.version))
                }
            }
        }
        toClear.forEach { id -> synchronized(lock) { sent.remove(id) }; sink.hide(id) }
        // Re-send only when first translated / coordinates changed; do not flood SSE.
        for((area,translation,height) in toShow) showIfChanged(area.id,translation,area.box,height)
        for((id,source,version) in toTranslate) executor.execute {
            val translated=runCatching { translator.translate(source)?.trim() }.getOrNull()
            if(translated.isNullOrBlank() || translated.equals(source,ignoreCase=true)) {
                synchronized(lock) { slots[id]?.takeIf{it.version==version}?.waiting=false }
                return@execute
            }
            var current: Slot?=null
            synchronized(lock) {
                val slot=slots[id]
                if(slot!=null && slot.version==version && slot.source==source) {
                    slot.translated=translated;slot.waiting=false
                    cache[source]=translated
                    current=slot.copy()
                }
            }
            current?.let{showIfChanged(id,translated,it.box,it.height)}
        }
    }
    private val sent=mutableMapOf<String,Triple<String,TextBox,Double>>()
    private fun showIfChanged(id:String,text:String,box:TextBox,lineHeight:Double) {
        val shouldSend=synchronized(lock) {
            val previous=sent[id]
            val same=previous!=null && previous.first==text &&
                kotlin.math.abs(previous.second.left-box.left)<.012 &&
                kotlin.math.abs(previous.second.top-box.top)<.012 &&
                kotlin.math.abs(previous.second.right-box.right)<.012 &&
                kotlin.math.abs(previous.second.bottom-box.bottom)<.012
            if(!same)sent[id]=Triple(text,box,lineHeight)
            !same
        }
        if(shouldSend) sink.show(id,text,box,lineHeight)
    }
    fun reset() {
        synchronized(lock) {epoch++;slots.clear();sent.clear()}
        sink.clear()
    }
}
