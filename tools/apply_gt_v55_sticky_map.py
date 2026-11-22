#!/usr/bin/env python3
"""Apply the local-tested GameLingoPro 5.5 sticky map overlay patch."""
from pathlib import Path
import base64,zlib,hashlib
payload=Path(__file__).with_name("gt_v55_sticky_map.zlib.b64")
raw=zlib.decompress(base64.urlsafe_b64decode(payload.read_text(encoding="ascii").strip()))
assert hashlib.sha256(raw).hexdigest()=="90e65ddbc8ad28e4c537514ce4ec6c8126ba171eac0c4e3090e56679e4d04f32"
exec(compile(raw, "gt_v55_sticky_map.py", "exec"))
