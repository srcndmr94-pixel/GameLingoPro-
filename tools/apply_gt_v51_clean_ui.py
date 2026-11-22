#!/usr/bin/env python3
"""Apply original GameLingoPro 5.1 clean UI patch to fully generated v5.0 source."""
from pathlib import Path
import base64,zlib,sys
p=Path(__file__).with_name("ui51_patch.zlib.b64")
s=p.read_text(encoding="ascii").strip()
patch=zlib.decompress(base64.urlsafe_b64decode(s))
assert b"GameLingoPro 5.1 native UI makeover" in patch
exec(compile(patch, "apply_gt_v51_clean_ui.py", "exec"))
