"""Deep dive: find actual note IDs"""
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

# Check cover.infoList and cover.traceId for each note
notes = data['user']['notes']
first_page = notes[0]
print("=== Full noteCard info ===")
for item in first_page[:12]:
    nc = item.get('noteCard', {})
    cover = nc.get('cover', {})
    xsec = item.get('xsecToken', '')
    print(f"\nidx={item.get('index')}:")
    print(f"  traceId={cover.get('traceId', '')}")
    info_list = cover.get('infoList', [])
    if info_list:
        for info in info_list:
            if isinstance(info, dict):
                url = info.get('url', '') or info.get('urlDefault', '')
                # Look for 24-char hex in any URL
                hex_matches = re.findall(r'([a-f0-9]{24})', url.lower())
                if hex_matches:
                    print(f"  info url hex: {hex_matches}")

# Also check ALL raw XHS note IDs in the page by looking for explore URLs
print("\n=== Raw explore URL patterns in HTML ===")
explore_patterns = re.findall(r'(?:explore|note)/([a-f0-9]{24})', html)
if explore_patterns:
    for pid in set(explore_patterns):
        print(f"  {pid}")

# Check if the page has any direct note links in <a> tags
link_pattern = r'<a[^>]*href="[^"]*(?:/explore/|/note/)([a-f0-9]{24})[^"]*"'
note_links = re.findall(link_pattern, html)
print(f"\nNote links in <a> tags: {len(note_links)}")
for nl in note_links[:5]:
    print(f"  {nl}")
