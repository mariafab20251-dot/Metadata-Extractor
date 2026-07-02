"""Deeper investigation into Xiaohongshu page structure"""
import re
import json
from pathlib import Path

html = Path("debug_xiaohongshu.html").read_text(encoding="utf-8")

# Fix the __INITIAL_STATE__ regex to handle nested braces
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?)</script>', html, re.DOTALL)
if state_match:
    raw = state_match.group(1).strip()
    # Remove trailing semicolons
    raw = raw.rstrip(';').strip()
    print(f"Raw extract length: {len(raw)}")
    print(f"Last 50 chars: {raw[-50:]}")

    # Find properly balanced braces
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
    if end_pos > 0:
        json_str = raw[:end_pos]
        print(f"Balanced JSON length: {len(json_str)}")
        try:
            data = json.loads(json_str)
            print(f"Top-level keys: {list(data.keys())}")
            for k, v in data.items():
                if isinstance(v, dict):
                    print(f"  {k}: dict with keys {list(v.keys())[:10]}")
                elif isinstance(v, list):
                    print(f"  {k}: list with {len(v)} items")
                    if v:
                        first = v[0]
                        if isinstance(first, dict):
                            print(f"    first item keys: {list(first.keys())[:15]}")
                            # Check for note-related fields
                            for key in first.keys():
                                if 'note' in key.lower() or 'id' in key.lower():
                                    print(f"    -> potential note field: {key} = {first[key][:80] if isinstance(first[key], str) else first[key]}")
                else:
                    print(f"  {k}: {str(v)[:100]}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
    else:
        print("Could not find balanced braces!")

# Search for ANY pattern that looks like video/note IDs in the page
print("\n=== Searching for non-standard ID patterns ===")
# What's in the page around xsecToken positions?
for m in re.finditer(r'"xsecToken"\s*:\s*"([^"]+)"', html):
    start = max(0, m.start() - 200)
    context = html[start:m.end()+50]
    print(f"\n--- xsecToken context (at {m.start()}) ---")
    print(context[:300])
    break  # Just first one

# Check if note data is in other script tags
script_count = len(re.findall(r'<script[^>]*>', html))
print(f"\nTotal script tags: {script_count}")

# Look for any JSON-like structures that might contain note data
print("\n=== Searching for ID patterns ===")
# Try to find 24-char hex strings (Xiaohongshu note IDs)
hex24 = re.findall(r'[a-f0-9]{24}', html)
print(f"24-char hex strings: {len(set(hex24))}")
for h in list(set(hex24))[:10]:
    print(f"  {h}")
