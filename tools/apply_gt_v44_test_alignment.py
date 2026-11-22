#!/usr/bin/env python3
"""Align older v4.2/v4.3 source-shape tests with v4.4's stricter implementation."""
from pathlib import Path
root=Path('.')
test=root/'app/src/test/java/com/example/altyazi'
def replace_once(path,old,new):
    s=path.read_text(encoding='utf-8')
    if s.count(old)!=1:raise RuntimeError(f"{path.name}: expected one obsolete assertion, found {s.count(old)}")
    path.write_text(s.replace(old,new,1),encoding='utf-8')
replace_once(test/'GtMapSelection42Test.kt',
    'service.contains("gtPanelTranslatedTitle[slot]!=gtPanelKeys[slot]")',
    'service.contains("gtPanelTranslatedTitle[slot]==gtPanelKeys[slot]")')
replace_once(test/'GtGameNoticeTest.kt',
    'service.contains("noticeProbe=gtNoticeMode")',
    'service.contains("noticeProbe=(gtNoticeMode || gtMapPanelMode)")')
print("Legacy tests now assert current visible-source safeguards")
