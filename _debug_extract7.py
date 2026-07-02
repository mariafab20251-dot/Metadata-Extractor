"""Find note IDs from cover URLs or page context"""
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

# Check cover URLs for note ID patterns
notes = data['user']['notes']
first_page = notes[0]
print("=== Cover URLs ===")
for item in first_page[:5]:
    nc = item.get('noteCard', {})
    cover = nc.get('cover', {})
    url = cover.get('urlDefault', '') or cover.get('url', '')
    file_id = cover.get('fileId', '')
    idx = item.get('index')
    xsec = item.get('xsecToken', '')
    title = nc.get('displayTitle', '')
    print(f"\nidx={idx}:")
    print(f"  title={str(title)[:30]}")
    print(f"  fileId={file_id}")
    print(f"  url={str(url)[:120]}")
    print(f"  xsecToken={xsec}")

# Check if any 24-char hex string in URL looks like a note ID
print("\n=== Extracting hex IDs from URLs ===")
for item in first_page[:12]:
    nc = item.get('noteCard', {})
    cover = nc.get('cover', {})
    url = cover.get('urlDefault', '') or cover.get('url', '')
    # Find 24-char hex in URL
    hex_in_url = re.findall(r'([a-f0-9]{24})', url.lower())
    if hex_in_url:
        print(f"  idx={item.get('index')}: hex_ids={hex_in_url[:3]}")

# Try interacting with Xiaohongshu API
print("\n=== Testing XHS API ===")
import requests
from http.cookiejar import MozillaCookieJar

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})

cookies_file = Path("cookies.txt")
if cookies_file.exists():
    jar = MozillaCookieJar(str(cookies_file))
    jar.load(ignore_discard=True, ignore_expires=True)
    session.cookies = jar

# Try the notes API endpoint
user_id = '68267b7f000000000d0091f5'
api_url = f'https://edith.xiaohongshu.com/api/sns/web/v1/user/notes'
print(f"\nAPI: {api_url}")
try:
    resp = session.post(api_url, json={
        'user_id': user_id,
        'cursor': '',
        'num': 30
    }, headers={'Origin': 'https://www.xiaohongshu.com', 'Referer': 'https://www.xiaohongshu.com/'}, timeout=15)
    print(f"Status: {resp.status_code}, len={len(resp.text)}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"API error: {e}")
