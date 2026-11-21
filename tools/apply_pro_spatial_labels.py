from pathlib import Path

root=Path("app/src/main/java/com/example/altyazi")
p=root/"Overlay.kt"
q=root/"CaptureService.kt"
s=p.read_text(encoding="utf-8")
s=s.replace("data class Label(val text: String, val x: Int, val y: Int)",
'''data class Label(val text: String, val x: Int, val y: Int, val rightX: Int? = null)''',1)
a='''                val lp = tv.layoutParams as FrameLayout.LayoutParams
                lp.leftMargin = label.x.coerceAtLeast(0)
                lp.topMargin = label.y.coerceAtLeast(0)
                tv.layoutParams = lp
                tv.text = label.text
                tv.visibility = View.VISIBLE'''
b='''                val totalWidth = container.width.takeIf { it > 0 } ?: context.resources.displayMetrics.widthPixels
                val totalHeight = container.height.takeIf { it > 0 } ?: context.resources.displayMetrics.heightPixels
                val margin = dp(9)
                val maximum = (totalWidth * .53f).toInt().coerceAtLeast(dp(112))
                tv.maxWidth = maximum
                tv.text = label.text
                tv.measure(
                    View.MeasureSpec.makeMeasureSpec(maximum, View.MeasureSpec.AT_MOST),
                    View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
                )
                val width = tv.measuredWidth.coerceAtLeast(dp(35))
                val height = tv.measuredHeight.coerceAtLeast(dp(24))
                val rightSide = label.x >= totalWidth / 2
                val desiredLeft = if (rightSide) (label.rightX ?: label.x) - width else label.x
                val lp = tv.layoutParams as FrameLayout.LayoutParams
                lp.leftMargin = desiredLeft.coerceIn(margin, (totalWidth - width - margin).coerceAtLeast(margin))
                lp.topMargin = label.y.coerceIn(margin, (totalHeight - height - margin).coerceAtLeast(margin))
                lp.rightMargin = 0
                tv.layoutParams = lp
                tv.visibility = View.VISIBLE'''
if a not in s: raise SystemExit("Unsupported Overlay.kt version")
p.write_text(s.replace(a,b,1),encoding="utf-8")
c=q.read_text(encoding="utf-8")
a='''                val screenY = (box.bottom.toFloat() / small.height * screenHeight).toInt()
                found.add(Triple(raw, screenX, screenY))'''
b='''                val screenY = (box.top.toFloat() / small.height * screenHeight).toInt()
                val rightX = (box.right.toFloat() / small.width * screenWidth).toInt()
                found.add(Overlay.Label(raw, screenX, screenY, rightX))'''
if a not in c:raise SystemExit("Unsupported CaptureService.kt OCR coordinate flow")
c=c.replace("val found = ArrayList<Triple<String, Int, Int>>()","val found = ArrayList<Overlay.Label>()",1)
c=c.replace(a,b,1)
c=c.replace('val key = found.joinToString("|") { it.first }','val key = found.joinToString("|") { it.text }',1)
a='''        for ((text, x, y) in found) {
            val translated = translateMenuText(text) ?: continue
            labels.add(Overlay.Label(translated, x, y))'''
b='''        for (item in found) {
            val translated = translateMenuText(item.text) ?: continue
            labels.add(item.copy(text = translated))'''
if a not in c:raise SystemExit("Unsupported CaptureService.kt menu flow")
q.write_text(c.replace(a,b,1),encoding="utf-8")
print("Spatial labels now anchor to OCR boxes and clamp inside display")
