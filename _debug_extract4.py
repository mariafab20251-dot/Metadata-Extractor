"""Extract notes from parsed Xiaohongshu data"""
import re
import json
from pathlib import Path

html = Path("debug_xiaohongshu.html").read_text(encoding="utf-8")

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

# Fix JS-specific patterns
json_str = re.sub(r':undefined', ':null', json_str)
json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

data = json.loads(json_str)

# 1. user.notes - THIS is what the scraper tries to access
user = data.get('user', {})
notes = user.get('notes')
print(f"user.notes type: {type(notes).__name__}")
if isinstance(notes, dict):
    print(f"user.notes keys: {list(notes.keys())}")
    for k, v in notes.items():
        print(f"  {k} ({type(v).__name__}): ", end="")
        if isinstance(v, dict):
            print(f"keys = {list(v.keys())[:10]}")
            # Look for noteId
            note_id = v.get('noteId') or v.get('id') or v.get('note_id')
            xsec = v.get('xsecToken') or v.get('xsec_token')
            print(f"    noteId={note_id}, xsecToken={xsec}")
        elif isinstance(v, list):
            print(f"len={len(v)}")
            if v and isinstance(v[0], dict):
                print(f"    first keys = {list(v[0].keys())[:15]}")
        else:
            print(str(v)[:100])
elif isinstance(notes, list):
    print(f"user.notes len: {len(notes)}")
    if notes and isinstance(notes[0], dict):
        print(f"first keys: {list(notes[0].keys())[:15]}")
        for item in notes[:5]:
            print(f"  noteId={item.get('noteId')}, xsecToken={item.get('xsecToken')}")

# 2. user.noteQueries
note_queries = user.get('noteQueries')
print(f"\nuser.noteQueries: {type(note_queries).__name__}")
if note_queries:
    print(note_queries)

# 3. user.userPageData - might contain note list
upd = user.get('userPageData', {})
print(f"\nuser.userPageData keys: {list(upd.keys())}")
for k, v in upd.items():
    print(f"  {k}: {type(v).__name__}", end="")
    if isinstance(v, dict):
        print(f" keys={list(v.keys())[:10]}")
        # Check recursively for note IDs
        def find_notes(obj, path="", depth=0):
            if depth > 5:
                return
            if isinstance(obj, dict):
                for sk, sv in obj.items():
                    if sk.lower() in ('noteid', 'id', 'note_id', 'xseckey', 'xsec_token', 'xsecToken'):
                        print(f"    {path}.{sk} = {sv}")
                    find_notes(sv, f"{path}.{sk}", depth+1)
            elif isinstance(obj, list):
                if obj and isinstance(obj[0], dict):
                    first_keys = list(obj[0].keys())[:5]
                    print(f" list[{len(obj)}] keys={first_keys}")
                    for i, item in enumerate(obj[:2]):
                        find_notes(item, f"{path}[{i}]", depth+1)
        find_notes(v, f"userPageData.{k}")
    elif isinstance(v, list):
        print(f" len={len(v)}")
        if v and isinstance(v[0], dict):
            print(f"  first keys: {list(v[0].keys())[:10]}")

# 4. note.noteDetailMap
nm = data.get('note', {}).get('noteDetailMap')
print(f"\nnote.noteDetailMap: {type(nm).__name__}")
if isinstance(nm, dict):
    print(f"keys: {list(nm.keys())[:10]}")
    for k, v in list(nm.items())[:3]:
        if isinstance(v, dict):
            print(f"  {k}: noteId={v.get('noteId')}, xsecToken={v.get('xsecToken')}")
