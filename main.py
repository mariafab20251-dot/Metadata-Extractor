import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import tkinter as tk
import sys
import os
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from gui.dashboard import Dashboard  # Professional GUI
from core.database import VideoDatabase
from core.downloader import VideoDownloader
from core.extractor import MediaExtractor
from core.exporter import DataExporter
from platforms.instagram import InstagramScraper
from platforms.tiktok import TikTokScraper
from platforms.youtube import YouTubeScraper
from platforms.facebook import FacebookScraper
from platforms.xiaohongshu import XiaohongshuScraper
from datetime import datetime

class VideoProcessor:
    def __init__(self):
        self.db = VideoDatabase()
        self.extractor = MediaExtractor()
        self.exporter = DataExporter()
        self.scrapers = {
            'instagram': InstagramScraper(),
            'tiktok': TikTokScraper(),
            'youtube': YouTubeScraper(),
            'facebook': FacebookScraper(),
            'xiaohongshu': XiaohongshuScraper()
        }
        self.current_channel_folder = None

    def extract_channel_name(self, url_input, platform):
        """Extract channel/profile name from URL"""
        import re

        if platform == 'youtube':
            if 'youtube.com/@' in url_input:
                match = re.search(r'youtube\.com/@([^/?]+)', url_input)
                if match:
                    return match.group(1)
            elif 'youtube.com/c/' in url_input:
                match = re.search(r'youtube\.com/c/([^/?]+)', url_input)
                if match:
                    return match.group(1)
            elif 'youtube.com/channel/' in url_input:
                match = re.search(r'youtube\.com/channel/([^/?]+)', url_input)
                if match:
                    return match.group(1)[:20]

        elif platform == 'instagram':
            if 'instagram.com' in url_input and '/reel/' not in url_input and '/p/' not in url_input:
                username = url_input.split('/')[-1] or url_input.split('/')[-2]
                return username

        elif platform == 'facebook':
            if 'facebook.com' in url_input:
                match = re.search(r'facebook\.com/([^/?]+)', url_input)
                if match:
                    return match.group(1)

        elif platform == 'tiktok':
            if 'tiktok.com/@' in url_input:
                match = re.search(r'tiktok\.com/@([^/?]+)', url_input)
                if match:
                    return match.group(1)

        elif platform == 'xiaohongshu':
            if 'xiaohongshu.com/user/profile/' in url_input or 'rednote.com/user/profile/' in url_input:
                match = re.search(r'user/profile/([a-f0-9]+)', url_input)
                if match:
                    return match.group(1)[:20]

        return None

    def setup_channel_folder(self, channel_name, platform, url_count=0, min_urls_for_dedicated=5):
        """Create folder structure for channel

        Established channels (already on disk from a metadata scan or
        previous download) keep their dedicated folder. New unknown
        channels are redirected to a shared _general_downloads folder
        per platform — this prevents creating dozens of one-video
        channel directories.

        Exception: If url_count >= min_urls_for_dedicated (default 5),
        a dedicated channel folder is created even for new channels —
        useful when batch-loading Instagram/Facebook URL lists.

        Also: if the exact folder doesn't exist, scans sibling folders
        for any that match the sanitized channel name (case-insensitive).
        This catches cases where detect_channel_from_urls() returns a
        slightly different name than the metadata scan used.
        """
        from pathlib import Path
        from config import BASE_DIR

        if not channel_name:
            return None

        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', channel_name)
        safe_name = safe_name[:50]

        MISC = "_general_downloads"  # shared misc folder name
        channel_folder = BASE_DIR / "channels" / platform / safe_name

        # If the exact folder doesn't exist, scan siblings for a match.
        # This handles name differences between yt-dlp and metadata scan
        # (e.g. "PetsAreAngelz" vs "Pets_Are_Angelz").
        if not channel_folder.exists():
            channels_dir = BASE_DIR / "channels" / platform
            if channels_dir.exists():
                found = None
                for sibling in channels_dir.iterdir():
                    if not sibling.is_dir() or sibling.name == MISC:
                        continue
                    # Compare alphanumeric skeleton (strip spaces, underscores,
                    # special chars) case-insensitively — catches mismatches like
                    # "PetsAreAngelz" vs "Pets_Are_Angelz" vs "Pets Are Angelz"
                    sib_alnum = re.sub(r'[^a-zA-Z0-9]', '', sibling.name).lower()
                    ch_alnum = re.sub(r'[^a-zA-Z0-9]', '', safe_name).lower()
                    if sib_alnum == ch_alnum:
                        found = sibling
                        break
                if found:
                    channel_folder = found

        # If still not found, decide: enough URLs → create dedicated folder,
        # otherwise → shared misc bucket
        if not channel_folder.exists():
            if url_count >= min_urls_for_dedicated:
                pass  # create dedicated folder below
            else:
                channel_folder = BASE_DIR / "channels" / MISC / platform

        channel_folder.mkdir(parents=True, exist_ok=True)

        videos_folder = channel_folder / "videos"
        reports_folder = channel_folder / "reports"
        videos_folder.mkdir(exist_ok=True)
        reports_folder.mkdir(exist_ok=True)

        return channel_folder

    def parse_input(self, url_input, platform):
        # Handle multiple URLs separated by commas, newlines, or spaces
        if ',' in url_input or '\n' in url_input or ';' in url_input:
            # Try splitting by newlines first, then commas, then semicolons
            if '\n' in url_input:
                urls = [url.strip() for url in url_input.split('\n') if url.strip()]
            elif ';' in url_input:
                urls = [url.strip() for url in url_input.split(';') if url.strip()]
            else:
                urls = [url.strip() for url in url_input.split(',') if url.strip()]

            # Only auto-detect channel folder if not already set externally
            # (e.g., by browse_url_file or metadata scan — prevents overwriting
            #  the correct channel folder with None for platforms like YouTube
            #  where video URLs don't embed channel info)
            if self.current_channel_folder is None:
                channel_name = self.detect_channel_from_urls(urls, platform)
                if channel_name:
                    # Pass URL count so Instagram/Facebook batches of 5+
                    # get a dedicated folder instead of _general_downloads
                    self.current_channel_folder = self.setup_channel_folder(
                        channel_name, platform, url_count=len(urls)
                    )
            return urls

        scraper = self.scrapers.get(platform)
        if scraper:
            channel_name = self.extract_channel_name(url_input, platform)
            if channel_name:
                self.current_channel_folder = self.setup_channel_folder(channel_name, platform)
            elif self.current_channel_folder is None and platform in ('youtube', 'tiktok'):
                # Single video URLs don't embed channel info, try metadata lookup
                try:
                    import yt_dlp
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                        info = ydl.extract_info(url_input, download=False)
                        channel = info.get('channel') or info.get('uploader')
                        if channel:
                            self.current_channel_folder = self.setup_channel_folder(channel, platform)
                except:
                    pass

        if not scraper and self.current_channel_folder:
            # No scraper for this platform (e.g. "other" for xvideos/pornhub/hardgif)
            # and no channel auto-detect happened — reset so videos go to
            # VIDEOS_DIR / platform (data/videos/other/) instead of a stale folder
            # from a previous run.
            self.current_channel_folder = None

        if platform == 'instagram' and 'instagram.com' in url_input:
            # Check if it's NOT a single video URL (not /reel/XXX or /p/XXX format)
            # Profile URLs: instagram.com/username or instagram.com/username/ or instagram.com/username/reels/
            if not re.search(r'/(?:reel|p|tv)/[A-Za-z0-9_-]+', url_input):
                # Extract username from profile URL
                # Handle: instagram.com/username, instagram.com/username/, instagram.com/username/reels/
                parts = [p for p in url_input.replace('https://', '').replace('http://', '').split('/') if p and p != 'www.instagram.com' and p != 'instagram.com']
                if parts:
                    username = parts[0]  # First part after domain is the username
                    return scraper.get_all_videos_from_profile(username)

        if platform == 'youtube' and ('youtube.com/channel/' in url_input or 'youtube.com/@' in url_input or 'youtube.com/c/' in url_input):
            return scraper.get_all_videos_from_channel(url_input)

        if platform == 'xiaohongshu' and ('xiaohongshu.com/user/profile/' in url_input or 'rednote.com/user/profile/' in url_input):
            # Profile URL detected, scrape all videos (keep channel folder set above)
            return scraper.get_all_videos_from_profile(url_input)

        # Single video URL — keep existing channel folder if set (from browse/file load)
        return [url_input]

    def detect_channel_from_urls(self, urls, platform):
        """Detect if all URLs belong to the same channel"""
        if not urls:
            return None

        channel_names = set()

        for url in urls[:10]:
            if platform == 'youtube':
                # YouTube video URLs (watch?v=XXX or youtu.be/XXX) don't
                # embed channel info — fetch it from the first video's metadata.
                try:
                    import yt_dlp
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                        info = ydl.extract_info(urls[0], download=False)
                        # yt-dlp video-level keys for the channel/uploader name
                        channel = info.get('channel') or info.get('uploader')
                        if channel:
                            return channel
                except:
                    pass
                return None

            elif platform == 'instagram':
                match = re.search(r'instagram\.com/([^/]+)/(?:reel|p|tv)/', url)
                if match:
                    username = match.group(1)
                    if username not in ['reel', 'p', 'tv']:
                        channel_names.add(username)

            elif platform == 'tiktok':
                match = re.search(r'tiktok\.com/@([^/]+)/', url)
                if match:
                    channel_names.add(match.group(1))

            elif platform == 'facebook':
                match = re.search(r'facebook\.com/([^/]+)/', url)
                if match:
                    channel_names.add(match.group(1))

            elif platform == 'xiaohongshu':
                # Xiaohongshu video URLs don't contain user/channel info
                # Try to find channel info from database for processed URLs
                try:
                    existing_data = self.db.get_processed_data(url)
                    if existing_data and existing_data.get('channel_name'):
                        channel_names.add(existing_data['channel_name'])
                except:
                    pass

        if len(channel_names) == 1:
            return channel_names.pop()

        return None

    def process_video(self, url, platform, log_callback, force_reprocess=False, download_video=True, download_audio=False, audio_format="mp3", video_quality="best", voice_only=False, extract_ocr=True, extract_speech=True, extract_captions=False):
        # Progress wrapper for download updates — replaces last log line
        def _dl_progress(msg):
            try:
                log_callback(msg, replace_last=True)
            except TypeError:
                log_callback(msg)
        existing_data = self.db.get_processed_data(url)

        if existing_data and not force_reprocess:
            log_callback(f"🔄 Found existing data, checking what needs updating...")

            need_ocr = download_video and extract_ocr and not existing_data['overlay_text']
            need_speech = (download_video or download_audio) and extract_speech and not existing_data['speech_text']
            need_metadata = (platform in ('youtube',)) or (not existing_data['captions'] and not existing_data['hashtags'])

            if not any([need_ocr, need_speech, need_metadata]):
                log_callback(f"⏭️ Skipping (all requested data already exists)")
                return "skipped"

            log_callback(f"📝 Updating missing fields: OCR={need_ocr}, Speech={need_speech}, Metadata={need_metadata}")
            overlay_text = existing_data['overlay_text']
            speech_text = existing_data['speech_text']
            captions = existing_data['captions']
            hashtags = existing_data['hashtags']
        else:
            overlay_text = ""
            speech_text = ""
            captions = ""
            hashtags = ""
            need_ocr = download_video and extract_ocr
            need_speech = (download_video or download_audio) and extract_speech
            need_metadata = True

        video_path = None
        audio_path = None
        try:
            from pathlib import Path
            scraper = self.scrapers.get(platform)

            # Initialize metadata fields first (may be overwritten by extractors below)
            video_channel = ""
            video_title = ""
            video_description = ""
            video_duration = 0.0
            video_view_count = 0

            if need_metadata and scraper:
                video_id, new_captions, new_hashtags = scraper.get_post_metadata(url)
                if new_captions: captions = new_captions
                if new_hashtags: hashtags = new_hashtags
            elif need_metadata and platform in ('bilibili', 'other'):
                # Platforms without a custom scraper — yt-dlp handles them
                try:
                    import yt_dlp
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        video_id = info.get('id', url.split('/')[-1].split('?')[0])
                        if info.get('description'): captions = info['description']
                        if info.get('tags'): hashtags = ','.join(info['tags'][:5])
                        if info.get('title'): video_title = info['title']
                        if info.get('duration'): video_duration = float(info['duration'])
                        if info.get('view_count'): video_view_count = int(info['view_count'])
                        if not video_channel:
                            video_channel = info.get('uploader') or info.get('channel', '') or ''
                except:
                    # Extract video ID from query params if available
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query)
                    # xvideos format: /video.{id}/slug
                    xv_match = re.search(r'/video\.([a-zA-Z0-9]+)', parsed.path)
                    video_id = xv_match.group(1) if xv_match else (
                        qs.get('viewkey', [None])[0] or qs.get('bvid', [None])[0] or parsed.path.split('/')[-1] or parsed.path.split('/')[-2]
                    )
            else:
                video_id = url.split('/')[-1].split('?')[0]

            if need_metadata:
                # Channel name from the folder path (if it's a dedicated channel)
                if self.current_channel_folder:
                    folder_name = Path(self.current_channel_folder).name
                    if folder_name != "_general_downloads":
                        video_channel = folder_name
                # For YouTube, do a single lightweight yt-dlp call to get title,
                # description, channel, duration, and view count — these aren't
                # returned separately by get_post_metadata, and the cost is
                # negligible compared to the download + OCR + speech pipeline.
                if platform in ('youtube',):
                    try:
                        import yt_dlp
                        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                            info = ydl.extract_info(url, download=False)
                            video_title = info.get('title', '') or ''
                            video_description = info.get('description', '') or ''
                            video_duration = float(info.get('duration', 0) or 0)
                            video_view_count = int(info.get('view_count', 0) or 0)
                            if not video_channel:
                                video_channel = info.get('channel') or info.get('uploader', '') or ''
                    except:
                        pass
                # Discard stale title-as-captions cached by older versions:
                # YouTube captions now come only from the dedicated extractor below,
                # so a cached value equal to the title/description is bad data.
                if platform in ('youtube',) and captions:
                    _placeholder = f"{video_title}. {video_description}".strip('. ')
                    if captions.strip() in (video_title.strip(), _placeholder, video_title.strip() + '.'):
                        captions = ""
            else:
                # For re-processed entries, restore from existing captions
                if captions and '. ' in captions:
                    parts = captions.split('. ', 1)
                    video_title = parts[0]
                    video_description = parts[1] if len(parts) > 1 else ''
                if self.current_channel_folder:
                    folder_name = Path(self.current_channel_folder).name
                    if folder_name != "_general_downloads":
                        video_channel = folder_name

            if not video_id:
                raise Exception("Could not extract video ID")

            # Extract YouTube captions without downloading (if requested)
            if extract_captions and platform in ('youtube',):
                # Clear any title/description placeholder from scraper metadata
                captions = ""
                log_callback(f"📝 Extracting YouTube captions (no download)...")
                try:
                    import yt_dlp, requests
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                        info = ydl.extract_info(url, download=False)

                    def _parse_youtube_caption_text(text, fmt=''):
                        """Extract plain text from YouTube caption response."""
                        if not text:
                            return ''
                        # JSON/pb3 format (preferred — cleanest, no repetitions)
                        if text.strip().startswith('{'):
                            try:
                                parsed = json.loads(text)
                            except (json.JSONDecodeError, ValueError):
                                return text.strip()
                            events = parsed.get('events', [])
                            seen = set()
                            lines = []
                            for ev in events:
                                segs = ev.get('segs', [])
                                for seg in segs:
                                    utf8 = seg.get('utf8', '')
                                    word = utf8.strip()
                                    if word and word not in seen:
                                        seen.add(word)
                                        lines.append(word)
                            return ' '.join(lines).strip()
                        # SRT format (simple timestamps)
                        if fmt == 'srt' or text.strip()[:1].isdigit():
                            text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', text)
                            text = re.sub(r'<[^>]+>', '', text)
                            text = re.sub(r'\n\s*\n+', '\n', text).strip()
                            return text
                        # VTT format (messy with repetitions, needs dedup)
                        text = re.sub(r'^WEBVTT.*?\n', '', text, flags=re.DOTALL)
                        text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
                        text = re.sub(r'<[^>]+>', '', text)
                        text = re.sub(r'\n{3,}', '\n\n', text).strip()
                        # Dedup repeated lines (VTT overlaps old+new text)
                        seen = set()
                        unique = []
                        for line in text.split('\n'):
                            line = line.strip()
                            if line and line not in seen:
                                seen.add(line)
                                unique.append(line)
                        return ' '.join(unique).strip()

                    def _pick_caption_entry(entries):
                        """Pick best caption entry from list: json3 > srt > vtt > others."""
                        score = {'json3': 4, 'srt': 3, 'vtt': 2, 'srv3': 1, 'srv2': 1, 'srv1': 1, 'ttml': 1}
                        best = None
                        best_score = -1
                        for e in entries:
                            ext = (e.get('ext') or '').lower()
                            s = score.get(ext, 0)
                            if s > best_score:
                                best_score = s
                                best = e
                        return best

                    caption_text = ""
                    for lang in ('en', 'en-US', 'en-GB'):
                        subs = (info.get('subtitles') or {}).get(lang, [])
                        auto_subs = (info.get('automatic_captions') or {}).get(lang, [])
                        all_entries = subs + auto_subs
                        if not all_entries:
                            continue
                        entry = _pick_caption_entry(all_entries)
                        if not entry or not entry.get('url'):
                            continue
                        ext = (entry.get('ext') or '').lower()
                        try:
                            resp = requests.get(entry['url'], timeout=15)
                            if resp.status_code == 200:
                                parsed = _parse_youtube_caption_text(resp.text, ext)
                                if parsed:
                                    caption_text = parsed
                                    break
                        except Exception:
                            continue

                    if caption_text:
                        captions = caption_text
                        log_callback(f"✅ Extracted {len(caption_text)} chars of captions")

                        # Auto-skip download if only captions were the goal
                        if not need_ocr and not need_speech:
                            log_callback(f"📝 Captions retrieved — skipping video download")
                            download_video = False
                            download_audio = False
                    else:
                        log_callback("⚠️ No captions available for this video (try English-only)")
                except Exception as e:
                    log_callback(f"⚠️ Caption extraction failed: {str(e)[:80]}")

                # If ONLY captions requested (no other processing), save and return early
                if not download_video and not download_audio and not need_ocr and not need_speech and not need_metadata:
                    log_callback("✅ Captions-only mode — saving results")
                    self.db.save_extracted_data(url, video_id, video_channel, video_title,
                                                video_description, "", "", captions, hashtags,
                                                str(video_duration), str(video_view_count))
                    return captions

            # If voice_only mode is enabled, check for voiceover first before downloading anything
            if voice_only and (download_video or download_audio):
                log_callback(f"🔍 Checking for voiceover before downloading...")
                downloader = VideoDownloader(platform, channel_folder=self.current_channel_folder)
                # Download audio temporarily to check for voice
                temp_audio = downloader.download_audio(url, video_id, "mp3", voice_only=True, title=video_title, progress_callback=_dl_progress)

                if temp_audio == "no_voice":
                    log_callback(f"⏭️  Skipped (no voiceover detected)")
                    return "skipped"

                # Voice detected, continue with normal download
                audio_path = temp_audio
                log_callback(f"✅ Voiceover detected, continuing download...")

            if need_speech and download_audio and not download_video:
                if not voice_only:  # Only download audio if we didn't already check
                    log_callback(f"🎵 Downloading audio {video_id}...")
                    downloader = VideoDownloader(platform, channel_folder=self.current_channel_folder)
                    audio_path = downloader.download_audio(url, video_id, audio_format, voice_only=voice_only, title=video_title, progress_callback=_dl_progress)

                    if audio_path == "no_voice":
                        log_callback(f"⏭️  Skipped (no voiceover detected)")
                        return "skipped"

                    if not audio_path or not os.path.exists(audio_path):
                        raise Exception("Audio download failed")

                log_callback(f"🎤 Transcribing speech from audio...")
                speech_text = self.extractor.extract_speech(audio_path)

            elif download_video:
                log_callback(f"📥 Downloading video {video_id}...")
                downloader = VideoDownloader(platform, channel_folder=self.current_channel_folder)
                video_path = downloader.download(url, video_id, quality=video_quality, title=video_title, progress_callback=_dl_progress)

                if not video_path or not os.path.exists(video_path):
                    raise Exception("Download failed")

                if need_ocr:
                    log_callback(f"🔍 Extracting overlay text...")
                    overlay_text = self.extractor.extract_overlay_text(video_path, video_id)

                if need_speech:
                    log_callback(f"🎤 Transcribing speech...")
                    speech_text = self.extractor.extract_speech(video_path)

                # Also download audio if requested
                if download_audio:
                    if not voice_only:  # Only download if we didn't already check
                        log_callback(f"🎵 Downloading audio {video_id}...")
                        downloader = VideoDownloader(platform, channel_folder=self.current_channel_folder)
                        audio_path = downloader.download_audio(url, video_id, audio_format, voice_only=False, title=video_title, progress_callback=_dl_progress)
            elif need_metadata:
                log_callback(f"📝 Extracting metadata only...")

            # Calculate transcript word count and WPM
            transcript_word_count = 0
            transcript_wpm = 0.0
            if speech_text:
                transcript_word_count = len(speech_text.split())
                if video_duration > 0:
                    transcript_wpm = (transcript_word_count / video_duration) * 60

            if transcript_word_count > 0:
                log_callback(f"📊 Transcript: {transcript_word_count:,} words, " +
                            f"{transcript_wpm:.1f} WPM" +
                            (f" (duration: {video_duration:.0f}s)" if video_duration > 0 else ""))

            self.exporter.save_results(
                video_id, url, platform, overlay_text,
                speech_text, captions, hashtags,
                channel_folder=self.current_channel_folder,
                channel_name=video_channel,
                video_title=video_title,
                video_description=video_description,
                transcript_word_count=transcript_word_count,
                transcript_wpm=transcript_wpm,
                video_duration=video_duration,
                view_count=video_view_count
            )

            self.db.add_video(
                video_id, platform, url, overlay_text,
                speech_text, captions, hashtags,
                transcript_word_count=transcript_word_count,
                transcript_wpm=transcript_wpm,
                video_duration=video_duration,
                view_count=video_view_count
            )
            log_callback(f"✅ Completed: {video_id}")

            return "success"

        except Exception as e:
            log_callback(f"❌ Failed {url}: {str(e)}")
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except:
                    pass
            raise

    def process_local_video(self, video_path, log_callback):
        try:
            video_id = Path(video_path).stem
            log_callback(f"🔍 Extracting overlay text...")
            overlay_text = self.extractor.extract_overlay_text(video_path, video_id)

            log_callback(f"🎤 Transcribing speech...")
            speech_text = self.extractor.extract_speech(video_path)

            self.exporter.save_results(
                video_id, video_path, "local", overlay_text,
                speech_text, "", "", channel_name=Path(video_path).parent.name
            )

            log_callback(f"✅ Completed: {video_id}")
            return "success"

        except Exception as e:
            log_callback(f"❌ Failed: {str(e)}")
            raise

if __name__ == "__main__":
    root = tk.Tk()
    processor = VideoProcessor()
    app = Dashboard(root, processor)
    root.mainloop()
