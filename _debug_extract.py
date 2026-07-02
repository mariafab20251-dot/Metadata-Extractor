"""Debug WHY the HTML scraping doesn't extract videos"""
import re
import json
from pathlib import Path

html = Path("debug_xiaohongshu.html").read_text(encoding="utf-8")

# Check all extraction methods the scraper uses

# Method 1: __INITIAL_STATE__ regex
print("=== Method 1: __INITIAL_STATE__ ===")
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*(?:</script>|;)', html, re.DOTALL)
if state_match:
    print(f"Found match at pos {state_match.start()}")
    json_str = state_match.group(1)
    print(f"JSON string length: {len(json_str)}")
    try:
        data = json.loads(json_str)
        print(f"Top-level keys: {list(data.keys())}")

        # Navigate the structure
        if 'user' in data:
            print(f"user keys: {list(data['user'].keys())}")
            if 'notes' in data['user']:
                notes = data['user']['notes']
                print(f"user.notes: {len(notes)} items")
                for n in notes[:3]:
                    print(f"  note: {list(n.keys())[:10]}...")
                    print(f"  noteId: {n.get('noteId')}")
                    print(f"  xsecToken: {n.get('xsecToken')}")
                    print(f"  type: {n.get('type')}")
            if 'noteIds' in data['user']:
                print(f"user.noteIds: {len(data['user']['noteIds'])} items")
        if 'note' in data:
            print(f"note keys: {list(data['note'].keys())}")
        if 'noteDetailMap' in str(data.keys()):
            print("Has noteDetailMap somewhere")
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
else:
    print("NO MATCH for __INITIAL_STATE__")
    # Try alternative patterns
    state_match2 = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*)', html, re.DOTALL)
    if state_match2:
        print("Found with alt pattern (no ending)")
    else:
        print("Not found at all")

# Method 2: Regex extraction of noteId + xsecToken pairs
print("\n=== Method 2: Regex extraction ===")
note_pattern = r'"noteId"\s*:\s*"([a-f0-9]{24})"'
token_pattern = r'"xsecToken"\s*:\s*"([^"]+)"'

note_matches = [(m.group(1), m.start(), m.end()) for m in re.finditer(note_pattern, html)]
token_matches = [(m.group(1), m.start(), m.end()) for m in re.finditer(token_pattern, html)]

print(f"noteId matches: {len(note_matches)}")
print(f"xsecToken matches: {len(token_matches)}")

if note_matches:
    for nid, start, end in note_matches[:5]:
        # Find closest token within 500 chars
        found = None
        for token, t_start, t_end in token_matches:
            if start < t_start < start + 500:
                found = token
                break
        print(f"  noteId={nid}, has_token={found is not None}, token={found}")

# Method 3: Explore URL extraction
print("\n=== Method 3: Explore URLs ===")
explore_pattern = r'href="(/explore/[a-f0-9]+(?:\?[^"]*)?)"'
explore_matches = re.findall(explore_pattern, html)
print(f"Explore URL matches: {len(explore_matches)}")
for m in explore_matches[:5]:
    print(f"  {m}")

# Also check if there are any note IDs NOT in hex format
print("\n=== Additional checks ===")
# Xiaohongshu might use different ID formats now
all_note_ids = set(re.findall(r'noteId["\']?\s*[:=]\s*["\']([^"\']+)["\']', html))
print(f"All unique noteId values: {len(all_note_ids)}")
for nid in list(all_note_ids)[:10]:
    print(f"  '{nid}' (len={len(nid)})")
