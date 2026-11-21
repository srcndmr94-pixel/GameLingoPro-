#!/usr/bin/env python3
"""GameLingoPro 4.5 — strictly selected map mission boxes ONLY.
No unboxed/game-world/weapon HUD, no SMS/tutorial floating labels, no bottom
objective overlay or spoken-caption overlay on the phone game screen.
Apply AFTER v4.4 to the original native GameLingoPro sources.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt"
build=root/"app/build.gradle.kts"
tests=root/"app/src/test/java/com/example/altyazi"
for f in [cap,build,src/"GtSelectedMapPanel.kt",src/"GtExactOverlay.kt"]:
    if not f.is_file():raise RuntimeError("Missing verified 4.4 source: "+str(f))
if 'applicationId = "com.gamelingo.pro"' not in build.read_text():
    raise RuntimeError("GameLingoPro package mismatch")
if "frameWidth=width,frameHeight=height,fitSourceBox=true" not in cap.read_text():
    raise RuntimeError("Original OCR rectangle mapping v4.4 not active")
def once(old,new):
    s=cap.read_text(encoding="utf8")
    n=s.count(old)
    if n!=1:raise RuntimeError(f"CaptureService.kt has {n} anchors, expected one: {old[:95]!r}")
    cap.write_text(s.replace(old,new,1),encoding="utf8")

once('''                    if(!gtMapPanelMode && !gtNoticeMode)processSubtitle(full)''',
'''                    // Phone game mode: map's selected bounded mission boxes ONLY.
                    // Do not render weapon menus, world text or dialogue subtitles.
                    if (isTv) processSubtitle(full)''')
once('''    private suspend fun processMenu(full: Bitmap, noticeProbe:Boolean=false) {
        if(!gtMapPanelMode && processGameNotice(full,noticeProbe))return''',
'''    private fun gtQuestBoxesOnly():Boolean=true
    private suspend fun processMenu(full: Bitmap, noticeProbe:Boolean=false) {
        if(gtQuestBoxesOnly()) {
            // Explicit whitelist: no general GtAllHud, menu labels or SMS.
            processMapDetailPanels(full,noticeProbe)
            return
        }
        if(!gtMapPanelMode && processGameNotice(full,noticeProbe))return''')
# Reduce flashing: source remains verified by periodic uncovered screenshots.
once('''                    val noticeProbe=(gtNoticeMode || gtMapPanelMode) && cycle%2L==0L''',
'''                    val noticeProbe=(gtNoticeMode || gtMapPanelMode) && cycle%4L==0L''')
once('''                        (gtMapPanelMode || gtNoticeMode || cycle % MENU_EVERY == 0L) &&''',
'''                        (gtMapPanelMode || cycle % MENU_EVERY == 0L) &&''')
# Nothing outside the original bordered left/right mission cards gets labels.
once('''        val instruction=gtObjectiveRect
        if(gtObjectiveText.isNotBlank() && instruction!=null)
            ready.add(instruction.copy(text=gtObjectiveText))
        overlay.setLabels(ready)''',
'''        // No unboxed bottom objective caption: only left/right quest cards.
        overlay.setLabels(ready)''')
s=cap.read_text(encoding="utf8")
start=s.find('''        val obj=GtSelectedMapPanel.objective(lines,width,height)''')
end=s.find('''        val visible=GtSelectedMapPanel.panels(lines,width,height)''',start)
if start<0 or end<start:raise RuntimeError("4.4 objective region not found")
cap.write_text(s[:start]+'''        // Ignore bottom prompts and unboxed HUD, as explicitly requested.
'''+s[end:],encoding="utf8")

once('''            gtPanelMisses[slot]=0
            val identity=panel.identity
            if(gtPanelKeys[slot]!=identity) {''',
'''            val identity=panel.identity
            if(panel.body.isBlank() && gtPanelKeys[slot]!=identity) {
                // Changed title with no confirmed paragraph: clear previous
                // translation immediately instead of sticking on new selection.
                synchronized(gtPanelStateLock) {
                    gtPanelJobs.remove(slot)?.cancel()
                    gtTitleJobs.remove(slot)?.cancel()
                    gtPanelKeys.remove(slot)
                    gtPanelText.remove(slot)
                    gtPanelRects.remove(slot)
                    gtPanelTranslatedTitle.remove(slot)
                    gtTitleText.remove(slot)
                    gtTitleRect.remove(slot)
                    gtTitleDone.remove(slot)
                    drawMapDetailPanels()
                }
                continue
            }
            gtPanelMisses[slot]=0
            if(gtPanelKeys[slot]!=identity) {''')
# Source OCR boxes vary 1–2px between frames. Freeze translation geometry
# for each actual selection; reset occurs in existing selection-change code.
once('''            if(panel.body.isNotBlank()) {
                gtPanelRects[slot]=Overlay.Label("",''',
'''            if(panel.body.isNotBlank() && gtPanelRects[slot]==null) {
                gtPanelRects[slot]=Overlay.Label("",''')
once('''            gtTitleRect[slot]=Overlay.Label("",panel.titleLeft,panel.titleTop,''',
'''            if(gtTitleRect[slot]==null)
                gtTitleRect[slot]=Overlay.Label("",panel.titleLeft,panel.titleTop,''')

tests.mkdir(parents=True,exist_ok=True)
(src/"GtMapBoxOnly.kt").write_text('''package com.example.altyazi
internal object GtMapBoxOnly {
    fun accepts(isMap:Boolean,hasBox:Boolean):Boolean=isMap && hasBox
    fun acceptsNew(body:String,old:String?,new:String):Boolean =
        body.isNotBlank() || (old!=null && old==new)
}
''',encoding="utf8")
(tests/"GtMapBoxOnly45Test.kt").write_text(r'''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
class GtMapBoxOnly45Test {
    @Test fun unboxedTextIsNotTranslated() {
        assertTrue(GtMapBoxOnly.accepts(true,true))
        assertFalse(GtMapBoxOnly.accepts(true,false))
        assertFalse(GtMapBoxOnly.accepts(false,true))
        assertFalse(GtMapBoxOnly.accepts(false,false))
        assertFalse(GtMapBoxOnly.acceptsNew("",null,"right|gun"))
        assertFalse(GtMapBoxOnly.acceptsNew("","right|motel","right|gun"))
        assertTrue(GtMapBoxOnly.acceptsNew("English details",null,"right|gun"))
    }
    @Test fun oldGeneralHudCannotRunInBoxOnlyMode() {
        val source=java.io.File("src/main/java/com/example/altyazi/CaptureService.kt").readText()
        assertTrue(source.contains("if(gtQuestBoxesOnly()) {\n            // Explicit whitelist"))
        assertTrue(source.contains("if (isTv) processSubtitle(full)"))
        assertTrue(source.contains("if(panel.body.isNotBlank() && gtPanelRects[slot]==null)"))
        assertTrue(source.contains("if(gtTitleRect[slot]==null)"))
        assertFalse(source.contains("val obj=GtSelectedMapPanel.objective(lines,width,height)"))
        assertFalse(source.contains("ready.add(instruction.copy(text=gtObjectiveText))"))
    }
}
''',encoding="utf8")
s=build.read_text(encoding="utf8")
s,n=re.subn(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261217',s,count=1)
if n!=1:raise RuntimeError("Missing versionCode")
s,n=re.subn(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',r'\g<1>versionName = "GameLingoPro-4.5-QuestBoxesOnly"',s,count=1)
if n!=1:raise RuntimeError("Missing versionName")
build.write_text(s,encoding="utf8")
print("4.5: boxed map quests only; all unboxed translations disabled; fixed layout; source-driven cleanup")
