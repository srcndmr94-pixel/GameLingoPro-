#!/usr/bin/env python3
"""V6 architectural refactor: Conflated capture -> single OCR worker.
Unlike 5.6.x patches, the capture loop no longer awaits any ML Kit OCR call.
This targets acquisition starvation; it cannot eliminate ML Kit or network latency.
"""
from pathlib import Path
import shutil
root=Path(".")
service=root/"app/src/main/java/com/example/altyazi/CaptureService.kt"
src=root/"app/src/main/java/com/example/altyazi/v6"
tests=root/"app/src/test/java/com/example/altyazi/v6"
src.mkdir(parents=True,exist_ok=True)
tests.mkdir(parents=True,exist_ok=True)
shutil.copy(root/"v6/core/V6FramePolicy.kt",src/"V6FramePolicy.kt")
shutil.copy(root/"v6/core/V6FramePolicyTest.kt",tests/"V6FramePolicyTest.kt")

def rep(old,new):
 s=service.read_text(encoding="utf-8")
 count=s.count(old)
 if count!=1: raise AssertionError(f"Expected exactly one old code anchor, got {count}:\n{old[:120]}")
 service.write_text(s.replace(old,new,1),encoding="utf-8")

rep("import kotlinx.coroutines.CancellationException",
    "import kotlinx.coroutines.channels.Channel\nimport kotlinx.coroutines.CancellationException")

rep('''    private var scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)''',
'''    private var scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    // V6: capture only ever submits immutable bitmap snapshots.
    // A single OCR worker owns processing; newest unprocessed frame wins.
    // Conflation eliminates unbounded OCR backlog, and dropped images are recycled.
    private data class V6Snapshot(
        val bitmap: Bitmap, val epoch: Int, val capturedAtMs: Long
    )
    private val v6Epoch = java.util.concurrent.atomic.AtomicInteger(0)
    private val v6Dropped = java.util.concurrent.atomic.AtomicInteger(0)
    private val v6Submitted = java.util.concurrent.atomic.AtomicInteger(0)
    private val v6Completed = java.util.concurrent.atomic.AtomicInteger(0)
    private val v6Snapshots = Channel<V6Snapshot>(
        Channel.CONFLATED,
        onUndeliveredElement = { snapshot ->
            if (!snapshot.bitmap.isRecycled) snapshot.bitmap.recycle()
            v6Dropped.incrementAndGet()
        }
    )''')

rep('''            v6ImageEventsAtResize = v6FrameEvents.get()

            // Log the *active* engine''',
'''            v6ImageEventsAtResize = v6FrameEvents.get()
            // Independent OCR consumer: never holds the capture loop while ML Kit
            // or the original GameTranslator's network request is in progress.
            val v6OcrWorker = launch {
                for (snapshot in v6Snapshots) {
                    try {
                        val now = android.os.SystemClock.elapsedRealtime()
                        if (com.example.altyazi.v6.V6FramePolicy.isFresh(
                            snapshot.capturedAtMs, now, snapshot.epoch, v6Epoch.get()
                        )) {
                            processSubtitle(snapshot.bitmap, snapshot.epoch)
                            v6Completed.incrementAndGet()
                        }
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Throwable) {
                        CrashLog.note(this@CaptureService, "V6 OCR işçisi", e)
                    } finally {
                        if (!snapshot.bitmap.isRecycled) snapshot.bitmap.recycle()
                    }
                }
            }
            var v6LastSnapshotMs = 0L

            // Log the *active* engine''')

rep('''                        lastScreen = now
                        val ok = configureDisplay()''',
'''                        lastScreen = now
                        // Rotation invalidates in-flight OCR results from old pixels.
                        v6Epoch.incrementAndGet()
                        gtOriginalCurrentOcr = ""
                        val ok = configureDisplay()''')

rep('''                        val ok = configureDisplay()
                        if (ok && (oldW != captureWidth || oldH != captureHeight)) {''',
'''                        val ok = configureDisplay()
                        if (ok && (oldW != captureWidth || oldH != captureHeight)) {
                            v6Epoch.incrementAndGet()
                            gtOriginalCurrentOcr = ""''')

rep('''                        log("V6 YAKALAMA: görüntü bildirimi " + v6FrameEvents.get() +
                            " · son bildirim " + v6LastImageEventAtMs +
                            " · boş kare " + diagNoFrame + " (OCR hatası değil)")''',
'''                        log("V6 YAKALAMA: görüntü bildirimi " + v6FrameEvents.get() +
                            " · son bildirim " + v6LastImageEventAtMs +
                            " · boş kare " + diagNoFrame + " (OCR hatası değil)" +
                            " · kuyruğa alınan " + v6Submitted.get() +
                            " · OCR biten " + v6Completed.get() +
                            " · eski kare atlanan " + v6Dropped.get())''')

rep('''                    processSubtitle(full) // caption always has priority''',
'''                    // V6: immutable snapshot, never pass shared frameBitmap to
                    // asynchronous OCR. One pending frame at most; newer replaces
                    // older, keeping the main capture loop responsive to rotation,
                    // screen-share changes, and new game subtitles.
                    val snapshotNow = android.os.SystemClock.elapsedRealtime()
                    if (!MainActivity.visible &&
                        com.example.altyazi.v6.V6FramePolicy.shouldSnapshot(
                            snapshotNow, v6LastSnapshotMs,
                            !v6ProjectionStopped && projection != null)) {
                        val copy = try {
                            if (captured.isRecycled) null
                            else captured.copy(Bitmap.Config.ARGB_8888, false)
                        } catch (_: Throwable) { null }
                        if (copy != null) {
                            val sample = V6Snapshot(copy,v6Epoch.get(),snapshotNow)
                            if (v6Snapshots.trySend(sample).isSuccess) {
                                v6LastSnapshotMs = snapshotNow
                                v6Submitted.incrementAndGet()
                            } else if (!copy.isRecycled) {
                                copy.recycle()
                            }
                        }
                    }''')

rep('''    private suspend fun processSubtitle(full: Bitmap) {
        // Ekran yeniden kurulurken tampon serbest bırakılmış olabilir.''',
'''    private suspend fun processSubtitle(full: Bitmap, epoch: Int) {
        // Once new content/rotation is observed, never translate stale pixels.
        if (epoch != v6Epoch.get() || v6ProjectionStopped) return
        // Ekran yeniden kurulurken tampon serbest bırakılmış olabilir.''')

rep('''        sonOcrMs = android.os.SystemClock.elapsedRealtime() - ocrBasi
        band.recycle()
        if (text.isNotBlank()) diagText++''',
'''        sonOcrMs = android.os.SystemClock.elapsedRealtime() - ocrBasi
        band.recycle()
        // A full OCR can take over 1 second; don't publish a result from a
        // previous screen orientation or a MediaProjection that Android stopped.
        if (epoch != v6Epoch.get() || v6ProjectionStopped) return
        if (text.isNotBlank()) diagText++''')


# V6 OCR scheduling: independent cadence so menu scanning cannot starve subtitles.
rep('''            var v6LastSnapshotMs = 0L''',
'''            var v6LastSnapshotMs = 0L
            var v6LastMenuScanMs = 0L''')
rep('''                    if (!isTv &&
                        (gtMapPanelMode || gtNoticeMode || cycle % MENU_EVERY == 0L) &&
                        menuJob?.isActive != true) {''',
'''                    if (!isTv &&
                        com.example.altyazi.v6.V6FramePolicy.shouldProbeMenu(
                            nowMs, v6LastMenuScanMs,
                            gtMapPanelMode || gtNoticeMode, menuJob?.isActive == true) &&
                        (gtMapPanelMode || gtNoticeMode || cycle % MENU_EVERY == 0L)) {''')
rep('''                        if (copy != null) menuJob = scope.launch {''',
'''                        if (copy != null) {
                            v6LastMenuScanMs = nowMs
                            menuJob = scope.launch {''')
rep('''                            } finally {
                                copy.recycle()
                            }
                        }
                    }

                    cycle++''',
'''                            } finally {
                                copy.recycle()
                            }
                            }
                        }
                    }

                    cycle++''')

rep('''        if (gtOriginalDialogueDelegate.isInitialized()) gtOriginalDialogueDelegate.value.shutdown()
        running = false''',
'''        if (gtOriginalDialogueDelegate.isInitialized()) gtOriginalDialogueDelegate.value.shutdown()
        // Cancel the bounded channel; queued bitmaps are freed by its
        // onUndeliveredElement hook, and the worker's finally frees in-flight.
        v6Snapshots.cancel()
        running = false''')

assert "processSubtitle(full)" not in service.read_text()
assert "v6Snapshots.trySend(sample)" in service.read_text()
assert "v6Snapshots.cancel()" in service.read_text()
assert (root/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt").is_file()
print("V6 core producer/consumer decoupled with conflation, bitmap ownership and rotation epochs.")
