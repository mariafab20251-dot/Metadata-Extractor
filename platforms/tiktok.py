import re
import requests
from urllib.parse import urlparse

class TikTokScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def extract_video_id(self, url):
        patterns = [
            r'tiktok.com/@[\w.-]+/video/(\d+)',
            r'tiktok.com/.*[?&]v=(\d+)',
            r'vm.tiktok.com/(\w+)',
            r'vt.tiktok.com/(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Try to extract from shortened URL
        if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
            try:
                response = requests.head(url, headers=self.headers, allow_redirects=True, timeout=10)
                return self.extract_video_id(response.url)
            except:
                pass

        return None

    def get_post_metadata(self, url):
        video_id = self.extract_video_id(url)
        if not video_id:
            return None, "", ""

        try:
            # Basic metadata extraction - captions/hashtags would require TikTok API or scraping
            # For now, return empty strings (yt-dlp will handle download)
            return video_id, "", ""
        except Exception:
            return video_id, "", ""

    def get_all_videos_from_profile(self, username):
        # TikTok profile scraping requires more complex auth/API access
        # For now, raise not implemented
        raise NotImplementedError("TikTok profile scraping requires TikTok API access. Use direct video URLs instead.")
