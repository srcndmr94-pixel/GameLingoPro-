#!/usr/bin/env python3
"""V6 safe heap budget + bounded OCR worker retries; runs AFTER apply_v6_core.py.

This does not invent PS5 video input: the current release still needs an embedded
Chiaki/Remote Play stream and on-device validation.
"""
from pathlib import Path
import shutil

root = Path(".")
service = root / "app/src/main/java/com/example/altyazi/CaptureService.kt"
source = root / "app/src/main/java/com/example/altyazi/v6"
tests = root / "app/src/test/java/com/example/altyazi/v6"
shutil.copyfile(root / "v6/stability/V6StabilityPolicy.kt", source / "V6StabilityPolicy.kt")
shutil.copyfile(root / "v6/stability/V6StabilityPolicyTest.kt", tests / "V6StabilityPolicyTest.kt")

def replace_once(old, new):
    contents = service.read_text(encoding="utf-8")
    n = contents.count(old)
    if n != 1:
        raise AssertionError("V6 source anchor mismatch (found %d): %s" % (n, old[:110]))
    service.write_text(contents.replace(old,new,1),encoding="utf-8")

replace_once(
'''            val v6OcrWorker = launch {
                for (snapshot in v6Snapshots) {
                    try {''',
'''            val v6OcrWorker = launch {
                var v6ConsecutiveOcrErrors = 0
                for (snapshot in v6Snapshots) {
                    try {''')

replace_once(
'''                            v6Completed.incrementAndGet()
                        }
                    } catch (e: CancellationException) {''',
'''                            v6Completed.incrementAndGet()
                            v6ConsecutiveOcrErrors = 0
                        }
                    } catch (e: CancellationException) {''')

replace_once(
'''                    } catch (e: Throwable) {
                        CrashLog.note(this@CaptureService, "V6 OCR işçisi", e)
                    } finally {''',
'''                    } catch (e: Throwable) {
                        // Never silently loop on a broken ML Kit/native translation
                        // state, consuming the whole CPU and heap for hours.
                        if (e is VirtualMachineError || e is ThreadDeath) throw e
                        v6ConsecutiveOcrErrors++
                        try { CrashLog.note(this@CaptureService, "V6 OCR işçisi", e) }
                        catch (_: Exception) { android.util.Log.e("GameLingoV6", "OCR worker failed", e) }
                        kotlinx.coroutines.delay(
                            com.example.altyazi.v6.V6StabilityPolicy.errorBackoffMs(
                                v6ConsecutiveOcrErrors))
                    } finally {''')

replace_once(
'''                        val copy = try {
                            if (captured.isRecycled) null
                            else captured.copy(Bitmap.Config.ARGB_8888, false)
                        } catch (_: Throwable) { null }''',
'''                        val copy = try {
                            val heap = Runtime.getRuntime()
                            val headroom = heap.maxMemory() -
                                (heap.totalMemory() - heap.freeMemory())
                            if (captured.isRecycled ||
                                !com.example.altyazi.v6.V6StabilityPolicy.canCopyFrame(
                                    captured.width, captured.height, headroom)) null
                            else captured.copy(Bitmap.Config.ARGB_8888, false)
                        } catch (_: OutOfMemoryError) {
                            // A copy failure must not recursively trigger log/OCR
                            // allocations. Give the heap time to recover.
                            null
                        } catch (_: RuntimeException) { null }''')

assert 'V6StabilityPolicy.canCopyFrame' in service.read_text()
assert 'V6StabilityPolicy.errorBackoffMs' in service.read_text()
print('V6 stability patch: bounded bitmap copies and OCR failure backoff installed')
