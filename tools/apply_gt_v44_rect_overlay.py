#!/usr/bin/env python3
"""Apply the GameLingoPro 4.4 in-place OCR geometry patch.

For review, decompress the adjacent gt_v44_rect_overlay.zlib.b64 file:
python3 -c "import base64,zlib,pathlib; p=pathlib.Path('tools/gt_v44_rect_overlay.zlib.b64'); print(zlib.decompress(base64.urlsafe_b64decode(p.read_text())).decode())"

This script intentionally fails if the generated 4.3 Kotlin source differs from
the verified baseline. It never writes an APK directly.
"""
import base64
import zlib
from pathlib import Path

data = Path(__file__).with_name("gt_v44_rect_overlay.zlib.b64").read_text(encoding="ascii").strip()
source = zlib.decompress(base64.urlsafe_b64decode(data)).decode("utf-8")
exec(compile(source, "apply_gt_v44_rect_overlay_source.py", "exec"), {"__name__": "__main__"})
