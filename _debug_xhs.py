"""Debug Xiaohongshu cookie loading and HTML response"""
import requests
from http.cookiejar import MozillaCookieJar
from pathlib import Path

cookies_file = Path("cookies.txt")
print(f"Cookies file exists: {cookies_file.exists()}")
print(f"Cookies file size: {cookies_file.stat().st_size if cookies_file.exists() else 0}")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})

if cookies_file.exists():
    try:
        jar = MozillaCookieJar(str(cookies_file))
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies = jar
        print(f"Loaded {len(jar)} cookies")
        for c in jar:
            print(f"  - {c.name} (domain={c.domain})")
    except Exception as e:
        print(f"Cookie load error: {e}")

url = "https://www.xiaohongshu.com/user/profile/68267b7f000000000d0091f5"
try:
    resp = session.get(url, timeout=30)
    print(f"\nStatus: {resp.status_code}")
    print(f"Content length: {len(resp.text)}")
    print(f"Final URL: {resp.url}")
    text = resp.text

    print(f"Has __INITIAL_STATE__: {'__INITIAL_STATE__' in text}")
    print(f"Has noteId: {text.count('noteId')}")
    print(f"Has xsecToken: {text.count('xsecToken')}")
    print(f"Has Cloudflare: {'cloudflare' in text.lower()}")
    print(f"Has captcha: {'captcha' in text.lower()}")

    # Save debug copy
    debug_file = Path("debug_xiaohongshu.html")
    debug_file.write_text(text, encoding="utf-8")
    print(f"\nSaved debug HTML to {debug_file.resolve()}")

    print("\n--- First 800 chars ---")
    print(text[:800])
except requests.exceptions.RequestException as e:
    print(f"\nRequest error: {e}")
except Exception as e:
    print(f"\nUnexpected error: {e}")
