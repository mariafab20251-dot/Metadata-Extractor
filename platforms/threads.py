import re, time, json
from pathlib import Path

import requests
import http.cookiejar


class ThreadsScraper:
    """Download Threads videos using Instagram API authentication.

    Threads posts are stored in Instagram's infrastructure (same media CDN).
    This scraper uses Instagram cookies to access the Instagram API and
    resolve the video URL from a Threads post code.

    Cookie files are checked from the legacy data/cookies.txt first, then
    the multi-account data/cookies/*.txt directory.
    """

    COOKIES_DIR = Path(__file__).parent.parent / "data" / "cookies"

    def __init__(self):
        self._cached_session = None
        self._cached_cookie_path = None

    # ── Cookie helpers ──────────────────────────────────────────

    @classmethod
    def _find_valid_cookie(cls):
        """Find a cookie file with a valid Instagram sessionid."""
        candidates = []
        legacy = Path(__file__).parent.parent / "data" / "cookies.txt"
        if legacy.exists():
            candidates.append(legacy)
        if cls.COOKIES_DIR.exists():
            for f in sorted(cls.COOKIES_DIR.glob("*.txt")):
                candidates.append(f)

        for path in candidates:
            try:
                cj = http.cookiejar.MozillaCookieJar(str(path))
                cj.load(ignore_discard=True, ignore_expires=True)
                for c in cj:
                    if c.name == "sessionid" and "instagram.com" in (c.domain or ""):
                        return path
            except Exception:
                continue
        return None

    # ── Session management ──────────────────────────────────────

    def _get_session(self):
        """Build a requests session with Instagram cookies for threads.net."""
        cookie_path = self._find_valid_cookie()
        if not cookie_path:
            raise ValueError(
                "No valid Instagram cookie found.\n"
                "Threads download requires an Instagram login.\n"
                "Save Instagram cookies to data/cookies/ or login via Settings."
            )

        # Re-use cached session if same cookie file
        if self._cached_session and self._cached_cookie_path == cookie_path:
            return self._cached_session, cookie_path

        s = requests.Session()
        cj = http.cookiejar.MozillaCookieJar(str(cookie_path))
        cj.load(ignore_discard=True, ignore_expires=True)
        for c in cj:
            if "instagram.com" in (c.domain or ""):
                s.cookies.set(c.name, c.value, domain=".threads.net", path="/")
                s.cookies.set(c.name, c.value, domain=".i.instagram.com", path="/")

        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })

        self._cached_session = s
        self._cached_cookie_path = cookie_path
        return s, cookie_path

    # ── URL parsing ────────────────────────────────────────────

    _SHORTCODE_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'

    def extract_video_id(self, url):
        """Extract the post code (video ID) from a Threads URL."""
        m = re.search(r'threads\.(?:com|net)/@[^/]+/post/([A-Za-z0-9_-]+)', url)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _shortcode_to_media_id(shortcode):
        """Decode an Instagram shortcode to its numeric media ID."""
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        mid = 0
        for c in shortcode:
            mid = mid * 64 + alphabet.index(c)
        return str(mid)

    # ── Metadata extraction ─────────────────────────────────────

    def get_post_metadata(self, url):
        """Fetch Threads post metadata.

        Returns: (post_code, caption_text, hashtags)
        """
        post_code = self.extract_video_id(url)
        if not post_code:
            return None, "", ""

        # Decode shortcode to numeric media_id directly (no HTML parsing needed)
        media_id = self._shortcode_to_media_id(post_code)

        session, _ = self._get_session()
        session.headers.update({
            "X-IG-App-ID": "238260118697367",
            "Accept": "application/json",
        })
        api_url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"
        try:
            resp = session.get(api_url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if items:
                    caption = items[0].get("caption", {}) or {}
                    caption_text = caption.get("text", "") if isinstance(caption, dict) else ""
                    found = re.findall(r'#(\w+)', caption_text)
                    hashtags = ", ".join(found) if found else ""
                    return post_code, caption_text, hashtags
        except Exception:
            pass

        return post_code, "", ""

    def get_video_url(self, url):
        """Resolve the direct video CDN URL for a Threads post.

        This is needed for downloading since yt-dlp doesn't support Threads.
        """
        post_code = self.extract_video_id(url)
        if not post_code:
            raise ValueError(f"Could not extract post code from: {url}")

        # Decode shortcode to numeric media_id directly (no HTML parsing needed)
        media_id = self._shortcode_to_media_id(post_code)

        session, _ = self._get_session()
        session.headers.update({
            "X-IG-App-ID": "238260118697367",
            "Accept": "application/json",
        })
        api_url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"
        resp = session.get(api_url, timeout=30)

        if resp.status_code != 200:
            raise ValueError(f"Instagram API returned HTTP {resp.status_code}")

        data = resp.json()
        items = data.get("items", [])
        if not items:
            raise ValueError("No items in Instagram API response")

        video_versions = items[0].get("video_versions", [])
        if not video_versions:
            raise ValueError("No video versions found")

        best = sorted(video_versions, key=lambda v: v.get("type", 0), reverse=True)[0]
        return best.get("url", "")

    def download_video(self, url, output_path, progress_callback=None):
        """Download a Threads video directly to a file (bypasses yt-dlp)."""
        video_url = self.get_video_url(url)
        if not video_url:
            raise ValueError("Could not resolve video URL")

        if not video_url.startswith("http"):
            video_url = "https:" + video_url

        print(f"   Downloading from Instagram CDN...")

        session, _ = self._get_session()
        r = session.get(video_url, timeout=300, stream=True)
        if r.status_code != 200:
            raise ValueError(f"Download failed (HTTP {r.status_code})")

        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total and progress_callback:
                        pct = downloaded / total * 100
                        if pct % 10 < 1:  # log ~every 10%
                            progress_callback(f"   ⬇️  {pct:.0f}%")

        return str(output_path)

    # ── Profile scraping (not implemented) ──────────────────────

    def get_all_videos_from_profile(self, username, max_videos=50, progress_callback=None):
        raise NotImplementedError(
            "Threads profile scraping is not yet supported. "
            "Use individual post URLs."
        )

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _extract_username(url):
        """Extract the @username from a Threads URL."""
        m = re.search(r'threads\.(?:com|net)/@([^/]+)', url)
        return m.group(1) if m else ""


# ── Legacy helpers (compatible with instagram.py's cookie check) ──

def _check_cookie_file(cookies_path):
    """Re-export for instagram.py's multi-account functions."""
    from platforms.instagram import _check_cookie_file as _ig_check
    return _ig_check(cookies_path)
