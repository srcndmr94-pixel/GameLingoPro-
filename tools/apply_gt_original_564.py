#!/usr/bin/env python3
"""GameLingoPro 5.6.4: faster OCR and translation scheduling.
Upstream GameTranslator v1.8.49 sources are copied as-is by earlier workflow step.
"""
from pathlib import Path
import shutil

root=Path('.')
src=root/'app/src/main/java/com/example/altyazi'
tests=root/'app/src/test/java/com/example/altyazi'
for name in ('GtLatestFirstExecutor.kt','GtRealtimeOcrPolicy.kt','GtLatencyMeter.kt'):
    shutil.copyfile(root/'tools/gt564'/name,src/name)
shutil.copyfile(root/'tools/gt564/GtRealtime564Test.kt',tests/'GtRealtime564Test.kt')

def replace(path, old, new):
    s=path.read_text(encoding='utf-8')
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'Expected 1 anchor, got {n} in {path}: {old[:90]}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

cap=src/'CaptureService.kt'
replace(cap,
"""        val retry = ProSubtitleAssembler.likelyContinued(text) ||
            (text.isBlank() && lastOcrRaw.isNotBlank())
        if (retry && ocrNow - lastLongOcrRetryAtMs >= 600L) {""",
"""        // Avoid expensive synchronous second OCR for empty / unrelated frames.
        // Preserve controlled vertical rescan for incomplete long subtitles.
        if (GtRealtimeOcrPolicy.shouldExpand(
                text, ocrNow - lastLongOcrRetryAtMs, gtMapPanelMode)) {""")
replace(cap,
"""        lastOcrRaw = text
        handleText(text)""",
"""        lastOcrRaw = text
        gtRealtimeLastOcrStartMs = ocrBasi
        gtRealtimeLastOcrDurationMs = sonOcrMs
        handleText(text)""")
replace(cap,
"""    @Volatile private var gtOriginalCurrentOcr = """"",
"""    @Volatile private var gtOriginalCurrentOcr = ""
    @Volatile private var gtRealtimeLastOcrStartMs = 0L
    @Volatile private var gtRealtimeLastOcrDurationMs = 0L""")
replace(cap,
"""                        publish(source, GtOriginalQualityGuard.polish(source, translated),
                            remember = false, tag = " · GT ORİJİNAL")""",
"""                        publish(source, GtOriginalQualityGuard.polish(source, translated),
                            remember = false, tag = " · GT ORİJİNAL")
                        gtOriginalDialogueDelegate.value.shown(source)?.let { metrics ->
                            if (prefs.diagnostics) log(
                                "GT GECİKME: OCR " + metrics.ocrMs + " ms · OCR→motor " +
                                metrics.waitBeforeTranslationMs + " ms (kuyruk " +
                                metrics.queueMs + " ms) · çeviri " + metrics.translationMs +
                                " ms · gösterim " + metrics.displayMs + " ms · toplam " +
                                metrics.totalMs + " ms · eski kuyruk atlandı " +
                                gtOriginalDialogueDelegate.value.droppedOldRequests() +
                                " · " + source.take(55))
                        }""")
replace(cap,
"""        gtOriginalCurrentOcr = usable
        gtOriginalDialogueDelegate.value.onOcrText(usable)""",
"""        gtOriginalCurrentOcr = usable
        gtOriginalDialogueDelegate.value.onOcrText(
            usable, gtRealtimeLastOcrStartMs, gtRealtimeLastOcrDurationMs)""")

pipeline=src/'GtOriginalDialoguePipeline.kt'
replace(pipeline,
"""    private val worker: ExecutorService = Executors.newSingleThreadExecutor { r ->
        Thread(r, "gt-original-translate")
    }""",
"""    private val queueWaitMs = ThreadLocal<Long>()
    private val worker = GtLatestFirstExecutor { waitMs -> queueWaitMs.set(waitMs) }
    private val latency = GtLatencyMeter { android.os.SystemClock.elapsedRealtime() }""")
replace(pipeline,
"""    private val speakerSafeTranslator = TextTranslator { input ->
        val (label, body) = GtOriginalInputGuard.splitSpeaker(input)
        if (label == null) originalTranslator.translate(body) else
            originalTranslator.translate(body)?.let { "$label: $it" }
    }""",
"""    private val speakerSafeTranslator = TextTranslator { input ->
        val (label, body) = GtOriginalInputGuard.splitSpeaker(input)
        latency.translationStarted(input, queueWaitMs.get() ?: 0L)
        try {
            if (label == null) originalTranslator.translate(body) else
                originalTranslator.translate(body)?.let { "$label: $it" }
        } finally {
            latency.translationEnded(input)
            queueWaitMs.remove()
        }
    }""")
replace(pipeline,
"""    init {
        originalPipeline.onPair = onPair
    }

    fun onOcrText(text: String) {
        originalPipeline.onRead(if (text.isBlank()) emptyList() else text.lines(), null)
    }""",
"""    init {
        originalPipeline.onPair = onPair
    }

    fun shown(source: String): GtLatencySample? = latency.displayed(source)
    fun droppedOldRequests() = worker.discardedOldRequests()

    fun onOcrText(text: String, ocrStartedMs: Long, ocrDurationMs: Long) {
        if (text.isNotBlank() && ocrStartedMs > 0L)
            latency.read(text, ocrStartedMs, ocrDurationMs)
        originalPipeline.onRead(if (text.isBlank()) emptyList() else text.lines(), null)
    }""")
replace(pipeline,"        worker.shutdownNow()","        worker.close()")
replace(pipeline,"import java.util.concurrent.Executors\nimport java.util.concurrent.ExecutorService\n","")

gradle=root/'app/build.gradle.kts'
replace(gradle,'applicationId = "com.gamelingo.pro.gt1849.fix563"',
        'applicationId = "com.gamelingo.pro.gt1849.fast564"')
replace(gradle,'versionName = "GameLingoPro-5.6.3-GTOriginalFix"',
        'versionName = "GameLingoPro-5.6.4-GTFast"')
replace(gradle,'versionCode = 20261234','versionCode = 20261235')
strings=root/'app/src/main/res/values/strings.xml'
replace(strings,
        '<string name="app_name">GameLingoPro GT Fix</string>',
        '<string name="app_name">GameLingoPro GT Fast</string>')
brand=tests/'GtBrandIdentity522Test.kt'
replace(brand,'GameLingoPro GT Fix</string>','GameLingoPro GT Fast</string>')
assert (src/'GtOriginalDialoguePipeline.kt').is_file()
assert (root/'app/src/main/java/com/gametranslator/gametranslator_mobile/core/SubtitlePipeline.kt').is_file()
print('Applied GameLingoPro 5.6.4 latency improvements; upstream GameTranslator unchanged.')
