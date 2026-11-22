#!/usr/bin/env python3
"""Wire authentic, unmodified GameTranslator v1.8.49 Android translation sources into GameLingoPro.
Only the glue adapter and GameLingoPro's OCR/overlay glue are project-specific.
AGPL-3.0-or-later: retain upstream attributions and provide complete corresponding source.
"""
import pathlib, shutil, sys
upstream=pathlib.Path(sys.argv[1]).resolve()
project=pathlib.Path(sys.argv[2]).resolve()
original=upstream/'mobile/android/app/src/main/kotlin/com/gametranslator/gametranslator_mobile'
target=project/'app/src/main/java/com/gametranslator/gametranslator_mobile'
assert (original/'Engine.kt').exists(), "GameTranslator original Engine.kt is absent"
assert (original/'core/SubtitlePipeline.kt').exists(), "GameTranslator original pipeline is absent"
target.mkdir(parents=True,exist_ok=True)
# Copy the authentic Android translator and full upstream OCR/pipeline library unmodified.
shutil.copy2(original/'Translators.kt',target/'Translators.kt')
shutil.copytree(original/'core',target/'core',dirs_exist_ok=True)
# Preserving the exact original Engine.kt as documentation/source only; the Flutter/PSN
# Remote Play session portion cannot run inside GameLingo's Android MediaProjection app.
notice=project/'app/src/main/assets/GT-ORIGINAL-ENGINE-SOURCES.txt'
notice.parent.mkdir(exist_ok=True,parents=True)
notice.write_text("""GameTranslator v1.8.49 upstream sources, unmodified:
mobile/android/app/src/main/kotlin/com/gametranslator/gametranslator_mobile/Translators.kt
mobile/android/app/src/main/kotlin/com/gametranslator/gametranslator_mobile/core/*.kt
Source: https://gitlab.com/sefflex/GameTranslator/-/tree/v1.8.49
Licensed under GNU AGPL-3.0-or-later (see GameTranslator-LICENSE.txt).
GameLingo's MediaProjection capture and existing map OCR are retained.
Original Remote Play/Flutter/PSN session Engine.kt and libchiaki are not integrated.
""")
dest=project/'app/src/main/java/com/example/altyazi/GtOriginalDialoguePipeline.kt'
dest.write_text("""// SPDX-License-Identifier: AGPL-3.0-or-later
// Uses the authentic GameTranslator v1.8.49 Android sources, unmodified, not a simulated engine.
package com.example.altyazi

import com.gametranslator.gametranslator_mobile.FallbackTranslator
import com.gametranslator.gametranslator_mobile.GoogleGtxTranslator
import com.gametranslator.gametranslator_mobile.MlKitTranslator
import com.gametranslator.gametranslator_mobile.core.PrefixTranslator
import com.gametranslator.gametranslator_mobile.core.SubtitlePipeline
import com.gametranslator.gametranslator_mobile.core.SubtitleSink
import com.gametranslator.gametranslator_mobile.core.TextBox
import java.util.concurrent.Executors
import java.util.concurrent.ExecutorService

/**
 * GameLingo supplies screen OCR lines and renders the results.
 * All text matching, stability, cache, stale-result suppression,
 * and GTX -> ML Kit fallback are executed by original GameTranslator classes.
 */
internal class GtOriginalDialoguePipeline(
    onPair: (String, String) -> Unit,
    onClear: () -> Unit
) {
    private val worker: ExecutorService = Executors.newSingleThreadExecutor { r ->
        Thread(r, "gt-original-translate")
    }
    private val mlkit = MlKitTranslator("en", "tr")
    private val originalTranslator = PrefixTranslator(FallbackTranslator(
        GoogleGtxTranslator("en", "tr"), mlkit
    ))
    private val originalPipeline = SubtitlePipeline(originalTranslator, object : SubtitleSink {
        override fun show(text: String, durationMs: Int, box: TextBox?, replaces: Boolean) {
            // GameLingo renders at the English subtitle's position via onPair.
        }
        override fun clear() { onClear() }
    }, worker)

    init {
        originalPipeline.onPair = onPair
    }

    fun onOcrText(text: String) {
        originalPipeline.onRead(if (text.isBlank()) emptyList() else text.lines(), null)
    }

    fun shutdown() {
        originalPipeline.reset()
        worker.shutdownNow()
        mlkit.close()
    }
}
""")
service=project/'app/src/main/java/com/example/altyazi/CaptureService.kt'
s=service.read_text()
anchor='    private fun handleText(raw: String) {\n'
assert s.count(anchor)==1
bridge="""    // Original GameTranslator v1.8.49 subtitle pipeline, not GtNativeEngine port.
    @Volatile private var gtOriginalCurrentOcr = ""
    private val gtOriginalDialogue by lazy {
        GtOriginalDialoguePipeline(
            onPair = { source, translated ->
                scope.launch {
                    if (gtOriginalCurrentOcr.isNotBlank() &&
                        com.gametranslator.gametranslator_mobile.core.TextMatch.isSameSubtitle(
                            gtOriginalCurrentOcr, source)) {
                        translatingFor = source
                        log("OKUNAN · GT ORİJİNAL: " + source)
                        publish(source, translated, remember = false, tag = " · GT ORİJİNAL")
                    } else if (prefs.diagnostics) log("GT ORİJİNAL ESKİ CEVAP ATLANDI: " + source.take(60))
                }
            },
            onClear = {
                scope.launch {
                    if (gtOriginalCurrentOcr.isBlank() && shownSource.isNotEmpty() &&
                        android.os.SystemClock.elapsedRealtime() - shownAtMs >= okumaMs) {
                        shownSource = ""
                        translatingFor = ""
                        showSubtitle(null)
                    }
                }
            }
        )
    }

    private fun handleOriginalGameTranslatorText(raw: String) {
        val text = if (raw.isBlank() || GtDialogueQuality.stageOnly(raw)) "" else
            GtDialogueQuality.repairOcr(adiAyir(clean(raw)))
        val usable = if (text.isBlank() || GtObjectiveLine.matches(text) ||
            isOurOwnText(text) || altyaziDegil(text) || OcrQuality.bozukMu(text)) "" else text
        gtOriginalCurrentOcr = usable
        gtOriginalDialogue.onOcrText(usable)
        // Respect GameLingo's minimum readable subtitle duration after an empty OCR frame.
        if (usable.isBlank() && shownSource.isNotEmpty() &&
            android.os.SystemClock.elapsedRealtime() - shownAtMs >= okumaMs) {
            shownSource = ""
            translatingFor = ""
            showSubtitle(null)
        }
    }

"""
s=s.replace(anchor,bridge+anchor+"""        // Dialogue now runs through the unmodified upstream GameTranslator pipeline.
        // Map and notification OCR keep their separate GameLingo flow.
        handleOriginalGameTranslatorText(raw)
        return

""",1)
s=s.replace('prefs.googleCeviri -> "Google GTX → ML Kit (GameTranslator v1.8.49 uyarlaması)"',
'''prefs.googleCeviri -> "GameTranslator v1.8.49 ORİJİNAL pipeline (Google GTX → ML Kit)"''')
# Stop the original translator worker on all exits; do not retain a background thread.
stop='    private fun stopEverything() {\n'
assert s.count(stop)==1
s=s.replace(stop, stop+"""        if (this::gtOriginalDummy.isInitialized) { /* no-op */ }
""",1) if False else s
s=s.replace(stop,stop+"""        if (gtOriginalDialogueDelegate.isInitialized()) gtOriginalDialogue.shutdown()
""",1) if False else s
# Accessing by lazy in the stop method initializes it; use a separate delegate.
s=s.replace('    private val gtOriginalDialogue by lazy {','    private val gtOriginalDialogueDelegate = lazy {',1)
s=s.replace('        gtOriginalDialogue.onOcrText(usable)','        gtOriginalDialogueDelegate.value.onOcrText(usable)',1)
s=s.replace(stop,stop+"""        if (gtOriginalDialogueDelegate.isInitialized()) gtOriginalDialogueDelegate.value.shutdown()
""",1)
service.write_text(s)
main=project/'app/src/main/java/com/example/altyazi/MainActivity.kt'
m=main.read_text()
m=m.replace('cbGoogle.text="GameLingoPro · Google GTX → ML Kit (otomatik)"',
            'cbGoogle.text="GameLingoPro · GameTranslator v1.8.49 orijinal"')
main.write_text(m)
gradle=project/'app/build.gradle.kts'
g=gradle.read_text()
old='applicationId = "com.gamelingo.pro.stayfix"'
if old not in g:
    old='applicationId = "com.gamelingo.pro"'
assert g.count(old)==1
g=g.replace(old,'applicationId = "com.gamelingo.pro.gt1849"')
g=g.replace('versionName = "GameLingoPro-5.6.1-MapOCR-StayFix"',
'''versionName = "GameLingoPro-5.6.2-GTOriginal"''')
g=g.replace('versionCode = 20261232','versionCode = 20261233')
gradle.write_text(g)
strings=project/'app/src/main/res/values/strings.xml'
st=strings.read_text()
assert '<string name="app_name">' in st
import re
st=re.sub(r'<string name="app_name">[^<]*</string>',
          '<string name="app_name">GameLingoPro GT Original</string>',st,count=1)
strings.write_text(st)
brand=project/'app/src/test/java/com/example/altyazi/GtBrandIdentity522Test.kt'
bt=brand.read_text()
bt=bt.replace('GameLingoPro StayFix</string>', 'GameLingoPro GT Original</string>')
bt=bt.replace('GameLingoPro</string>', 'GameLingoPro GT Original</string>')
bt=bt.replace('GameLingoPro · Google GTX', 'GameLingoPro · GameTranslator v1.8.49')
brand.write_text(bt)
assert "GtOriginalDialoguePipeline" in service.read_text()
assert (target/'core/SubtitlePipeline.kt').read_bytes()==(original/'core/SubtitlePipeline.kt').read_bytes()
print("Authentic GameTranslator v1.8.49 Android translation and pipeline wired into GameLingo.")
