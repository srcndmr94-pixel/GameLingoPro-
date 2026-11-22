#!/usr/bin/env python3
"""Apply locally validated GameLingoPro 5.4 subtitle-priority patch."""
from pathlib import Path
import base64,zlib
p=Path(__file__).with_name("gt_v54_subtitle_priority.zlib.b64")
source=zlib.decompress(base64.urlsafe_b64decode(p.read_text(encoding="ascii").strip()))
exec(compile(source,str(p)+".py","exec"))
