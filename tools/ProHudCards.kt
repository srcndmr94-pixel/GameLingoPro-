package com.example.altyazi

import kotlin.math.abs
import kotlin.math.max

/** Pure geometry for left mission and right reward cards. No translation engine changes. */
internal data class ProHudText(
    val text:String, val left:Int, val top:Int, val right:Int, val bottom:Int
)
internal object ProHudCards {
    /** Right-bottom notifications sit below the normal dialogue crop. */
    fun rightBottom(x:Float,y:Float):Boolean =
        x>=.65f && x<=.99f && y>=.78f && y<=.985f

    fun validUiText(text:String):Boolean {
        val s=text.trim()
        if(s.length<4 || s.none(Char::isLetter))return false
        // Single-word signs in the world (e.g. "Uacks") are not mission cards.
        if(s.split(Regex("\\s+")).size==1 && s.length<11 &&
            s.none{it.isDigit()} && s.none{it in "?!:$"})return false
        return true
    }
    /** Adjacent OCR lines from the same panel become one anchored label. */
    fun group(lines:List<ProHudText>,width:Int,height:Int):List<ProHudText> {
        if(width<1 || height<1)return emptyList()
        val result=ArrayList<ProHudText>()
        for(line in lines.sortedWith(compareBy<ProHudText>{it.top}.thenBy{it.left})){
            val side=(line.left+line.right)/2>=width/2
            val match=result.indices.reversed().firstOrNull{i->
                val old=result[i]
                val oldSide=(old.left+old.right)/2>=width/2
                val gap=line.top-old.bottom
                val span=max(12,max(line.bottom-line.top,old.bottom-old.top)/2)
                val startNear=abs(line.left-old.left)<=width*.095f
                val overlap=minOf(line.right,old.right)-max(line.left,old.left)
                oldSide==side && gap>=-4 && gap<=span &&
                    (startNear || overlap>minOf(line.right-line.left,old.right-old.left)*.35f) &&
                    old.text.count{it=='\n'}<3
            }
            if(match==null)result.add(line)
            else{
                val old=result[match]
                result[match]=ProHudText(old.text+"\n"+line.text,
                    minOf(old.left,line.left),minOf(old.top,line.top),
                    maxOf(old.right,line.right),maxOf(old.bottom,line.bottom))
            }
        }
        return result.filter{validUiText(it.text)}
    }
}
