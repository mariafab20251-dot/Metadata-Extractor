"""Final check: find note IDs in any form"""
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

# Search ENTIRE JSON for any string that looks like a 24-char hex note ID
print("=== All 24-char hex values in JSON ===")
all_hex = set()
def find_hex(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                # Check if this value looks like a 24-char hex
                v_clean = v.strip().lower()
                if len(v_clean) == 24 and all(c in '0123456789abcdef' for c in v_clean):
                    all_hex.add(v_clean)
                # Also check if url contains hex
                if 'url' in k.lower() and len(v_clean) < 200:
                    for match in re.finditer(r'([a-f0-9]{24})', v_clean):
                        all_hex.add(match.group(1))
            elif isinstance(v, dict):
                find_hex(v, f"{path}.{k}")
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        find_hex(item, f"{path}.{k}[{i}]")
                    elif isinstance(item, str) and len(item) == 24 and all(c in '0123456789abcdef' for c in item.lower()):
                        all_hex.add(item.lower())

find_hex(data)
print(f"Total unique hex IDs: {len(all_hex)}")
for h in sorted(all_hex):
    print(f"  {h}")

# Search for any data attributes related to notes in HTML
print("\n=== Data attributes in HTML ===")
for attr in re.findall(r'data-note[-\w]*="[^"]*"', html):
    print(f"  {attr[:150]}")
for attr in re.findall(r'data-feed[-\w]*="[^"]*"', html):
    print(f"  {attr[:150]}")
for attr in re.findall(r'data-id[-\w]*="[^"]*"', html):
    print(f"  {attr[:150]}")

# Check for any other script tags with JSON data
print("\n=== Other script content ===")
for m in re.finditer(r'<script[^>]*id=["\'](\w+)["\'][^>]*>(.*?)</script>', html, re.DOTALL):
    sid = m.group(1)
    if sid not in ('__INITIAL_STATE__',):
        content = m.group(2)[:200]
        has_hex24 = bool(re.search(r'[a-f0-9]{24}', content))
        print(f"  id={sid}, len={len(m.group(2))}, has_hex24={has_hex24}")
