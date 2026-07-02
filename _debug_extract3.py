"""Final debug: extract notes from Xiaohongshu page"""
import re
import json
from pathlib import Path

html = Path("debug_xiaohongshu.html").read_text(encoding="utf-8")

# 1. Fix __INITIAL_STATE__ JSON (replace JS undefined with null)
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?)</script>', html, re.DOTALL)
raw = state_match.group(1).rstrip(';').strip()

# Balance braces
brace_count = 0
end_pos = 0
for i, ch in enumerate(raw):
    if ch == '{':
        brace_count += 1
    elif ch == '}':
        brace_count -= 1
        if brace_count == 0:
            end_pos = i + 1
            break

json_str = raw[:end_pos]

# Fix JS-specific patterns that break JSON parsing
fixes = [
    (r':undefined', ':null'),
    (r',\s*([}\]])', r'\1'),  # trailing commas
    (r"'([^']+)'", r'"\1"'),  # single quotes (if any)
]
for pattern, replacement in fixes:
    json_str = re.sub(pattern, replacement, json_str)

try:
    data = json.loads(json_str)
    print(f"Top keys: {list(data.keys())}")
    # Look for note data
    for k, v in data.items():
        if isinstance(v, dict):
            nk = list(v.keys())
            # Check if any value contains note-like data
            if any(x in str(nk).lower() for x in ['note', 'video', 'feed', 'post', 'userNote', 'notes']):
                print(f"\n  {k}: dict keys = {nk}")
                # Check first few items if it's a dict of notes
                for subk, subv in list(v.items())[:5]:
                    if isinstance(subv, dict):
                        sv_keys = list(subv.keys())
                        print(f"    {subk}: keys = {sv_keys}")
                        if 'noteId' in sv_keys:
                            print(f"      noteId = {subv.get('noteId')}")
                            print(f"      xsecToken = {subv.get('xsecToken')}")
                        if 'displayTitle' in sv_keys and subv.get('displayTitle'):
                            print(f"      title = {subv.get('displayTitle')[:50]}")
                    elif isinstance(subv, list) and len(subv) > 0 and isinstance(subv[0], dict):
                        print(f"    {subk}: list[{len(subv)}], first keys = {list(subv[0].keys())[:10]}")
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            first_keys = list(v[0].keys())
            if any(x in str(first_keys).lower() for x in ['note', 'id', 'video', 'xsec']):
                print(f"\n  {k}: list[{len(v)}], keys = {first_keys}")
                for item in v[:3]:
                    item_keys = list(item.keys())
                    note_id = item.get('noteId') or item.get('id') or item.get('note_id')
                    xsec = item.get('xsecToken') or item.get('xsec_token')
                    print(f"    noteId={note_id}, xsecToken={xsec}, keys={item_keys[:10]}")
except json.JSONDecodeError as e:
    print(f"Parse error at {e.pos}: {json_str[max(0,e.pos-50):e.pos+50]}")

# 2. Try to find __NEXT_DATA__ or other data sources
print("\n=== Other data sources ===")
for script_match in re.finditer(r'<script[^>]*id="__NEXT_DATA__"[^>]*>', html):
    print("Found __NEXT_DATA__!")

for script_match in re.finditer(r'<script[^>]*id="__NUXT__"[^>]*>', html):
    print("Found __NUXT__!")

# 3. Check for API response data embedded in the page
if '"noteId":"' not in html:
    print("\nNo 'noteId' field found in page!")
    # What about just 'id' field?
    id_mentions = [(m.group(1), m.start()) for m in re.finditer(r'"(?:id|note_id|noteId|videoId)"\s*:\s*"([^"]+)"', html)]
    print(f"ID field mentions: {len(id_mentions)}")
    for val, pos in id_mentions[:10]:
        if val:  # non-empty
            print(f"  {val} at {pos}")
else:
    # Already found noteId is empty, but let's look at STRING noteId (not empty)
    nonempty = re.findall(r'"noteId"\s*:\s*"([^"]+)"', html)
    print(f"\nNon-empty noteId values: {len(nonempty)}")
    for nid in nonempty[:10]:
        print(f"  '{nid}'")
