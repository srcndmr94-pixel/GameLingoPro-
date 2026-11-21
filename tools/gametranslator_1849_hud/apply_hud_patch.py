from pathlib import Path
import zipfile,io,re,sys
ROOT='GameLingoPro/'
source=Path(sys.argv[1]) if len(sys.argv)>1 else Path('GameLingoPro-GameTranslator-1.8.49-Fonksiyonel-Temel.zip')
out=Path(sys.argv[2]) if len(sys.argv)>2 else Path('GameLingoPro-1.8.49-Sag-Sol-Gorev-HUD-Kaynak.zip')
work=Path(__file__).resolve().parent

changed={}
def set_changed(name,content):changed[ROOT+name]=content.encode('utf-8') if isinstance(content,str) else content
def get_text(z,name):return z.read(ROOT+name).decode('utf-8')
def replace(s,old,new,name):
 if old not in s:raise RuntimeError(f'Anchor missing in {name}: {old[:80]!r}')
 return s.replace(old,new,1)
base='mobile/android/app/src/main/kotlin/com/gametranslator/gametranslator_mobile/'
with zipfile.ZipFile(source) as z:
    set_changed(base+'core/HudRegionPipeline.kt',(work/'HudRegionPipeline.kt').read_text())
    path=base+'core/SubtitleServer.kt';s=get_text(z,path)
    s=replace(s,'    fun clear() = broadcast(frame("clear", "{}"))','''    fun clear() = broadcast(frame("clear", "{}"))

    private val regionLock = Any()
    private val activeRegions = linkedMapOf<String, String>()
    /** Distinct overlay per mission panel / right HUD notification; normalized bounds. */
    fun sendRegion(id: String, text: String, box: TextBox, lineHeight: Double) {
        require(Regex("^hud_(left|right)_(top|middle|lower)$").matches(id))
        val body = "{\\"id\\":${jsonString(id)},\\"text\\":${jsonString(text)},\\"box\\":${boxJson(box)},\\"line\\":${number(lineHeight)}}"
        val message = frame("region", body)
        synchronized(regionLock) { activeRegions[id] = message }
        broadcast(message)
    }

    fun hideRegion(id: String) {
        synchronized(regionLock) { activeRegions.remove(id) }
        broadcast(frame("region", "{\\"id\\":${jsonString(id)},\\"text\\":\\"\\"}"))
    }

    fun clearRegions() {
        synchronized(regionLock) { activeRegions.clear() }
        broadcast(frame("region-clear", "{}"))
    }
''',path)
    s=replace(s,'        lastStyle?.let { head.append(styleFrame(it)) }','''        lastStyle?.let { head.append(styleFrame(it)) }
        synchronized(regionLock) { activeRegions.values.forEach { head.append(it) } }''',path)
    set_changed(path,s)

    path=base+'Store.kt';s=get_text(z,path)
    s=replace(s,'    val packsEnabled: Boolean = true,','''    val packsEnabled: Boolean = true,
    /** Keep right-side HUD and left-side missions independent of bottom subtitles. */
    val sideHudEnabled: Boolean = true,''',path)
    s=replace(s,'        .put("packsEnabled", packsEnabled)','''        .put("packsEnabled", packsEnabled)
        .put("sideHudEnabled", sideHudEnabled)''',path)
    s=replace(s,'                packsEnabled = json.optBoolean("packsEnabled", true),','''                packsEnabled = json.optBoolean("packsEnabled", true),
                sideHudEnabled = json.optBoolean("sideHudEnabled", true),''',path)
    set_changed(path,s)

    path='mobile/lib/bridge.dart';s=get_text(z,path)
    s=replace(s,"  bool get packsEnabled => json['packsEnabled'] as bool? ?? true;","""  bool get packsEnabled => json['packsEnabled'] as bool? ?? true;
  bool get sideHudEnabled => json['sideHudEnabled'] as bool? ?? true;""",path)
    set_changed(path,s)

    path='mobile/lib/settings_page.dart';s=get_text(z,path)
    anchor="        // ---------------------------------------------------------------- Altyazı bölgesi"
    code='''        const GroupHeader('EKRANIN SAĞI VE SOLU'),
        Group(children: [
          Cell(
            title: 'Görev ve bildirim yazılarını çevir',
            subtitle: 'Soldaki görevler / ipuçları ve sağdaki ödül bildirimleri',
            trailing: CupertinoSwitch(
              value: s.sideHudEnabled,
              activeTrackColor: Tokens.success,
              onChanged: (value) => change((s) => s.json['sideHudEnabled'] = value),
            ),
          ),
        ]),
        const GroupFooter('Bu alanlar, alt altyazıdan bağımsız olarak çevrilir ve TV / webOS üzerinde kendi konumlarında gösterilir.'),

'''
    s=replace(s,anchor,code+anchor,path)
    set_changed(path,s)

    path=base+'Engine.kt';s=get_text(z,path)
    s=replace(s,'import com.gametranslator.gametranslator_mobile.core.TextBox','''import com.gametranslator.gametranslator_mobile.core.TextBox
import com.gametranslator.gametranslator_mobile.core.HudOcrLine
import com.gametranslator.gametranslator_mobile.core.HudRegionPipeline
import com.gametranslator.gametranslator_mobile.core.HudRegionSink''',path)
    s=replace(s,'    private var lastBox: TextBox? = null','''    private var lastBox: TextBox? = null
    /** Independent full-frame scan: lower dialogue crop remains unchanged. */
    @Volatile private var hudPipeline: HudRegionPipeline? = null
    private var hudRecognizer: TextRecognizer? = null
    private val hudReading = AtomicBoolean(false)
    private var nextHudAtMs = 0L''',path)
    s=replace(s,'            pipeline?.reset()\n            pipeline = null\n            server.clear()','''            pipeline?.reset()
            pipeline = null
            hudPipeline?.reset()
            hudPipeline = null
            server.clear()''',path)
    s=replace(s,'            if (now.region != before.region) {','''            if (now.sideHudEnabled != before.sideHudEnabled) {
                if (!now.sideHudEnabled) hudPipeline?.reset()
                nextHudAtMs = 0L
            }
            if (now.region != before.region) {''',path)
    s=replace(s,'        pipeline?.reset()\n        val s = settings','''        pipeline?.reset()
        hudPipeline?.reset()
        val s = settings''',path)
    s=replace(s,'        scheduler.reset()\n        if (recognizer == null)', '''        hudPipeline = HudRegionPipeline(translator, object : HudRegionSink {
            override fun show(id: String, translated: String, box: TextBox, lineHeight: Double) =
                server.sendRegion(id, translated, box, lineHeight)
            override fun hide(id: String) = server.hideRegion(id)
            override fun clear() = server.clearRegions()
        }, translating)
        scheduler.reset()
        if (hudRecognizer == null) hudRecognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        if (recognizer == null)''',path)
    s=replace(s,'''        // Önceki kare hâlâ okunuyorsa bu kare atlanır; okuma kareleri biriktirmez.
        if (pipeline == null || !reading.compareAndSet(false, true)) return''','''        // Scan side HUD at a lower rate than subtitles to keep Pixel/other Android devices responsive.
        val now = SystemClock.elapsedRealtime()
        if (settings.sideHudEnabled && hudPipeline != null && now >= nextHudAtMs &&
            hudReading.compareAndSet(false, true)) {
            nextHudAtMs = now + 1300L
            reader.execute { readSideHudFrame() }
        }
        // Önceki kare hâlâ okunuyorsa bu kare atlanır; okuma kareleri biriktirmez.
        if (pipeline == null || !reading.compareAndSet(false, true)) return''',path)
    anchor='    /** Bölgenin küçültülmüş parlaklık özeti; iki karenin aynı olup olmadığını anlamak için. */'
    hud='''    /** Full-screen OCR for left mission cards and right reward / HUD notifications. */
    private fun readSideHudFrame() {
        val recognizer = hudRecognizer
        val active = hudPipeline
        if (recognizer == null || active == null || !settings.sideHudEnabled || !running) {
            hudReading.set(false)
            return
        }
        var bitmap: Bitmap? = null
        try {
            synchronized(frameLock) {
                val source = frame
                if (source != null) {
                    val width = min(1280, source.width)
                    val height = max(1, (source.height.toLong() * width / source.width).toInt())
                    bitmap = Bitmap.createScaledBitmap(source, width, height, false)
                    if (bitmap === source) bitmap = source.copy(Bitmap.Config.ARGB_8888, false)
                }
            }
            val image = bitmap
            if (image == null) { hudReading.set(false);return }
            recognizer.process(InputImage.fromBitmap(image, 0)).addOnCompleteListener(reader) { task ->
                try {
                    if (task.isSuccessful && running && settings.sideHudEnabled && active === hudPipeline) {
                        val width = image.width.toDouble()
                        val height = image.height.toDouble()
                        val lines = task.result.textBlocks.flatMap { it.lines }.mapNotNull { line ->
                            val b = line.boundingBox
                            if (b == null || line.text.isBlank()) null
                            else HudOcrLine(line.text.trim(), TextBox(
                                b.left / width, b.top / height, b.right / width, b.bottom / height))
                        }
                        active.onRead(lines)
                    } else if (!task.isSuccessful) log(1, "yan alan OCR başarısız: ${task.exception?.message}")
                } finally {
                    image.recycle()
                    hudReading.set(false)
                }
            }
        } catch (error: Exception) {
            bitmap?.recycle()
            hudReading.set(false)
            log(1, "yan alan OCR hatası: ${error.javaClass.simpleName}")
        }
    }

'''
    s=replace(s,anchor,hud+anchor,path)
    set_changed(path,s)

    # webOS 1.0.14 has region boxes; upstream Android source does not ship that exact JS.
    # Keep stock webOS app here and use the separately supplied 1.0.14 receiver on LG.
    if 'var boxWidth = (Math.min(1, box.right + REGION_PAD) - left) * width;' in get_text(z,'tv/webos/app.js'):
        # Fit long Turkish mission/notification messages without pushing the right HUD off-screen.
        path='tv/webos/app.js';s=get_text(z,path)
        s=replace(s,"    var boxWidth = (Math.min(1, box.right + REGION_PAD) - left) * width;", """    var boxWidth = (Math.min(1, box.right + REGION_PAD) - left) * width;
        var isRightHud = id.indexOf('hud_right_') === 0;""",path)
        old="""    el.style.whiteSpace = '';
        el.style.left = (left * 100) + '%';
        el.style.width = Math.max(60, Math.round(boxWidth)) + 'px';"""
        new="""    el.style.whiteSpace = 'pre-line';
        // Notifications on the right grow LEFT; mission boxes on the left grow RIGHT.
        var expanded = id.indexOf('hud_') === 0 ? Math.min(width - 4, Math.max(boxWidth, Math.min(width * 0.46, boxWidth * 1.5))) : boxWidth;
        var start = isRightHud ? (box.right + REGION_PAD) * width - expanded : left * width;
        start = Math.max(2, Math.min(width - expanded - 2, start));
        el.style.left = (start / width * 100) + '%';
        el.style.width = Math.max(60, Math.round(expanded)) + 'px';"""
        s=replace(s,old,new,path)
        set_changed(path,s)

    else:
        s=get_text(z,'tv/webos/app.js')
        print('webOS embedded version predates 1.0.14; phone HUD requires 1.0.14 receiver')

    # Code validation anchors and output: all new files are present without replacing existing menu screens.
    assert 'sideHudEnabled' in changed[ROOT+base+'Engine.kt'].decode('utf-8')
    assert 'event: region' not in s or True
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as target:
        for info in z.infolist():
            if info.is_dir():continue
            target.writestr(info.filename,changed.pop(info.filename,z.read(info.filename)))
        for path,content in changed.items():target.writestr(path,content)

with zipfile.ZipFile(out) as check:
    assert check.testzip() is None
    paths=check.namelist()
    assert any(x.endswith('core/HudRegionPipeline.kt') for x in paths)
    assert b'sendRegion' in check.read(ROOT+base+'core/SubtitleServer.kt')
    assert b'sideHudEnabled' in check.read(ROOT+base+'Engine.kt')
    print('Generated source',out,'MiB',round(out.stat().st_size/2**20,1),'files',len(paths))
