"""Try Xiaohongshu API endpoints for user notes"""
import requests, json, re, time
from http.cookiejar import MozillaCookieJar
from pathlib import Path

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://www.xiaohongshu.com',
    'Referer': 'https://www.xiaohongshu.com/',
    'Accept': 'application/json, text/plain, */*',
})

cookies_file = Path("cookies.txt")
if cookies_file.exists():
    jar = MozillaCookieJar(str(cookies_file))
    jar.load(ignore_discard=True, ignore_expires=True)
    session.cookies = jar

user_id = "68267b7f000000000d0091f5"

# Try different API endpoints
endpoints = [
    ("POST", f"https://edith.xiaohongshu.com/api/sns/web/v1/user/notes", {"user_id": user_id, "cursor": "", "num": 30, "image_formats": []}),
    ("GET", f"https://edith.xiaohongshu.com/api/sns/web/v1/user/notes?user_id={user_id}&num=30", None),
    ("POST", f"https://www.xiaohongshu.com/api/sns/web/v1/user/notes", {"user_id": user_id, "cursor": "", "num": 30}),
    ("GET", f"https://www.xiaohongshu.com/api/sns/web/v1/user/notes?user_id={user_id}&num=30", None),
    ("POST", f"https://edith.xiaohongshu.com/api/sns/web/v1/feed", {"num": 30, "cursor_score": "", "note_index": 0}),
    ("GET", f"https://www.xiaohongshu.com/api/sns/web/v1/search/notes?keyword=&page=1&page_size=30&sort=time&note_type=0", None),
]

for method, url, data in endpoints:
    try:
        if method == "POST":
            resp = session.post(url, json=data, timeout=15)
        else:
            resp = session.get(url, timeout=15)
        print(f"\n{method} {url}")
        print(f"  Status: {resp.status_code}, len={len(resp.text)}")
        if resp.status_code == 200:
            try:
                j = resp.json()
                if isinstance(j, dict):
                    keys = list(j.keys())[:10]
                    print(f"  Keys: {keys}")
                    if 'data' in j and isinstance(j['data'], dict):
                        dkeys = list(j['data'].keys())[:10]
                        print(f"  data keys: {dkeys}")
                        if 'notes' in j['data']:
                            print(f"  notes count: {len(j['data']['notes'])}")
                        if 'items' in j['data']:
                            print(f"  items count: {len(j['data']['items'])}")
                    if 'items' in j:
                        print(f"  items count: {len(j['items'])}")
                    if 'notes' in j:
                        print(f"  notes count: {len(j['notes'])}")
            except:
                print(f"  Response: {resp.text[:200]}")
        else:
            print(f"  Response: {resp.text[:200]}")
    except Exception as e:
        print(f"\n{method} {url}")
        print(f"  Error: {e}")

    time.sleep(1)
