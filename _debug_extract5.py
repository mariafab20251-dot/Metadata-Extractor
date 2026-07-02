"""Check what's in user.notes items"""
import re, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

html = Path("debug_xiaohongshu.html").read_text(encoding="utf-8")
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?)</script>', html, re.DOTALL)
raw = state_match.group(1).rstrip(';').strip()
brace_count, end_pos = 0, 0
for i, ch in enumerate(raw):
    if ch == '{': brace_count += 1
    elif ch == '}': brace_count -= 1
    if brace_count == 0: end_pos = i + 1; break
json_str = raw[:end_pos]
json_str = re.sub(r':undefined', ':null', json_str)
json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
data = json.loads(json_str)

notes = data['user']['notes']
print(f"Type: {type(notes).__name__}, len={len(notes)}")
for i, item in enumerate(notes):
    print(f"  [{i}] type={type(item).__name__}")
    if isinstance(item, list):
        for j, sub in enumerate(item):
            if isinstance(sub, dict):
                print(f"    [{j}] dict keys={list(sub.keys())[:10]}")
                print(f"         noteId={sub.get('noteId')}, xsecToken={sub.get('xsecToken')}, type={sub.get('type')}")
                for k, v in sub.items():
                    if not isinstance(v, (dict, list)):
                        try:
                            print(f"         {k}={str(v)[:100]}")
                        except:
                            print(f"         {k}=(cannot display)")
            else:
                print(f"    [{j}] {type(sub).__name__}")
    elif isinstance(item, dict):
        print(f"    keys={list(item.keys())}")
