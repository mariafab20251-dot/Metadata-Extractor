"""Check noteCard structure for actual note IDs"""
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
# First page, first note
first_page = notes[0]
first_note = first_page[0]
note_card = first_note.get('noteCard', {})
print(f"noteCard type: {type(note_card).__name__}")
if isinstance(note_card, dict):
    print(f"noteCard keys: {list(note_card.keys())}")
    for k, v in note_card.items():
        if isinstance(v, dict):
            print(f"  {k}: dict keys={list(v.keys())[:15]}")
        elif isinstance(v, list):
            print(f"  {k}: list len={len(v)}")
            if v and isinstance(v[0], dict):
                print(f"    first item keys={list(v[0].keys())[:10]}")
            elif v and isinstance(v[0], str):
                print(f"    first item={v[0]}")
        else:
            try:
                val_str = str(v)[:100]
            except:
                val_str = "(encoding error)"
            print(f"  {k}={val_str}")

# Print a few noteCards more compactly
print("\n=== All notes in first page ===")
for item in first_page:
    nc = item.get('noteCard', {})
    if isinstance(nc, dict):
        # Try to find noteId/displayTitle
        note_id = None
        for key, val in nc.items():
            if isinstance(val, str) and len(val) == 24 and all(c in '0123456789abcdef' for c in val.lower()):
                note_id = val
                break
        display = nc.get('displayTitle', '')
        print(f"  idx={item.get('index')}, displayTitle={str(display)[:40] if display else '(none)'}, note_id={note_id}")
