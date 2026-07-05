import yt_dlp
from pathlib import Path
from config import VIDEOS_DIR, MAX_RETRIES
import os
import sys
import re
from io import StringIO
import contextlib


# Context manager to suppress progress output from yt-dlp
@contextlib.contextmanager
def suppress_output():
    """Suppress stdout only (yt-dlp progress) — let stderr (warnings/errors) through"""
    old_stdout = sys.stdout
    try:
        sys.stdout = StringIO()
        yield
    finally:
        sys.stdout = old_stdout


class VideoDownloader:
    # Platforms that should save files as "{video_id}.ext" (no title in the
    # filename) — their IDs are stable and titles add noise / length issues.
    ID_ONLY_PLATFORMS = {'youtube', 'instagram', 'facebook', 'tiktok'}

    def __init__(self, platform, channel_folder=None):
        self.platform = platform
        if channel_folder:
            self.output_dir = channel_folder / "videos"
            self.audio_dir = channel_folder / "audio"
        else:
            self.output_dir = VIDEOS_DIR / platform
            self.audio_dir = VIDEOS_DIR.parent / "audio" / platform
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = VIDEOS_DIR.parent / "cookies.txt"

    def _id_only(self):
        """True when this platform should name files by video ID only."""
        return (self.platform or '').lower() in self.ID_ONLY_PLATFORMS

    @staticmethod
    def _sanitize_filename(name):
        """Sanitize a string for use as a filename — remove chars invalid on Windows."""
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = re.sub(r'\s+', ' ', name).strip()
        # Limit length (255 is max for NTFS, leave room for extension + video_id)
        if len(name) > 180:
            name = name[:180].rstrip()
        return name or "untitled"

    def download(self, url, video_id, quality="best", title=None, progress_callback=None):
        if title and not self._id_only():
            safe_title = self._sanitize_filename(title)
            output_path = self.output_dir / f"{safe_title} [{video_id}].mp4"
        else:
            output_path = self.output_dir / f"{video_id}.mp4"

        if output_path.exists():
            return str(output_path)

        # Normalise rednote.com → xiaohongshu.com for yt-dlp, which has
        # a XiaohongshuIE extractor but no extractor for the rednote.com
        # alias domain.  Both share the same backend and cookies.
        yt_url = re.sub(r'(?:www\.)?rednote\.com', 'www.xiaohongshu.com', url)

        # Build a progress hook that calls back with live download stats
        last_pct = [0]  # mutable box to throttle log spam

        def _progress_hook(d):
            if d['status'] == 'downloading' and progress_callback:
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                pct = (downloaded / total * 100) if total else 0
                # Only log every ~2% to avoid flooding the log window
                if pct - last_pct[0] >= 2 or (pct >= 99 and last_pct[0] < 99):
                    last_pct[0] = pct
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    speed_str = f"{speed/1024/1024:.1f} MiB/s" if speed else "?"
                    eta_str = f"{eta//60:02.0f}:{eta%60:02.0f}" if eta else "?"
                    progress_callback(
                        f"   ⬇️  {pct:.0f}% ({speed_str}) ETA {eta_str}"
                    )
            elif d['status'] == 'finished' and progress_callback:
                progress_callback("   ✅ Download complete, processing...")

        print(f"📥 Downloading: {yt_url}")

        # Instagram preflight: yt-dlp needs a valid sessionid in cookies.txt.
        # Without it Instagram returns an "empty media response" (looks logged
        # out). Check up front and tell the user exactly what to do.
        if 'instagram.com' in yt_url:
            try:
                from platforms.instagram import ig_session_status
                ig = ig_session_status(self.cookies_file)
                if not ig["logged_in"]:
                    raise RuntimeError(
                        "❌ Instagram not logged in — "
                        f"{ig['reason']}.\n\n"
                        "FIX: Open Settings → Instagram and Login again, "
                        "or import fresh cookies. The login token (sessionid) "
                        f"must be present in:\n  {self.cookies_file}"
                    )
            except ImportError:
                pass  # platforms not importable (standalone use) — let yt-dlp try

        # Bilibili needs extra headers (Referer) or it returns 412
        if 'bilibili.com' in yt_url:
            ydl_opts['http_headers']['Referer'] = 'https://www.bilibili.com/'
            ydl_opts['http_headers']['Origin'] = 'https://www.bilibili.com/'

        # Check if Facebook and cookies exist
        if 'facebook.com' in yt_url and not self.cookies_file.exists():
            print(f"⚠️  WARNING: Facebook downloads require cookies.txt!")
            print(f"   Download may fail. Please export Facebook cookies to: {self.cookies_file}")

        # Map quality string to max height for format_sort
        quality = quality.strip().lower()
        if quality.startswith("2160") or quality.startswith("4k"):
            max_h = 2160
            label = "2160p (4K)"
        elif quality.startswith("1440"):
            max_h = 1440
            label = "1440p"
        elif quality.startswith("1080"):
            max_h = 1080
            label = "1080p"
        elif quality.startswith("720"):
            max_h = 720
            label = "720p"
        elif quality.startswith("480"):
            max_h = 480
            label = "480p"
        elif quality.startswith("360"):
            max_h = 360
            label = "360p"
        else:
            max_h = 2160
            label = "Best"

        # Use bv*+ba (best video with any codec + best audio) with format_sort
        # to cap resolution at the user's choice. format_sort is more reliable
        # than the complex format+fallback chains.
        fmt = f'bv*[height<={max_h}]+ba/b[height<={max_h}]/bv*+ba/b'
        print(f"   Format: {fmt} (target: {label})")

        ydl_opts = {
            'format': fmt,
            'merge_output_format': 'mp4',
            'outtmpl': str(output_path.with_suffix('')),
            'quiet': True,
            'no_warnings': True,
            'retries': MAX_RETRIES,
            'verbose': False,
            'noprogress': True,  # Suppress progress output
            'ignoreerrors': False,  # Don't ignore errors
            'no_color': True,  # Disable colors in output
            'socket_timeout': 30,  # 30 second timeout
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate'
            },
            'progress_hooks': [_progress_hook] if progress_callback else [],
        }

        # Add cookies if file exists
        if self.cookies_file.exists():
            ydl_opts['cookiefile'] = str(self.cookies_file)

        # Retry loop for transient HTTP errors (especially PornHub 474)
        MAX_RETRY_474 = 2
        last_error = None
        for attempt in range(1, MAX_RETRY_474 + 2):  # 1 initial + MAX_RETRY retries
            if attempt > 1:
                print(f"   🔄 Retry {attempt - 1}/{MAX_RETRY_474} — waiting 30s before retry...")
                if progress_callback:
                    progress_callback(f"   ⏳ Retry {attempt - 1}/{MAX_RETRY_474} — waiting 30s...")
                import time
                time.sleep(30)
                # Reset progress tracking for retry
                last_pct = [0]

            try:
                # Only suppress progress output, keep errors visible
                with suppress_output():
                    # Download with yt-dlp
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        result = ydl.download([yt_url])

                        # Check if download failed (yt-dlp returns 1 on error)
                        if result != 0:
                            raise Exception("Download failed - yt-dlp returned error code")

                # Check for file without extension first (yt-dlp sometimes saves without extension)
                no_ext_path = output_path.with_suffix('')
                if no_ext_path.exists():
                    try:
                        # Check file size first
                        file_size = no_ext_path.stat().st_size

                        if file_size == 0:
                            print(f"❌ ERROR: Downloaded file is empty!")
                            no_ext_path.unlink()  # Delete empty file
                            return None

                        # Try rename
                        no_ext_path.rename(output_path)

                        # Verify renamed file exists
                        if output_path.exists():
                            print(f"✅ Download complete")
                            return str(output_path)
                        else:
                            print(f"❌ ERROR: File missing after rename!")
                            return None

                    except Exception as rename_err:
                        # Try direct copy as fallback
                        try:
                            import shutil
                            shutil.copy2(no_ext_path, output_path)
                            print(f"✅ Download complete")
                            return str(output_path)
                        except Exception as copy_err:
                            print(f"❌ ERROR: File operation failed: {copy_err}")
                            return None

                # Handle extension variations
                for ext in ['.mp4', '.mkv', '.webm']:
                    potential_path = output_path.with_suffix(ext)
                    if potential_path.exists():
                        if ext != '.mp4':
                            potential_path.rename(output_path)
                        print(f"✅ Download complete")
                        return str(output_path)

                # No file found - download failed
                raise Exception("No output file found after download")
            except Exception as e:
                error_msg = str(e)

                # On 474 (PornHub throttling/geo), retry if attempts remain
                if '474' in error_msg and attempt < MAX_RETRY_474 + 1:
                    last_error = e
                    print(f"   ⚠️  HTTP 474 (PornHub throttling) — will retry")
                    continue

                # Exhausted retries on 474 — give a clear message
                if '474' in error_msg:
                    raise Exception(
                        "❌ PornHub throttled the download (HTTP 474) after retries.\n"
                        "This is a temporary server-side block. Try:\n"
                        "  • Wait a few minutes and try again\n"
                        "  • Use a different VPN exit node\n"
                        "  • Export fresh PornHub cookies while logged in"
                    )

                # YouTube bot detection
                if 'youtube.com' in url or 'youtu.be' in url:
                    if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
                        raise Exception(
                            "❌ YouTube blocked the download (bot detection)\n\n"
                            "SOLUTION: Export YouTube cookies to cookies.txt\n"
                            "1. Login to YouTube in your browser\n"
                            "2. Use 'Get cookies.txt LOCALLY' extension\n"
                            "3. Export cookies while on youtube.com\n"
                            "4. Merge with your existing cookies.txt\n\n"
                            f"Place cookies at: {self.cookies_file}"
                        )

                # Facebook-specific errors
                if 'facebook.com' in url:
                    if 'timed out' in error_msg or 'getaddrinfo failed' in error_msg:
                        raise Exception(
                            "❌ Facebook download timed out!\n\n"
                            "SOLUTIONS:\n"
                            "• Export fresh Facebook cookies to cookies.txt\n"
                            "• Wait 10-15 minutes (rate limiting)\n"
                            "• Check your internet connection"
                        )
                    if not self.cookies_file.exists():
                        raise Exception(
                            "❌ Facebook requires cookies.txt!\n"
                            "Please export Facebook cookies from your browser."
                        )

                # Instagram-specific errors
                if 'instagram.com' in url:
                    if not self.cookies_file.exists():
                        raise Exception(
                            f"❌ Instagram requires cookies.txt!\n"
                            f"Place cookies at: {self.cookies_file}"
                        )
                    if 'empty media response' in error_msg.lower() or 'login' in error_msg.lower():
                        raise Exception(
                            "❌ Instagram served a logged-out response (empty media).\n\n"
                            "Your sessionid is missing or expired. FIX:\n"
                            "• Settings → Instagram → Login again, or import fresh cookies\n"
                            f"• The login token must be in: {self.cookies_file}"
                        )
                    if 'No video formats found' in error_msg:
                        raise Exception(
                            "❌ Instagram post has no video!\n"
                            "This is a photo post, not a video. Skipping."
                        )

                # Check for auth errors
                if 'login' in error_msg.lower() or '401' in error_msg or 'unauthorized' in error_msg.lower():
                    raise Exception(
                        f"❌ Authentication failed!\n"
                        f"Your cookies are expired. Re-export cookies.txt from browser."
                    )

                raise Exception(f"❌ Download failed: {error_msg}")

    def download_audio(self, url, video_id, audio_format="mp3", voice_only=False, title=None, progress_callback=None):
        if title and not self._id_only():
            safe_title = self._sanitize_filename(title)
            output_path = self.audio_dir / f"{safe_title} [{video_id}].{audio_format}"
        else:
            output_path = self.audio_dir / f"{video_id}.{audio_format}"

        if output_path.exists():
            return str(output_path)

        # Build a progress hook for audio downloads
        last_pct = [0]

        def _audio_progress_hook(d):
            if d['status'] == 'downloading' and progress_callback:
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                pct = (downloaded / total * 100) if total else 0
                if pct - last_pct[0] >= 5 or (pct >= 95 and last_pct[0] < 95):
                    last_pct[0] = pct
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    speed_str = f"{speed/1024/1024:.1f} MiB/s" if speed else "?"
                    eta_str = f"{eta//60:02.0f}:{eta%60:02.0f}" if eta else "?"
                    progress_callback(
                        f"   ⬇️  {pct:.0f}% ({speed_str}) ETA {eta_str}"
                    )
            elif d['status'] == 'finished' and progress_callback:
                progress_callback("   ✅ Audio download complete, processing...")

        print(f"🎵 Downloading audio...")

        # Normalise rednote.com → xiaohongshu.com for yt-dlp
        yt_url = re.sub(r'(?:www\.)?rednote\.com', 'www.xiaohongshu.com', url)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_path.with_suffix('')),
            'quiet': True,
            'no_warnings': True,
            'retries': MAX_RETRIES,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'progress_hooks': [_audio_progress_hook] if progress_callback else [],
        }

        if self.cookies_file.exists():
            ydl_opts['cookiefile'] = str(self.cookies_file)

        # Retry loop for transient HTTP errors (especially PornHub 474)
        MAX_RETRY_474 = 2
        for attempt in range(1, MAX_RETRY_474 + 2):
            if attempt > 1:
                print(f"   🔄 Retry {attempt - 1}/{MAX_RETRY_474} — waiting 30s before retry...")
                if progress_callback:
                    progress_callback(f"   ⏳ Retry {attempt - 1}/{MAX_RETRY_474} — waiting 30s...")
                import time
                time.sleep(30)

            try:
                # Suppress all yt-dlp output
                with suppress_output():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([yt_url])

                if output_path.exists():
                    # If voice_only mode, check if audio contains speech
                    if voice_only:
                        has_voice = self._detect_voice_in_audio(output_path)
                        if not has_voice:
                            print(f"⏭️  No voiceover detected, skipping audio")
                            output_path.unlink()  # Delete the audio file
                            return "no_voice"

                    print(f"✅ Audio downloaded")
                    return str(output_path)

                return None

            except Exception as e:
                error_msg = str(e)

                # On 474 (PornHub throttling/geo), retry if attempts remain
                if '474' in error_msg and attempt < MAX_RETRY_474 + 1:
                    print(f"   ⚠️  HTTP 474 (PornHub throttling) — will retry")
                    continue

                if '474' in error_msg:
                    raise Exception(
                        "❌ PornHub throttled the download (HTTP 474) after retries.\n"
                        "  • Wait a few minutes and try again\n"
                        "  • Use a different VPN exit node\n"
                        "  • Export fresh PornHub cookies while logged in"
                    )

                raise Exception(f"Audio download failed: {error_msg}")

    def _detect_voice_in_audio(self, audio_path):
        """Detect if audio contains human voice/speech using Whisper"""
        try:
            import whisper
            print(f"🔍 Checking for voiceover...")

            # Load a small Whisper model for quick detection
            model = whisper.load_model("tiny")

            # Transcribe the audio
            result = model.transcribe(str(audio_path), language="en", fp16=False)

            # Check if any text was detected
            transcription = result.get("text", "").strip()

            # Consider it has voice if:
            # 1. Transcription has at least 10 characters
            # 2. Transcription has at least 2 words
            words = transcription.split()
            has_voice = len(transcription) >= 10 and len(words) >= 2

            if has_voice:
                print(f"✅ Voiceover detected: \"{transcription[:50]}...\"")
            else:
                print(f"⏭️  No meaningful voiceover found")

            return has_voice

        except Exception as e:
            print(f"⚠️  Voice detection failed: {str(e)}")
            # If detection fails, assume there's voice to be safe
            return True
