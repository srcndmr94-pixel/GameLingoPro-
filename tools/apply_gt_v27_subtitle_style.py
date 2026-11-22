#!/usr/bin/env python3
"""GameTranslator mobile subtitle appearance for original native GameLingoPro.
Source reference: v1.8.49 mobile/lib/home_page.dart RegionPreview glass caption.
Do not replace any GameLingoPro app branding or spatial HUD functions.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else ".")
p=root/"app/src/main/java/com/example/altyazi/Overlay.kt"
s=p.read_text(encoding="utf8")
assert "class Overlay(" in s and "fun setSubtitle(" in s
assert s.count("import android.graphics.Color\n")==1
s=s.replace("import android.graphics.Color\n","import android.graphics.Color\nimport android.graphics.Typeface\nimport android.content.res.Configuration\n",1)
start=s.index("    private fun stiliUygula(t: TextView, boyutSp: Float) {")
end=s.index("\n    fun show() {",start)
s=s[:start]+'''    private fun stiliUygula(t: TextView, boyutSp: Float) {
        // Compact GameTranslator v1.8.49 glass caption, without clipping.
        val landscape = context.resources.configuration.orientation ==
            Configuration.ORIENTATION_LANDSCAPE
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, if (landscape) 15.5f else 16f)
        t.setTextColor(Color.WHITE)
        t.typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        t.gravity = Gravity.CENTER
        t.setShadowLayer(2f, 0f, 1f, Color.argb(180, 0, 0, 0))
        t.setPadding(dp(10), dp(5), dp(10), dp(5))
        t.maxWidth = (context.resources.displayMetrics.widthPixels * .88f)
            .toInt().coerceAtLeast(dp(180))
        t.maxLines = Int.MAX_VALUE
        t.ellipsize = null
        t.background = GradientDrawable().apply {
            cornerRadius = dp(10).toFloat()
            setColor(Color.argb(198, 0, 0, 0))
        }
    }
''' + s[end:]
# Previous translation line should not stay as an extra box above new captions.
old="oncekiYerlestir(previous, lp.topMargin, lp.leftMargin, lp.rightMargin)"
if old in s:s=s.replace(old,"oncekiGizle() // GameTranslator single visible caption",1)
else:
    pattern=r"oncekiYerlestir\(if \(context.resources.displayMetrics.widthPixels >\s*context.resources.displayMetrics.heightPixels\) null else previous,\s*lp.topMargin, lp.leftMargin, lp.rightMargin\)"
    s,n=re.subn(pattern,"oncekiGizle() // GameTranslator single visible caption",s,count=1)
    if n!=1:raise RuntimeError("Previous subtitle placement not found; inspect source")
# GameLingoPro 2.4 computes size on each new caption. Adjust THAT path too.
old='''            t.setTextSize(TypedValue.COMPLEX_UNIT_SP,
                (stil.boyutSp * scale).coerceAtLeast(11f))'''
new='''            val gtSize = if (context.resources.configuration.orientation ==
                Configuration.ORIENTATION_LANDSCAPE) 15.5f else 16f
            t.setTextSize(TypedValue.COMPLEX_UNIT_SP,
                (gtSize * scale).coerceAtLeast(11f))'''
if old not in s:raise RuntimeError("GameLingoPro 2.4 dynamic caption size not found")
s=s.replace(old,new,1)
assert s.count("t.maxLines = Int.MAX_VALUE")>=1
assert "Color.WHITE" in s and "Color.argb(198, 0, 0, 0)" in s
assert "oncekiGizle() // GameTranslator" in s
p.write_text(s,encoding="utf8")
print("GameTranslator 1.8.49 compact glass subtitle style installed: white, centered, soft black, rounded, no truncation")
