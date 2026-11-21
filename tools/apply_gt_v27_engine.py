#!/usr/bin/env python3
"""Integrate GameTranslator v1.8.49 Android Google GTX / ML Kit into native GameLingoPro.
Call AFTER GameLingoPro v2.6 patches; keep MediaProjection, UI shell, HUD and webOS.
GameTranslator source is AGPL-3.0-only; distribute original license and notices.
"""
from pathlib import Path
import sys,re,shutil
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
gt=Path(sys.argv[2] if len(sys.argv)>2 else "GameTranslator-v1.8.49")
src=root/"app/src/main/java/com/example/altyazi"
cap=src/"CaptureService.kt";main=src/"MainActivity.kt";build=root/"app/build.gradle.kts"
assert cap.exists() and main.exists() and 'applicationId = "com.gamelingo.pro"' in build.read_text()
base=gt/"mobile/android/app/src/main/kotlin/com/gametranslator/gametranslator_mobile"
assert (base/"Translators.kt").exists()
for relative in ("Translators.kt","core/SubtitleSegmenter.kt","core/OcrNoise.kt","core/Glossary.kt"):
    s=(base/relative).read_text(encoding="utf8")
    s=s.replace("package com.gametranslator.gametranslator_mobile.core","package com.example.altyazi.gtcore").replace("package com.gametranslator.gametranslator_mobile","package com.example.altyazi.gtcore")
    s=s.replace("import com.gametranslator.gametranslator_mobile.core.TextTranslator\n","")
    if relative=="Translators.kt":
        a=s.index("/** DeepL API");b=s.index("/** Cihaz üstünde çeviri",a);s=s[:a]+s[b:]
    if relative=="core/SubtitleSegmenter.kt":
        b=s.index("object PackLookup");a=s.rfind("\n/**",0,b);s=s[:a]
    dest=src/"gtcore"/Path(relative).name;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(s,encoding="utf8")
(src/"gtcore/TextTranslator.kt").write_text("package com.example.altyazi.gtcore\nfun interface TextTranslator { fun translate(text: String): String? }\n",encoding="utf8")
(src/"GtNativeEngine.kt").write_text(r'''// SPDX-License-Identifier: AGPL-3.0-only
// GameTranslator v1.8.49 Android source adapted into original GameLingoPro.
package com.example.altyazi
import com.example.altyazi.gtcore.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

internal object GtNativeEngine {
    private val google=GoogleGtxTranslator("en","tr")
    private val offline by lazy { MlKitTranslator("en","tr") }
    @Volatile private var prepared=false
    private val speaker=Regex("""^(?:\[[\p{L} .'-]{2,30}\]|[\p{Lu}][\p{L} .'-]{1,29}:)\s*""")
    fun normalize(raw:String):String {
        val text=OcrNoise.clean(raw).trim().ifEmpty { raw.trim() }
        return text.replace(Regex("""(?i)\bstandśa\b"""),"stands a")
            .replace(Regex("""(?i)\bstands aj\b"""),"stands a")
            .replace(Regex("""(?i)\bshutey\b"""),"shut eye")
            .replace(Regex("""(?i)\bYoune Master\b"""),"Young Master")
            .replace(Regex("""\s+""")," ").trim()
    }
    suspend fun translate(raw:String,unused:FastTranslate?):String? = translateWith(raw,
        { s -> withContext(Dispatchers.IO) { google.translate(s) } },
        { s -> withContext(Dispatchers.IO) {
            if(!prepared) synchronized(offline) { if(!prepared) prepared=offline.prepare(8) }
            if(prepared) offline.translate(s) else null
        } })
    suspend fun translateWith(raw:String,primary:suspend (String)->String?,backup:suspend (String)->String?):String? {
        val clean=normalize(raw)
        if(clean.isEmpty())return null
        // Keep entire OCR sentence together, even when split across display lines.
        val label=speaker.find(clean)?.value?.trim() ?: ""
        val body=if(label.isEmpty())clean else clean.drop(label.length).trim()
        if(body.isEmpty())return null
        val translated=primary(body)?.trim()?.takeIf{usable(body,it)}
            ?:backup(body)?.trim()?.takeIf{usable(body,it)} ?: return null
        return if(label.isEmpty())translated else "$label $translated"
    }
    internal fun usable(source:String,text:String):Boolean {
        if(text.isBlank() || source.equals(text,ignoreCase=true))return false
        if(source.length>45 && Regex("""(?i)\b(?:the|and|when|with|after|before|from|this|that|your)\b""")
            .findAll(text).count()>=3)return false
        return true
    }
}
''',encoding="utf8")
def patch(file,old,new):
    s=file.read_text(encoding="utf8")
    if s.count(old)!=1:raise RuntimeError("Expected one anchor in "+str(file)+": "+old[:55])
    file.write_text(s.replace(old,new,1),encoding="utf8")
patch(cap,"        val f = FastTranslate()\n        fast = f",'''        prefs.opusMtEnabled=false; prefs.firefoxMotoru=false
        prefs.deepLEnabled=false; prefs.googleCeviri=true
        prefs.mode=Prefs.MODE_INSTANT; prefs.ceviriBicimi=Prefs.BICIM_DENGELI
        val f = FastTranslate()
        fast = f''')
patch(cap,"        store = TranslationStore(this)\n        storeAi = TranslationStore(this, TranslationStore.AI)",'''        store=TranslationStore(this,"gt_native_v1849")
        storeAi=TranslationStore(this,"gt_native_v1849_ai")''')
# Remove the old translation body completely: unreachable legacy smart-casts
# fail Kotlin 2.x compilation and would keep unused engines in executable code.
source=cap.read_text(encoding="utf8")
first=source.index("    private suspend fun runTranslation(source: String, runId: Long) {")
after=source.index("    private suspend fun processMenu(full: Bitmap) {",first)
replacement='''    private suspend fun runTranslation(source: String, runId: Long) {
        val result = GtNativeEngine.translate(source, fast)
        if (result != null) {
            publishForRun(runId, source, result, remember = false, tag = " · GT/GTX")
        } else {
            log("GT: çeviri üretilemedi")
        }
    }

    // Side mission / inventory labels retain their existing GameLingoPro path.
    '''
cap.write_text(source[:first]+replacement+source[after:],encoding="utf8")
patch(cap,"    private suspend fun translateMenuText(text: String): String? {",'''    private suspend fun translateMenuText(text: String): String? {
        return GtNativeEngine.translate(text,fast)
''')
patch(cap,'                prefs.googleCeviri -> "Google → Firefox/yerel"',
              '                prefs.googleCeviri -> "GameTranslator v1.8.49: Google GTX → ML Kit"')
patch(main,"        cbSpeaker = findViewById(R.id.cbSpeaker)\n        cbFirefox = findViewById(R.id.cbFirefox)",'''        cbSpeaker = findViewById(R.id.cbSpeaker)
        prefs.opusMtEnabled=false; prefs.firefoxMotoru=false
        prefs.deepLEnabled=false; prefs.googleCeviri=true
        prefs.mode=Prefs.MODE_INSTANT; prefs.ceviriBicimi=Prefs.BICIM_DENGELI
        cbFirefox = findViewById(R.id.cbFirefox)''')
patch(main,"        cbDeepL = findViewById(R.id.cbDeepL)\n        etDeepLKey = findViewById(R.id.etDeepLKey)",'''        cbDeepL = findViewById(R.id.cbDeepL)
        etDeepLKey = findViewById(R.id.etDeepLKey)
        for(id in listOf(R.id.cbOpus,R.id.cbFirefox,R.id.cbDeepL,R.id.etDeepLKey,
            R.id.tvOpusStatus,R.id.btnOpusImport,R.id.btnModelCleanup,
            R.id.btnFirefoxIndir,R.id.rbBicimDogru,R.id.rbAi,R.id.rbHybrid))
            findViewById<android.view.View>(id)?.visibility=android.view.View.GONE
        findViewById<android.view.View>(R.id.boxModel)?.visibility=android.view.View.GONE
        cbGoogle.text="GameTranslator · Google GTX → ML Kit (otomatik)"
        cbGoogle.isChecked=true;cbGoogle.isEnabled=false''')
patch(main,'            if (tvCihaz) box.visibility = View.GONE\n            else modelSetup = ModelSetup(this) { pickModel.launch(arrayOf("*/*")) }.also { it.attach(box, 0) }',
'''            box.visibility=View.GONE
            modelSetup=null''')
patch(main,'        prefs.firefoxMotoru = cbFirefox.isChecked\n        prefs.googleCeviri = cbGoogle.isChecked\n        prefs.opusMtEnabled = cbOpus.isChecked && OpusModelPack.isInstalled(this)',
'''        prefs.firefoxMotoru=false; prefs.googleCeviri=true; prefs.opusMtEnabled=false''')
patch(main,'        prefs.deepLEnabled = cbDeepL.isChecked && DeepLCredentials.read(this).isNotBlank()',
'        prefs.deepLEnabled=false')
patch(main,'        prefs.ceviriBicimi = bicim','        prefs.ceviriBicimi=Prefs.BICIM_DENGELI')
patch(main,'        prefs.alwaysAi = cbAlwaysAi.isChecked','        prefs.alwaysAi=false; prefs.mode=Prefs.MODE_INSTANT')
b=build.read_text(encoding="utf8")
b=re.sub(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261128',b,count=1)
b=re.sub(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',r'\g<1>versionName = "GameLingoPro-2.7-GT-Core"',b,count=1)
if 'testImplementation("junit:junit:4.13.2")' not in b:b=b.replace('dependencies {','dependencies {\n    testImplementation("junit:junit:4.13.2")',1)
build.write_text(b,encoding="utf8")
assets=root/"app/src/main/assets";assets.mkdir(parents=True,exist_ok=True)
for name in ("LICENSE","NOTICE"):
    original=gt/name
    if original.exists():shutil.copyfile(original,assets/("GameTranslator-"+name+".txt"))
    elif name=="LICENSE":raise RuntimeError("GameTranslator AGPL license missing")
test=root/"app/src/test/java/com/example/altyazi/GtNativeEngineTest.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.example.altyazi
import org.junit.Assert.*
import org.junit.Test
import kotlinx.coroutines.runBlocking
class GtNativeEngineTest {
 @Test fun fixesObservedOCR() {
  val s=GtNativeEngine.normalize("At the center standśa Three-Eyed Puppet. The tightly shutey on its forehead.")
  assertTrue(s.contains("stands a Three-Eyed Puppet"));assertTrue(s.contains("shut eye"))
 }
 @Test fun preservesLongClauseAndFallsBack()=runBlocking {
  val input="At the center stands a Three-Eyed Puppet. The tightly shut eye on its forehead seems different."
  val sent=mutableListOf<String>()
  GtNativeEngine.translateWith(input,{sent.add(it);null},{"Ortada üç gözlü kukla duruyor."})
  assertEquals(1,sent.size);assertEquals(input,sent[0])
 }
}
''',encoding="utf8")
print("GameLingoPro original Android + GameTranslator v1.8.49 Google GTX / ML Kit integrated")
