import subprocess
import json
from pathlib import Path
import pandas as pd
from openpyxl.styles import Alignment
import time
import sys

class MetadataScanner:
    """Fast metadata extraction using yt-dlp flat-playlist mode"""

    def __init__(self):
        # Use Python module mode to avoid launcher issues on Windows
        self.yt_dlp = [sys.executable, "-m", "yt_dlp"]
        self.instagram_scraper = None
        self.facebook_scraper = None

    def run_cmd(self, cmd):
        """Run command and return output"""
        return subprocess.run(cmd, capture_output=True, text=True)

    def get_playlist_entries(self, url, flat=True, progress_callback=None):
        """Get all entries from playlist/channel without downloading

        Args:
            url: YouTube channel / playlist / profile URL
            flat: If True (default), use --flat-playlist for lightweight
                  basic info (id, title, duration). If False, yt-dlp
                  extracts full metadata including descriptions for every
                  video — still in a single subprocess call with internal
                  connection reuse and parallel workers, avoiding the
                  overhead of N separate subprocess invocations.
            progress_callback: Optional function called with a live count as
                  entries stream in (so the UI doesn't look frozen).
        """
        cmd = self.yt_dlp + ["--no-warnings", "--dump-json", url]
        if flat:
            cmd.insert(-1, "--flat-playlist")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        entries = []
        for line in proc.stdout:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
            if progress_callback and len(entries) % 25 == 0:
                progress_callback(f"Found {len(entries)} videos so far...")
        proc.wait()
        return entries

    def sanitize_sheet_name(self, name):
        """Sanitize name for Excel sheet"""
        import re
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        return safe[:30]  # Excel sheet name limit

    def scan_youtube_channel(self, channel_url, filter_shorts=False, max_videos=None,
                             progress_callback=None, min_views=0, top_n=0):
        """
        Fast scan of YouTube channel/playlist

        Args:
            channel_url: YouTube channel or playlist URL
            filter_shorts: If True, only include videos < 180 seconds
            max_videos: Maximum number of videos to scan (None = all)
            progress_callback: Function to call with progress updates
            min_views: Minimum view count to include (0 = no filter)
            top_n: Only return top N most-viewed videos (0 = all)

        Returns:
            dict with channel info and video list
        """
        if progress_callback:
            progress_callback("Fetching playlist entries...")

        # Flat listing is near-instant (id/title/duration only). Full per-video
        # metadata (flat=False) is far too slow on large shorts channels, so we
        # only fetch view counts later, in parallel, when a popularity filter
        # actually needs them.
        needs_views = (min_views > 0 or top_n > 0)
        entries = self.get_playlist_entries(channel_url, flat=True,
                                            progress_callback=progress_callback)
        total = len(entries)

        if progress_callback:
            progress_callback(f"Found {total} entries. Processing...")

        videos = []
        channel_name = None

        for i, entry in enumerate(entries, 1):
            # Check max_videos limit (only applies when NOT using popularity filter)
            if max_videos and len(videos) >= max_videos and min_views == 0 and top_n == 0:
                break

            vid_id = entry.get("id")
            title = entry.get("title", "")
            url = f"https://www.youtube.com/watch?v={vid_id}"

            if not channel_name:
                channel_name = (entry.get("playlist_channel") or
                               entry.get("playlist_uploader") or
                               entry.get("channel") or
                               entry.get("uploader") or
                               "YouTube")

            duration = entry.get("duration", 0) or 0
            view_count = entry.get("view_count", 0) or 0

            # Filter shorts if requested
            if filter_shorts and duration and duration > 180:
                if progress_callback and i % 50 == 0:
                    progress_callback(f"Scanning... {i}/{total} ({len(videos)} shorts found)")
                continue

            videos.append({
                "video_id": vid_id,
                "title": title,
                "channel_name": channel_name,
                "description": title,
                "url": url,
                "duration": duration,
                "view_count": view_count
            })

            if progress_callback and i % 50 == 0:
                progress_callback(f"Scanning... {i}/{total} ({len(videos)} videos found)")

        # Fetch view counts in parallel ONLY when the popularity filter needs them
        if needs_views and videos:
            videos = self._fetch_view_counts(videos, progress_callback)
            videos = self._apply_popularity_filter(videos, min_views, top_n, progress_callback)

        return {
            "channel_name": channel_name,
            "platform": "youtube",
            "total_entries": total,
            "videos": videos
        }

    def _get_view_count(self, video_url):
        """Fetch view count for a single video using lightweight yt-dlp call"""
        try:
            cmd = self.yt_dlp + ["--quiet", "--no-warnings", "-O", "view_count", video_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.stdout.strip():
                return int(result.stdout.strip())
        except:
            pass
        return 0

    def _fetch_view_counts(self, videos, progress_callback=None):
        """Fetch view counts for all videos in parallel (8 workers)

        Args:
            videos: List of video dicts with at least 'url' key
            progress_callback: Optional progress function

        Returns:
            Same list with 'view_count' populated
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = len(videos)
        if total == 0:
            return videos

        if progress_callback:
            progress_callback(f"📊 Fetching view counts for {total} videos...")

        MAX_WORKERS = 8
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_video = {
                executor.submit(self._get_view_count, v["url"]): v
                for v in videos
            }

            completed = 0
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    video["view_count"] = future.result()
                except:
                    video["view_count"] = 0

                completed += 1
                if progress_callback and completed % 25 == 0:
                    progress_callback(f"📊 View counts: {completed}/{total}")

        return videos

    def _apply_popularity_filter(self, videos, min_views, top_n, progress_callback=None):
        """Filter and sort videos by popularity (view counts already populated)

        Args:
            videos: List of video dicts with 'view_count' populated
            min_views: Minimum view count threshold
            top_n: Keep only top N most-viewed (0 = keep all meeting min_views)
            progress_callback: Optional progress function

        Returns:
            Filtered and sorted list
        """
        # Filter by min views
        filtered = [v for v in videos if v["view_count"] >= min_views]

        # Sort by view_count descending
        filtered.sort(key=lambda v: v["view_count"], reverse=True)

        # Keep top_n if specified
        if top_n > 0:
            filtered = filtered[:top_n]

        if progress_callback:
            progress_callback(f"📊 Popularity filter: {len(filtered)} videos meet criteria " +
                             f"(≥{min_views:,} views)" + (f", top {top_n}" if top_n > 0 else ""))

        return filtered

    def scan_tiktok_profile(self, profile_url, max_videos=None, progress_callback=None):
        """
        Fast scan of TikTok profile

        Args:
            profile_url: TikTok profile URL
            max_videos: Maximum number of videos to scan
            progress_callback: Function to call with progress updates

        Returns:
            dict with profile info and video list
        """
        if progress_callback:
            progress_callback("Fetching TikTok profile entries...")

        entries = self.get_playlist_entries(profile_url)
        total = len(entries)

        username = profile_url.split("@")[-1].strip("/")

        if progress_callback:
            progress_callback(f"Found {total} videos in @{username}")

        videos = []

        for i, entry in enumerate(entries, 1):
            if max_videos and len(videos) >= max_videos:
                break

            vid_id = entry.get("id") or entry.get("url")
            title = entry.get("title", "")

            if not vid_id:
                continue

            video_url = entry.get("url") or f"https://www.tiktok.com/@{username}/video/{vid_id}"
            duration = entry.get("duration", 0)
            description = entry.get("description") or title

            view_count = entry.get("view_count", 0) or 0

            videos.append({
                "video_id": vid_id,
                "title": title,
                "username": username,           # TikTok has username
                "description": description,     # TikTok uses description
                "url": video_url,
                "duration": duration,
                "view_count": view_count
            })

            if progress_callback and i % 10 == 0:
                progress_callback(f"Scanning... {i}/{total}")

        return {
            "channel_name": username,
            "platform": "tiktok",
            "total_entries": total,
            "videos": videos
        }

    def scan_instagram_profile(self, profile_input, max_videos=50, progress_callback=None):
        """
        Fast scan of Instagram profile using yt-dlp with cookies.txt (preferred) or Instaloader

        Args:
            profile_input: Instagram profile URL or username
            max_videos: Maximum number of videos to scan (default: 50)
            progress_callback: Function to call with progress updates

        Returns:
            dict with profile info and video list
        """
        # Extract username from URL if needed
        import re
        if 'instagram.com' in profile_input:
            # Handle various Instagram URL formats
            match = re.search(r'instagram\.com/([^/?]+)', profile_input)
            if match:
                username = match.group(1)
                # Skip if username is actually a content type
                if username in ['reel', 'p', 'tv', 'stories', 'reels', 'tagged', 'saved']:
                    raise Exception(
                        f"Invalid Instagram profile URL: {profile_input}\n"
                        f"Please provide a profile URL like: https://www.instagram.com/username/"
                    )
            else:
                username = profile_input
        else:
            username = profile_input.strip('@')

        # IMPORTANT: yt-dlp's Instagram support is currently broken
        # Skip it and use Instaloader directly
        if progress_callback:
            progress_callback(f"Fetching Instagram profile: @{username}")
            progress_callback("⚠️  Note: Using Instaloader - Instagram API has restrictions")

        return self._scan_instagram_with_instaloader(username, max_videos, progress_callback)

    def _scan_instagram_with_ytdlp(self, username, max_videos, progress_callback):
        """Scan Instagram profile using yt-dlp with cookies.txt"""
        from pathlib import Path
        cookies_file = Path(__file__).parent.parent / "data" / "cookies.txt"

        profile_url = f"https://www.instagram.com/{username}/"

        if progress_callback:
            progress_callback(f"📡 Fetching videos from @{username} with yt-dlp...")

        try:
            # Use yt-dlp to get profile videos
            cmd = self.yt_dlp + [
                "--cookies", str(cookies_file),
                "--flat-playlist",
                "--dump-json",
                "--no-warnings",
                profile_url
            ]

            import subprocess
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            videos = []
            for line in proc.stdout:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    video_id = entry.get('id', '')
                    title = entry.get('title', '')
                    description = entry.get('description', title)
                    url = entry.get('url') or f"https://www.instagram.com/p/{video_id}/"

                    videos.append({
                        "video_id": video_id,
                        "title": title[:100] if title else "",
                        "username": username,
                        "caption": description,
                        "url": url,
                        "duration": entry.get('duration', 0)
                    })

                    if progress_callback and len(videos) % 10 == 0:
                        progress_callback(f"Found {len(videos)} videos...")

                    if max_videos and len(videos) >= max_videos:
                        proc.kill()
                        break
                except:
                    continue

            proc.wait()

            if not videos:
                raise Exception(f"No videos found for @{username} using yt-dlp")

            if progress_callback:
                progress_callback(f"✅ Successfully scraped {len(videos)} videos with yt-dlp!")

            return {
                "channel_name": username,
                "platform": "instagram",
                "total_entries": len(videos),
                "videos": videos
            }

        except Exception as e:
            if progress_callback:
                progress_callback(f"⚠️  yt-dlp failed: {str(e)}")
                progress_callback(f"💡 Falling back to Instaloader method...")

            # Fallback to Instaloader
            return self._scan_instagram_with_instaloader(username, max_videos, progress_callback)

    def _scan_instagram_with_instaloader(self, username, max_videos, progress_callback):
        """Scan Instagram profile using Instaloader (requires login, may hit rate limits)"""
        # Lazy load Instagram scraper
        if not self.instagram_scraper:
            from platforms.instagram import InstagramScraper
            self.instagram_scraper = InstagramScraper()

        # Check if logged in
        is_logged_in = self.instagram_scraper.loader.context.is_logged_in
        if progress_callback:
            progress_callback(f"[DEBUG] Session check: is_logged_in = {is_logged_in}")
            if is_logged_in:
                try:
                    username_from_session = self.instagram_scraper.loader.context.username
                    progress_callback(f"[DEBUG] Logged in as: {username_from_session}")
                except:
                    progress_callback(f"[DEBUG] Session exists but username unavailable")

        if not is_logged_in:
            raise Exception(
                "Instagram login required for profile scanning.\n"
                "Click the 'Login' button to authenticate first.\n\n"
                "If you already logged in, the session may have expired.\n"
                "Try logging in again from the Settings tab."
            )

        try:
            import instaloader

            # Get profile
            profile = instaloader.Profile.from_username(
                self.instagram_scraper.loader.context,
                username
            )

            if progress_callback:
                progress_callback(f"Scanning posts from @{username} (max {max_videos} videos)...")

            videos = []
            post_count = 0

            # Iterate through posts
            for post in profile.get_posts():
                post_count += 1

                # Rate limiting: pause every 10 posts
                if post_count % 10 == 0:
                    if progress_callback:
                        progress_callback(
                            f"Checked {post_count} posts, found {len(videos)} videos. "
                            f"Pausing 2s to avoid rate limits..."
                        )
                    time.sleep(2)

                # Only process video posts
                if post.is_video:
                    # Determine URL format based on post type
                    if post.typename == 'GraphVideo':
                        url = f"https://www.instagram.com/p/{post.shortcode}/"
                    else:
                        url = f"https://www.instagram.com/reel/{post.shortcode}/"

                    # Extract metadata
                    caption = post.caption if post.caption else ""

                    # Extract hashtags
                    hashtags = []
                    if caption:
                        hashtag_pattern = r'#(\w+)'
                        hashtags = re.findall(hashtag_pattern, caption)

                    videos.append({
                        "video_id": post.shortcode,
                        "title": caption[:100] + "..." if len(caption) > 100 else caption,
                        "username": username,
                        "caption": caption,
                        "hashtags": ", ".join(hashtags),
                        "url": url,
                        "duration": post.video_duration if hasattr(post, 'video_duration') else 0,
                        "likes": post.likes,
                        "views": post.video_view_count if hasattr(post, 'video_view_count') else 0
                    })

                    if progress_callback:
                        progress_callback(f"Found video {len(videos)}: {post.shortcode}")

                    # Stop if we've reached max
                    if len(videos) >= max_videos:
                        if progress_callback:
                            progress_callback(f"Reached maximum of {max_videos} videos")
                        break

                # Safety limit
                if post_count >= 200:
                    if progress_callback:
                        progress_callback(f"Checked {post_count} posts, stopping to avoid rate limits")
                    break

            if not videos:
                raise Exception(f"No videos found on profile @{username}")

            return {
                "channel_name": username,
                "platform": "instagram",
                "total_entries": len(videos),
                "videos": videos
            }

        except Exception as e:
            if "rate limit" in str(e).lower() or "401" in str(e):
                raise Exception(
                    f"Instagram rate limit exceeded.\n\n"
                    f"Please wait 10-15 minutes before trying again.\n"
                    f"Tip: Process individual video URLs instead of scanning entire profiles."
                )
            raise

    def scan_facebook_page(self, page_url, max_videos=None, progress_callback=None):
        """
        Fast scan of Facebook page/group

        Args:
            page_url: Facebook page or group URL
            max_videos: Maximum number of videos to scan
            progress_callback: Function to call with progress updates

        Returns:
            dict with page info and video list

        Note: Facebook scanning has limitations and may not work for all pages
        """
        if progress_callback:
            progress_callback("Fetching Facebook page entries...")
            progress_callback("⚠️  Note: Facebook scanning is limited to public pages")

        try:
            entries = self.get_playlist_entries(page_url)
            total = len(entries)

            if total == 0:
                # Try single video info
                info = self.get_video_info(page_url)
                if info:
                    entries = [info]
                    total = 1

            if total == 0:
                raise Exception(
                    "Could not fetch Facebook videos.\n\n"
                    "This may be because:\n"
                    "• The page is private or requires login\n"
                    "• The page has no videos\n"
                    "• Facebook is blocking automated access\n\n"
                    "Try processing individual video URLs instead."
                )

            # Extract page name from URL
            import re
            page_match = re.search(r'facebook\.com/([^/?]+)', page_url)
            page_name = page_match.group(1) if page_match else "Facebook"

            if progress_callback:
                progress_callback(f"Found {total} entries from {page_name}")

            videos = []

            for i, entry in enumerate(entries, 1):
                if max_videos and len(videos) >= max_videos:
                    break

                vid_id = entry.get("id", "")
                title = entry.get("title", "")
                url = entry.get("url") or entry.get("webpage_url", "")
                duration = entry.get("duration", 0)
                description = entry.get("description", "")

                if not url:
                    continue

                videos.append({
                    "video_id": vid_id,
                    "title": title,
                    "page_name": page_name,        # Use page_name for consistency
                    "description": description,     # Facebook uses description, not caption
                    "url": url,
                    "duration": duration
                })

                if progress_callback and i % 10 == 0:
                    progress_callback(f"Scanning... {i}/{total}")

            if not videos:
                raise Exception("No video metadata could be extracted from Facebook page")

            return {
                "channel_name": page_name,
                "platform": "facebook",
                "total_entries": total,
                "videos": videos
            }

        except Exception as e:
            if "Could not fetch" in str(e):
                raise
            raise Exception(
                f"Facebook scanning failed: {str(e)}\n\n"
                f"Facebook has strict access controls. Try:\n"
                f"• Processing individual video URLs\n"
                f"• Ensuring the page is public\n"
                f"• Using yt-dlp with cookies for authentication"
            )

    def scan_xiaohongshu_profile(self, profile_url, max_videos=50, progress_callback=None):
        """
        Scan Xiaohongshu profile using custom scraper

        Args:
            profile_url: Xiaohongshu profile URL
            max_videos: Maximum number of videos to scan (default: 50)
            progress_callback: Function to call with progress updates

        Returns:
            dict with profile info and video list
        """
        # Lazy load Xiaohongshu scraper
        from platforms.xiaohongshu import XiaohongshuScraper

        if progress_callback:
            progress_callback(f"🔍 Scraping Xiaohongshu profile...")

        scraper = XiaohongshuScraper()

        try:
            # Get all video URLs from profile
            video_urls = scraper.get_all_videos_from_profile(profile_url, max_videos=max_videos)

            if progress_callback:
                progress_callback(f"✅ Found {len(video_urls)} video URLs")

            # Extract user ID for naming
            import re
            user_id_match = re.search(r'user/profile/([a-f0-9]+)', profile_url)
            user_id = user_id_match.group(1) if user_id_match else "unknown"

            videos = []
            for i, url in enumerate(video_urls, 1):
                # Extract video ID from URL
                video_id = scraper.extract_video_id(url)

                if not video_id:
                    continue

                videos.append({
                    "video_id": video_id,
                    "title": f"Xiaohongshu Video {video_id[:8]}",
                    "username": user_id[:12],
                    "caption": "",
                    "url": url,
                    "duration": 0
                })

                if progress_callback and i % 10 == 0:
                    progress_callback(f"Processed {i}/{len(video_urls)} videos")

            if not videos:
                raise Exception("No videos found in profile")

            return {
                "channel_name": user_id[:12],
                "platform": "xiaohongshu",
                "total_entries": len(videos),
                "videos": videos
            }

        except Exception as e:
            raise Exception(f"Xiaohongshu profile scan failed: {str(e)}")

    def export_to_excel(self, scan_results, output_path, selected_columns=None):
        """
        Export scan results to Excel

        Args:
            scan_results: List of scan result dicts or single dict
            output_path: Path to save Excel file
            selected_columns: Dict of column names to boolean (True=include, False=exclude)
                            If None, include all columns

        Returns:
            Path to created Excel file or None if no data to export
        """
        if not isinstance(scan_results, list):
            scan_results = [scan_results]

        output_path = Path(output_path)

        # Check if there's any data to export
        has_data = any(result.get("videos", []) for result in scan_results)
        if not has_data:
            raise Exception("No videos to export - all scan results are empty")

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for result in scan_results:
                channel_name = result.get("channel_name", "Unknown")
                platform = result.get("platform", "unknown")
                videos = result.get("videos", [])

                if not videos:
                    continue

                # Determine columns based on platform
                if platform == "instagram":
                    # Instagram has extra fields: hashtags, likes, views
                    columns = [
                        "video_id", "title", "username", "caption",
                        "hashtags", "url", "duration", "likes", "views"
                    ]
                    col_widths = {
                        'A': 15,  # video_id
                        'B': 40,  # title
                        'C': 20,  # username
                        'D': 60,  # caption
                        'E': 30,  # hashtags
                        'F': 50,  # url
                        'G': 10,  # duration
                        'H': 10,  # likes
                        'I': 10   # views
                    }
                elif platform == "youtube":
                    # YouTube has channel_name and description (not username/caption)
                    columns = [
                        "video_id", "title", "channel_name", "description", "url", "duration", "view_count"
                    ]
                    col_widths = {
                        'A': 15,  # video_id
                        'B': 50,  # title
                        'C': 25,  # channel_name
                        'D': 60,  # description
                        'E': 50,  # url
                        'F': 10,  # duration
                        'G': 12   # view_count
                    }
                elif platform == "tiktok":
                    # TikTok has username and description
                    columns = [
                        "video_id", "title", "username", "description", "url",
                        "duration", "view_count"
                    ]
                    col_widths = {
                        'A': 15,  # video_id
                        'B': 50,  # title
                        'C': 20,  # username
                        'D': 60,  # description
                        'E': 50,  # url
                        'F': 10,  # duration
                        'G': 12   # view_count
                    }
                elif platform == "facebook":
                    # Facebook has page_name and description
                    columns = [
                        "video_id", "title", "page_name", "description", "url", "duration"
                    ]
                    col_widths = {
                        'A': 15,  # video_id
                        'B': 50,  # title
                        'C': 25,  # page_name
                        'D': 60,  # description
                        'E': 50,  # url
                        'F': 10   # duration
                    }
                elif platform == "xiaohongshu":
                    # Xiaohongshu has username and caption
                    columns = [
                        "video_id", "title", "username", "caption", "url", "duration"
                    ]
                    col_widths = {
                        'A': 15,  # video_id
                        'B': 50,  # title
                        'C': 20,  # username
                        'D': 60,  # caption
                        'E': 50,  # url
                        'F': 10   # duration
                    }
                else:
                    # Fallback for unknown platforms
                    columns = [
                        "video_id", "title", "username", "caption", "url", "duration"
                    ]
                    col_widths = {
                        'A': 15,  # video_id
                        'B': 50,  # title
                        'C': 20,  # username
                        'D': 60,  # caption
                        'E': 50,  # url
                        'F': 10   # duration
                    }

                # Create DataFrame with available columns
                # Filter to only include columns that exist in the data
                available_columns = []
                for col in columns:
                    if any(col in video for video in videos):
                        available_columns.append(col)

                # Further filter by user selection if provided
                if selected_columns:
                    available_columns = [col for col in available_columns
                                        if selected_columns.get(col, True)]

                df = pd.DataFrame(videos, columns=available_columns)

                # Sanitize sheet name
                sheet_name = self.sanitize_sheet_name(channel_name)

                # Write to Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # Format worksheet
                worksheet = writer.sheets[sheet_name]

                # Set column widths
                for col_letter, width in col_widths.items():
                    try:
                        worksheet.column_dimensions[col_letter].width = width
                    except:
                        pass

                # Enable text wrapping
                for row in worksheet.iter_rows():
                    for cell in row:
                        cell.alignment = Alignment(wrap_text=True, vertical='top')

        return str(output_path)

    def export_urls_to_txt(self, scan_results, output_path):
        """
        Export just URLs to TXT file for later processing

        Args:
            scan_results: Scan result dict or list
            output_path: Path to save TXT file

        Returns:
            Path to created TXT file
        """
        if not isinstance(scan_results, list):
            scan_results = [scan_results]

        output_path = Path(output_path)

        urls = []
        for result in scan_results:
            videos = result.get("videos", [])
            for video in videos:
                urls.append(video["url"])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(urls))

        return str(output_path)
