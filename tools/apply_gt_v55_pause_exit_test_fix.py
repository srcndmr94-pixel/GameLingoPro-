#!/usr/bin/env python3
"""5.5 post-patch: count short PAUSED heading as a recognizable exit screen."""
from pathlib import Path
p=Path("app/src/main/java/com/example/altyazi/GtMapStay55.kt")
s=p.read_text(encoding="utf8")
a="row.text.length in 7..120"
b="row.text.length in 6..120"
assert s.count(a)==1, "Map presence evidence source differs"
p.write_text(s.replace(a,b,1),encoding="utf8")
print("5.5: explicit PAUSED/RESUME/SETTINGS/EXIT screen now qualifies as exit evidence")
