#!/usr/bin/env python3
"""5.0: lower-right in-game alerts, character-message lifecycle and readable
source-fitted Turkish cards, without disabling captions or changing colors.
"""
from pathlib import Path
import sys,re
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
notice=src/"GtGameNotice.kt";cap=src/"CaptureService.kt";view=src/"GtExactOverlay.kt"
build=root/"app/build.gradle.kts";tests=root/"app/src/test/java/com/example/altyazi"
for p in (notice,cap,view,build):
    if not p.exists():raise RuntimeError("Missing 4.9 source "+str(p))
assert "gameEnglish" in notice.read_text()
assert "gtMapPanelMode" in cap.read_text()
assert "Color.rgb(255,203,86)" in view.read_text()
def once(file,before,after):
    s=file.read_text(encoding="utf8")
    n=s.count(before)
    if n!=1:raise RuntimeError(f"{file.name}: anchor {before[:75]!r} has count {n}")
    file.write_text(s.replace(before,after,1),encoding="utf8")

once(notice,
'''        return null
    }
}''',
'''        // Independent lower-right game notification region. Exclude icons,
        // numeric counters, TV/PS5 system shell and ordinary subtitles.
        val right=valid.filter { line ->
            val x=line.left.toFloat()/w
            val y=line.top.toFloat()/h
            val xr=line.right.toFloat()/w
            val t=line.text.trim()
            x in .57f.. .955f && y in .58f.. .955f &&
                xr<=.994f && t.length>=10 &&
                t.count(Char::isLetter)>=8 &&
                t.count(Char::isDigit)*3 < t.length &&
                !psShell.containsMatchIn(t)
        }
        for(first in right) {
            val rows=ArrayList<GtAllHud.Line>()
            rows.add(first)
            for(row in right.filter{it.top>first.top}.sortedBy{it.top}) {
                val previous=rows.last()
                val gap=row.top-previous.bottom
                val lineH=(previous.bottom-previous.top).coerceAtLeast(8)
                if(gap > lineH*1.7f || gap < -lineH/2)break
                if(abs(row.left-first.left)>w*.13f)break
                rows.add(row)
                if(rows.size==5)break
            }
            val body=rows.joinToString(" "){it.text.trim()}
            val cornerCue=Regex("""(?i)\b(?:objective|mission|new|reward|complete|
                available|collect|meet|drive|reach|find|go|take|delivered)\b""",
                RegexOption.COMMENTS)
            if(body.length>=25 && (gameEnglish(body) ||
                    cornerCue.containsMatchIn(body)) &&
                !psShell.containsMatchIn(body) &&
                (rows.size>=2 || body.any{it=='.'||it=='!'||it=='?'})) {
                return Notice("corner","Oyun bildirimi",body,
                    rows.minOf{it.left},rows.minOf{it.top},
                    rows.maxOf{it.right},rows.maxOf{it.bottom},rows.size)
            }
        }
        return null
    }
}''')

once(cap,
'''                    if(!gtMapPanelMode && !gtNoticeMode)processSubtitle(full)''',
'''                    // Game notifications are separate HUD labels; speech
                    // captions must keep translating while a message is shown.
                    if(!gtMapPanelMode)processSubtitle(full)''')
once(cap,
'''            shownSource=""
            translatingFor=""
            subtitleGeneration.invalidate()
            showSubtitle(null)
            log("OYUN BİLDİRİMİ ALGILANDI: "+notice.title.take(40))''',
'''            // Never cancel an ongoing spoken sentence for a right-corner
            // pop-up or an incoming character SMS.
            log("OYUN BİLDİRİMİ ALGILANDI: "+notice.title.take(40))''')

# The exact-rectangle style is retained, but the source glyphs receive a
# near-opaque single backdrop. Font fitting keeps text inside its box.
once(view,
'''                        setColor(if(card.lightNotice)Color.rgb(236,242,248)
                            else Color.rgb(17,24,38)) // opaque dark''',
'''                        setColor(if(card.lightNotice)Color.argb(248,236,242,248)
                            else Color.argb(248,17,24,38)) // masked translucent''')
once(view,
'''                val minPx=if(useRect)(initialFont*.57f).coerceAtLeast(dp(5).toFloat())
                    else dp(6).toFloat()
                tv.maxWidth=sourceW''',
'''                val minPx=if(useRect)(initialFont*.72f).coerceAtLeast(dp(8).toFloat())
                    else dp(6).toFloat()
                // Allow a little more of the original bordered card area for
                // Turkish (generally longer), but never paint outside screen.
                val displayW=if(useRect)(sourceW+dp(5)).coerceAtMost(w)
                    else sourceW
                val displayH=if(useRect) {
                    val grown=if(card.questHeading)sourceH+dp(3)
                        else (sourceH*1.17f).toInt()+dp(4)
                    grown.coerceAtMost((h-sourceY).coerceAtLeast(dp(12)))
                } else sourceH
                tv.maxWidth=displayW''')
once(view,
'''                    tv.measure(View.MeasureSpec.makeMeasureSpec(sourceW,
                        View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED))
                    if(tv.measuredHeight<=sourceH || fontPx<=minPx)break''',
'''                    tv.measure(View.MeasureSpec.makeMeasureSpec(displayW,
                        View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED))
                    if(tv.measuredHeight<=displayH || fontPx<=minPx)break''')
once(view,
'''                val measuredH=if(useRect)sourceH else tv.measuredHeight.coerceAtLeast(dp(14))
                val x=(if(useRect)sourceX else sourceX-dp(4))
                    .coerceIn(0,(w-sourceW).coerceAtLeast(0))''',
'''                val measuredH=if(useRect)displayH else tv.measuredHeight.coerceAtLeast(dp(14))
                val x=(if(useRect)sourceX-dp(2) else sourceX-dp(4))
                    .coerceIn(0,(w-displayW).coerceAtLeast(0))''')
once(view,
'''                lp.width=sourceW
                lp.height=if(useRect || card.gameNotice)sourceH''',
'''                lp.width=displayW
                lp.height=if(useRect || card.gameNotice)displayH''')

# Clear failed captures while a map or notice overlay is present, instead of
# leaving old translations on screen when MediaProjection stops producing frames.
once(cap,
'''                    if (full == null) {
                        if(noticeProbe && gtNoticeMode)drawGameNotice()
                        diagNoFrame++''',
'''                    if (full == null) {
                        if(noticeProbe && gtNoticeMode)drawGameNotice()
                        if(nowMs-lastFrameMs>1900L && lastFrameMs>0L) {
                            if(gtMapPanelMode) {
                                gtMapPanelMode=false
                                resetMapDetailPanels()
                            }
                            if(gtNoticeMode)resetGameNotice()
                        }
                        diagNoFrame++''')

tests.mkdir(parents=True,exist_ok=True)
(tests/"GtCornerNotice50Test.kt").write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtCornerNotice50Test {
    private fun row(t:String,x:Int,y:Int,w:Int=300,h:Int=24)=
        GtAllHud.Line(t,x,y,x+w,y+h)
    @Test fun findsEnglishRightBottomAlertWithoutNumbersOrIcons() {
        val rows=listOf(
            row("New objective available",1040,545,310),
            row("Meet your contact at the docks.",1040,574,330),
            row("+100",1400,590,60))
        val n=GtGameNotice.find(rows,1536,690)
        assertNotNull(n)
        assertEquals("corner",n!!.kind)
        assertTrue(n.body.contains("Meet your contact"))
        assertFalse(n.body.contains("+100"))
    }
    @Test fun neverTreatsPs5NativeAlertAsGameMessage() {
        assertNull(GtGameNotice.find(listOf(
            row("Güç",1040,530,250),
            row("PS5 sisteminiz kapatilmaya hazırlanıyor.",1035,563,410)),
            1536,690))
    }
    @Test fun preservesOriginalCharacterSenderAndInGameMessage() {
        val n=GtGameNotice.find(listOf(
            row("Moses",316,487,160),
            row("Clients stiffed me when it",220,539,350),
            row("was time to pay up. Trashed",219,571,350),
            row("my shop, too. They wanna...",222,603,350)),
            1536,690)
        assertEquals("Moses",n!!.title)
        assertFalse(n.body.startsWith("Moses"))
    }
    @Test fun phoneSpokenCaptionsStillRunDuringNotices() {
        val cap=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(cap.contains("if(!gtMapPanelMode)processSubtitle(full)"))
        assertTrue(cap.contains("processGameNotice(full,noticeProbe)"))
        assertFalse(cap.contains("gtQuestBoxesOnly"))
    }
    @Test fun sourceMaskUsesTranslucentBackdropAndReadableSizing() {
        val v=java.io.File("src/main/java/com/example/altyazi/GtExactOverlay.kt").readText()
        assertTrue(v.contains("Color.argb(248,17,24,38)"))
        assertTrue(v.contains("val displayW=if(useRect)"))
        assertTrue(v.contains("val displayH=if(useRect)"))
        assertTrue(v.contains("questHeading -> Color.rgb(255,203,86)"))
    }
}
''',encoding="utf8")

s=build.read_text(encoding="utf8")
s,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261222',s,count=1)
if n!=1:raise RuntimeError("versionCode not found")
s,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',
    r'\g<1>versionName = "GameLingoPro-5.0-MapNoticeStability"',s,count=1)
if n!=1:raise RuntimeError("versionName not found")
build.write_text(s,encoding="utf8")
print("5.0: lower-right English notifications, subtitle coexistence, mask and fitting")
