import re
import yt_dlp

class YouTubeScraper:
    def __init__(self):
        pass

    def extract_video_id(self, url):
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_post_metadata(self, url):
        video_id = self.extract_video_id(url)
        if not video_id:
            return None, "", ""

        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                description = info.get('description', '')
                title = info.get('title', '')
                tags = info.get('tags', [])

                captions = f"{title}. {description}" if description else title
                hashtags = " ".join([f"#{tag}" for tag in tags if tag])

                return video_id, captions, hashtags
        except Exception:
            return video_id, "", ""

    def get_all_videos_from_channel(self, channel_url):
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(channel_url, download=False)

                video_urls = []
                if 'entries' in result:
                    for entry in result['entries']:
                        if entry:
                            video_id = entry.get('id')
                            if video_id:
                                video_urls.append(f"https://youtube.com/watch?v={video_id}")

                return video_urls
        except Exception as e:
            raise Exception(f"Failed to fetch channel videos: {str(e)}")
