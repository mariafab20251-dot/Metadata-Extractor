from pathlib import Path
import re

html = Path('debug_xiaohongshu.html').read_text(encoding='utf-8')

print("=== Testing Xiaohongshu HTML Parsing ===\n")

# Test Method 1: __INITIAL_STATE__
print("Method 1: Looking for window.__INITIAL_STATE__")
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*(?:</script>|;)', html, re.DOTALL)
print(f"  First regex: {state_match is not None}")

if not state_match:
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*)', html, re.DOTALL)
    print(f"  Alternative regex: {state_match is not None}")

# Test Method 2: Extract /explore/ URLs
print("\nMethod 2: Extract explore URLs directly")
explore_pattern = r'href="(/explore/[a-f0-9]+)"'
explore_matches = re.findall(explore_pattern, html)
print(f"  Found {len(explore_matches)} total matches")
print(f"  Unique IDs: {len(set(explore_matches))}")
print(f"  Sample matches: {explore_matches[:5]}")

# Check what the scraper would do
base_url = 'https://www.xiaohongshu.com'
video_urls = []
seen_ids = set()
for match in explore_matches:
    note_id = match.split('/')[-1]
    if note_id not in seen_ids:
        seen_ids.add(note_id)
        video_url = f"{base_url}{match}"
        video_urls.append(video_url)
        if len(video_urls) >= 50:
            break

print(f"\n✅ Would extract {len(video_urls)} video URLs")
print(f"Sample URLs:")
for url in video_urls[:3]:
    print(f"  - {url}")
