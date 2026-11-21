#!/usr/bin/env python3
"""Fix actual GameLingoPro OCR HUD card layout without replacing its app or engines."""
from pathlib import Path
import re,sys,shutil
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('.')
src=root/'app/src/main/java/com/example/altyazi'
cap=src/'CaptureService.kt'
over=src/'Overlay.kt'
bld=root/'app/build.gradle.kts'
if not all(p.is_file() for p in (cap,over,bld)) or 'applicationId = "com.gamelingo.pro"' not in bld.read_text():
    raise SystemExit('Not original GameLingoPro: refusing to patch')
shutil.copyfile(Path(__file__).with_name('ProHudCards.kt'),src/'ProHudCards.kt')
def once(path,old,new):
    s=path.read_text(encoding='utf-8')
    if new in s:return
    if old not in s:raise RuntimeError('Unexpected '+path.name+' source near '+old[:100])
    path.write_text(s.replace(old,new,1),encoding='utf-8')
once(cap,'private const val MENU_EVERY = 4','private const val MENU_EVERY = 2')
once(cap,'private const val MAX_LABELS = 5','private const val MAX_LABELS = 10')
once(cap,'val found = ArrayList<Overlay.Label>()\n        val subtitleTop',
    'val rawFound = ArrayList<ProHudText>()\n        val subtitleTop')
once(cap,'''                val byPreferences = yanYaziAlaninda(relX, relY, subtitleTop)
                // When the user starts TV sharing, scan mission and HUD edges
                // even if the standalone menu-translation option is disabled.
                val tvSide = PhoneBridgeService.running && relY in .07f..minOf(.88f,subtitleTop) &&
                    (relX <= .43f || relX >= .57f)
                if (!byPreferences && !tvSide) continue''',
'''                val reward = ProHudCards.rightBottom(relX, relY)
                // Lower-right reward HUD must not be discarded with subtitles.
                val byPreferences = yanYaziAlaninda(relX, relY, subtitleTop) ||
                    (reward && (prefs.menuTranslate || prefs.yanSagAcik))
                val tvSide = PhoneBridgeService.running && (
                    (relY in .07f..minOf(.88f,subtitleTop) &&
                        (relX <= .43f || relX >= .57f)) || reward)
                if (!byPreferences && !tvSide) continue
                if (!prefs.menuModu && relX in .44f.. .56f) continue''')
once(cap,'''                found.add(Overlay.Label(raw, screenX, screenY, right))
                if (found.size >= MAX_LABELS) break''',
'''                val screenBottom = (box.bottom.toFloat() / small.height * screenHeight).toInt()
                rawFound.add(ProHudText(raw, screenX, screenY, right, screenBottom))
                if (rawFound.size >= MAX_LABELS * 3) break''')
once(cap,'''        val key = found.joinToString("|") {''',
'''        // Merge adjacent OCR lines from the SAME on-screen mission/notification.
        val found = ProHudCards.group(rawFound, screenWidth, screenHeight)
            .take(MAX_LABELS).map {
                Overlay.Label(it.text, it.left, it.top, it.right, it.bottom)
            }
        val key = found.joinToString("|") {''')
once(over,'    data class Label(val text: String, val x: Int, val y: Int, val rightX: Int? = null)',
'''    data class Label(
        val text: String, val x: Int, val y: Int,
        val rightX: Int? = null, val bottomY: Int? = null
    )''')
once(over,'''                val tv = makeText(13f, 205)
                container.addView(''',
'''                val tv = makeText(14f, 255).apply {
                    setTextColor(Color.WHITE)
                    setShadowLayer(0f, 0f, 0f, Color.TRANSPARENT)
                    setPadding(dp(11),dp(8),dp(11),dp(8))
                    background = GradientDrawable().apply {
                        cornerRadius=dp(8).toFloat()
                        setColor(Color.argb(249,25,29,43))
                        setStroke(dp(1),Color.argb(160,114,126,158))
                    }
                }
                container.addView(''')
once(over,'''                val maximum = (screenWidth * .47f).toInt().coerceAtLeast(dp(110))
                tv.maxWidth = maximum
                tv.text = label.text
                tv.measure(View.MeasureSpec.makeMeasureSpec(maximum, View.MeasureSpec.AT_MOST),
                    View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                val width = tv.measuredWidth.coerceAtLeast(dp(36))
                val height = tv.measuredHeight.coerceAtLeast(dp(24))
                val rightSide = label.x >= screenWidth / 2
                val desiredX = if (rightSide) (label.rightX ?: label.x) - width else label.x
                val lp = tv.layoutParams as FrameLayout.LayoutParams
                lp.leftMargin = desiredX.coerceIn(margin, (screenWidth - width - margin).coerceAtLeast(margin))
                lp.topMargin = label.y.coerceIn(margin, (screenHeight - height - margin).coerceAtLeast(margin))''',
'''                val rightSide = label.x >= screenWidth / 2
                val maximum = (screenWidth * (if (rightSide) .38f else .43f)).toInt()
                    .coerceAtLeast(dp(140))
                val sourceWidth = ((label.rightX ?: label.x) - label.x).coerceAtLeast(0)
                val sourceHeight = ((label.bottomY ?: label.y) - label.y).coerceAtLeast(0)
                tv.maxWidth = maximum
                tv.minWidth = (sourceWidth + dp(18)).coerceIn(dp(90), maximum)
                tv.minHeight = (sourceHeight + dp(12)).coerceAtLeast(dp(36))
                tv.text = label.text
                tv.measure(View.MeasureSpec.makeMeasureSpec(maximum, View.MeasureSpec.AT_MOST),
                    View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                val width = tv.measuredWidth.coerceAtLeast(tv.minWidth)
                val height = tv.measuredHeight.coerceAtLeast(tv.minHeight)
                val desiredX = if (rightSide) (label.rightX ?: label.x) - width + dp(4)
                    else label.x - dp(4)
                val lp = tv.layoutParams as FrameLayout.LayoutParams
                lp.leftMargin = desiredX.coerceIn(margin, (screenWidth - width - margin).coerceAtLeast(margin))
                lp.topMargin = (label.y - dp(5)).coerceIn(margin,
                    (screenHeight - height - margin).coerceAtLeast(margin))''')
# Higher versionCode is required for update to the existing Pro APK.
s=bld.read_text(encoding='utf-8')
s=re.sub(r'(?m)^(\s*)versionCode\s*=\s*\d+',r'\g<1>versionCode = 20261123',s,count=1)
s=re.sub(r'(?m)^(\s*)versionName\s*=\s*"[^"]+"',r'\g<1>versionName = "GameLingoPro-2.2-HUD-Cards"',s,count=1)
bld.write_text(s,encoding='utf-8')
web=root/'webos/index.html'
if web.exists():
    s=web.read_text(encoding='utf-8')
    s=s.replace('background:rgba(8,12,25,.88)','background:rgba(8,12,25,.98)')
    web.write_text(s,encoding='utf-8')
assert 'ProHudCards.group' in cap.read_text()
assert 'Color.argb(249,25,29,43)' in over.read_text()
print('GameLingoPro HUD cards and bottom-right reward fix installed')
