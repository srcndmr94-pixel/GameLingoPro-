#!/usr/bin/env python3
"""V6 capture repair. Apply after v6/tools/apply_v6_foundation.py.
Original GameTranslator v1.8.49 translation classes remain unchanged.
"""
from pathlib import Path
import shutil

root=Path(".")
src=root/"app/src/main/java/com/example/altyazi"
service=src/"CaptureService.kt"
v6src=src/"v6"
v6tests=root/"app/src/test/java/com/example/altyazi/v6"
v6src.mkdir(parents=True,exist_ok=True)
v6tests.mkdir(parents=True,exist_ok=True)
shutil.copyfile(root/"v6/capture/V6CaptureRecovery.kt",v6src/"V6CaptureRecovery.kt")
shutil.copyfile(root/"v6/capture/V6CaptureRecoveryTest.kt",v6tests/"V6CaptureRecoveryTest.kt")

def rep(old,new):
    s=service.read_text(encoding="utf-8")
    count=s.count(old)
    if count!=1: raise ValueError(f"CaptureService anchor mismatch ({count}): {old[:95]}")
    service.write_text(s.replace(old,new,1),encoding="utf-8")

rep('    private var readerHandler: Handler? = null', '''    private var readerHandler: Handler? = null
    @Volatile private var v6CapturedContentWidth = 0
    @Volatile private var v6CapturedContentHeight = 0
    private val v6ResizeGeneration = java.util.concurrent.atomic.AtomicInteger(0)
    @Volatile private var v6ProjectionStopped = false
    private val v6FrameEvents = java.util.concurrent.atomic.AtomicInteger(0)
    @Volatile private var v6LastImageEventAtMs = 0L
    @Volatile private var v6ImageEventsAtResize = 0''')

rep('''                    mp.registerCallback(object : MediaProjection.Callback() {
                        override fun onStop() {
                            stopEverything()
                        }
                    }, Handler(mainLooper))''', '''                    v6ProjectionStopped = false
                    mp.registerCallback(object : MediaProjection.Callback() {
                        override fun onStop() {
                            v6ProjectionStopped = true
                            log("V6 EKRAN İZNİ SONA ERDİ: Android paylaşımı durdurdu. Yeniden izin gerekli.")
                            stopEverything()
                        }
                        override fun onCapturedContentResize(width: Int, height: Int) {
                            if (width <= 0 || height <= 0 || v6ProjectionStopped) return
                            v6CapturedContentWidth = width
                            v6CapturedContentHeight = height
                            v6ResizeGeneration.incrementAndGet()
                        }
                    }, Handler(mainLooper))''')

rep('''        val scale = min(1f, (if (isTv) TARGET_WIDTH_TV else TARGET_WIDTH).toFloat() / max(sw, 1))
        val w = max(2, (sw * scale).toInt() / 2 * 2)
        val h = max(2, (sh * scale).toInt() / 2 * 2)''', '''        // The shared app may have different dimensions from the physical screen.
        // Keep physical screenWidth/screenHeight for overlay coordinates.
        val sourceW = v6CapturedContentWidth.takeIf { it > 0 } ?: sw
        val sourceH = v6CapturedContentHeight.takeIf { it > 0 } ?: sh
        val scale = min(1f, (if (isTv) TARGET_WIDTH_TV else TARGET_WIDTH).toFloat() / max(sourceW, 1))
        val w = max(2, (sourceW * scale).toInt() / 2 * 2)
        val h = max(2, (sourceH * scale).toInt() / 2 * 2)''')

rep('''            ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2)
        } catch (e: Throwable) {''', '''            ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2).also {
                it.setOnImageAvailableListener({ active ->
                    if (active === imageReader) {
                        v6FrameEvents.incrementAndGet()
                        v6LastImageEventAtMs = android.os.SystemClock.elapsedRealtime()
                    }
                }, readerHandler)
            }
        } catch (e: Throwable) {''')

rep('''        imageReader = null
        try {
            readerThread?.quitSafely()''', '''        imageReader = null
        v6CapturedContentWidth = 0
        v6CapturedContentHeight = 0
        v6ResizeGeneration.set(0)
        try {
            readerThread?.quitSafely()''')

rep('''            val yeni = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2)
            vd.setSurface(null)
            if (zorla) {
                // Boyutu değiştirip geri almak üreticiyi yeniden yapılandırıyor.
                vd.resize(maxOf(2, w - 2), maxOf(2, h - 2), dpi)
            }
            vd.resize(w, h, dpi)
            vd.setSurface(yeni.surface)
            val eski = imageReader
            imageReader = yeni
            try { eski?.close() } catch (_: Throwable) {}
            // Yeni okuyucu yeni boyutta kare verecek: eski tamponu bırak.
            frameBitmap = null
            bandImza = null
            true''', '''            val yeni = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2)
            val eski = imageReader
            try {
                // Resize existing VirtualDisplay; do not create another one.
                vd.setSurface(null)
                if (zorla) vd.resize(maxOf(2, w - 2), maxOf(2, h - 2), dpi)
                vd.resize(w, h, dpi)
                vd.setSurface(yeni.surface)
                yeni.setOnImageAvailableListener({ active ->
                    if (active === imageReader) {
                        v6FrameEvents.incrementAndGet()
                        v6LastImageEventAtMs = android.os.SystemClock.elapsedRealtime()
                    }
                }, readerHandler)
                imageReader = yeni
                try { eski?.close() } catch (_: Throwable) {}
                frameBitmap = null
                bandImza = null
                true
            } catch (inner: Throwable) {
                try { vd.resize(w, h, dpi); vd.setSurface(eski?.surface) } catch (_: Throwable) {}
                try { yeni.close() } catch (_: Throwable) {}
                throw inner
            }''')

rep('''        rotatedAtMs = 0L; framesSinceRotate = 0; reattachTries = 0; sonKurtarmaMs = 0L
        lastFrameMs = 0L; staleWarned = false''', '''        rotatedAtMs = 0L; framesSinceRotate = 0; reattachTries = 0; sonKurtarmaMs = 0L
        lastFrameMs = 0L; staleWarned = false
        v6ImageEventsAtResize = v6FrameEvents.get()''')

rep('''            if (!configureDisplay()) {
                stopEverything()
                return@launch
            }''', '''            if (!configureDisplay()) {
                stopEverything()
                return@launch
            }
            // First-start stalls need bounded recovery even without rotation.
            rotatedAtMs = android.os.SystemClock.elapsedRealtime()
            sonKurtarmaMs = rotatedAtMs
            framesSinceRotate = 0
            reattachTries = 0
            v6ImageEventsAtResize = v6FrameEvents.get()''')

rep('''            var lastScreen = screenWidth to screenHeight''', '''            var lastScreen = screenWidth to screenHeight
            var v6HandledResizeGeneration = v6ResizeGeneration.get()''')

rep('''                        reattachTries = 0
                        sonKurtarmaMs = rotatedAtMs''', '''                        reattachTries = 0
                        sonKurtarmaMs = rotatedAtMs
                        v6ImageEventsAtResize = v6FrameEvents.get()''')

rep('''                    // Tanı: başlangıçta hiç altyazı okunmadıysa nedenini kayda yaz (ilk 60 sn).
                    val nowMs = android.os.SystemClock.elapsedRealtime()''', '''                    // The Android content-resize callback may fire WITHOUT a
                    // physical screen orientation change (single-app sharing).
                    // All display reconfiguration stays on this one coroutine.
                    val newGeneration = v6ResizeGeneration.get()
                    if (newGeneration != v6HandledResizeGeneration &&
                        v6CapturedContentWidth > 0 && v6CapturedContentHeight > 0) {
                        v6HandledResizeGeneration = newGeneration
                        val oldW = captureWidth
                        val oldH = captureHeight
                        val ok = configureDisplay()
                        if (ok && (oldW != captureWidth || oldH != captureHeight)) {
                            rotatedAtMs = android.os.SystemClock.elapsedRealtime()
                            framesSinceRotate = 0
                            reattachTries = 0
                            sonKurtarmaMs = rotatedAtMs
                            v6ImageEventsAtResize = v6FrameEvents.get()
                            bandImza = null
                            lastOcrRaw = ""
                            log("V6 İÇERİK BOYUTU: " + v6CapturedContentWidth +
                                "x" + v6CapturedContentHeight +
                                " · yakalama " + captureWidth + "x" + captureHeight)
                        } else if (!ok) {
                            log("V6 İÇERİK BOYUTU YENİLENEMEDİ: yeniden paylaşım izni gerekebilir")
                        }
                    }
                    // Tanı: başlangıçta hiç altyazı okunmadıysa nedenini kayda yaz (ilk 60 sn).
                    val nowMs = android.os.SystemClock.elapsedRealtime()''')

rep('''                        log("ALTYAZI TARAMA: OCR " + diagCaptionOcrReads +''', '''                        log("V6 YAKALAMA: görüntü bildirimi " + v6FrameEvents.get() +
                            " · son bildirim " + v6LastImageEventAtMs +
                            " · boş kare " + diagNoFrame + " (OCR hatası değil)")
                        log("ALTYAZI TARAMA: OCR " + diagCaptionOcrReads +''')

rep('''                        if (rotatedAtMs > 0 && framesSinceRotate == 0 &&
                            reattachTries < KURTARMA_UST_SINIR &&
                            nowMs - sonKurtarmaMs > minOf(2500L * (reattachTries + 1), 30_000L)
                        ) {''', '''                        if (com.example.altyazi.v6.V6CaptureRecovery.shouldReattach(
                                !v6ProjectionStopped && projection != null,
                                rotatedAtMs, framesSinceRotate, reattachTries,
                                sonKurtarmaMs, nowMs)) {''')

rep('''                            if (reattachTries == KURTARMA_UST_SINIR) {
                                log("Kurtarma denemeleri durduruldu ($KURTARMA_UST_SINIR deneme, " +
                                    "~7 dk). Ekran yeniden dönünce baştan denenir.")
                            }''', '''                            if (com.example.altyazi.v6.V6CaptureRecovery.needsUserConsentMessage(
                                    reattachTries, framesSinceRotate)) {
                                log("V6 GÖRÜNTÜ DURDU: " +
                                    com.example.altyazi.v6.V6CaptureRecovery.noFrameExplanation(
                                        v6FrameEvents.get() - v6ImageEventsAtResize) +
                                    ". İki yüzey yenilemesi başarısız; DURDUR → BAŞLAT ile yeniden izin ver.")
                            }''')

assert (root/"app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt").is_file()
assert 'applicationId = "com.gamelingo.pro.v6test"' in (root/"app/build.gradle.kts").read_text()
print("V6 safe content resize + reader frame diagnostics + two-attempt recovery applied")
