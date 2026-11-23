#!/usr/bin/env python3
"""V6 fast caption OCR with full-resolution retry and source-locked idiom fixes.
Apply after apply_v6_stability.py. This does not modify a signed Alpha.77 APK.
"""
from pathlib import Path
import shutil
root=Path(".")
service=root/"app/src/main/java/com/example/altyazi/CaptureService.kt"
src=root/"app/src/main/java/com/example/altyazi/v6"
tests=root/"app/src/test/java/com/example/altyazi/v6"
if not service.exists() or 'applicationId = "com.gamelingo.pro.v6stability"' not in (root/"app/build.gradle.kts").read_text():
    raise RuntimeError("Expected editable V6 stability source, not an unknown APK.")
src.mkdir(parents=True,exist_ok=True)
tests.mkdir(parents=True,exist_ok=True)
for name in ("V6RealtimePolicy.kt","V6DialogueRepair.kt"):
    shutil.copyfile(root/"v6/realtime"/name,src/name)
shutil.copyfile(root/"v6/realtime/V6RealtimePatchTest.kt",tests/"V6RealtimePatchTest.kt")
def replace(old,new):
    s=service.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1: raise RuntimeError("CaptureService anchor mismatch %d: %s"%(n,old[:85]))
    service.write_text(s.replace(old,new,1),encoding="utf-8")
replace('''    private suspend fun processSubtitle(full: Bitmap, epoch: Int) {''',
'''    private var v6RecentEmptyOcrReads = 0
    private suspend fun processSubtitle(full: Bitmap, epoch: Int) {''')
replace('''        if (band.height < 110) {
            val scaled = Bitmap.createScaledBitmap(band, band.width * 2, band.height * 2, true)
            if (scaled != band) band.recycle()
            band = scaled
        }''',
'''        // Fast pass on large subtitle strips, full-resolution on every fourth
        // consecutive empty OCR scan. Other HUD regions are not resized here.
        val v6Target = com.example.altyazi.v6.V6RealtimePolicy.targetWidth(
            band.width,band.height,v6RecentEmptyOcrReads)
        if (v6Target in 1 until band.width) {
            val scaledHeight = (band.height.toLong() * v6Target / band.width).toInt().coerceAtLeast(2)
            val scaled = Bitmap.createScaledBitmap(band,v6Target,scaledHeight,true)
            if (scaled !== band) band.recycle()
            band = scaled
        } else if (band.height < 110) {
            val scaled = Bitmap.createScaledBitmap(band,band.width * 2,band.height * 2,true)
            if (scaled !== band) band.recycle()
            band = scaled
        }''')
replace('''        ocrBandScale = if (band.height >= (bottom - top) * 2 - 1) 2f else 1f''',
'''        ocrBandScale = band.height.toFloat() / (bottom - top).coerceAtLeast(1)''')
replace('''        lastOcrRaw = text
        gtRealtimeLastOcrStartMs''',
'''        lastOcrRaw = text
        v6RecentEmptyOcrReads = com.example.altyazi.v6.V6RealtimePolicy.nextEmptyCount(
            v6RecentEmptyOcrReads,text)
        gtRealtimeLastOcrStartMs''')
replace('''                        val rendered = GtOriginalQualityGuard.polish(source, translated)''',
'''                        val rendered = com.example.altyazi.v6.V6DialogueRepair.polish(
                            source,GtOriginalQualityGuard.polish(source,translated))''')
replace('''            val prepared = GtOriginalInputGuard.prepare(raw)''',
'''            val prepared = GtOriginalInputGuard.prepare(
                com.example.altyazi.v6.V6DialogueRepair.repairInput(raw))''')
assert "gtOriginalDialogueDelegate.value.onOcrText" in service.read_text()
assert "PhoneBridgeService" in service.read_text()
print("V6 fast OCR + dialogue patch installed; device verification still required.")
