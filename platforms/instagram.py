import instaloader
import re
import time
from pathlib import Path


def ig_session_status(cookies_path=None):
    """Single source of truth for Instagram auth.

    Reads data/cookies.txt (the ONE file yt-dlp downloads with) and reports
    whether it holds a non-expired Instagram `sessionid`. Returns a dict:
        {"logged_in": bool, "user_id": str|None, "reason": str}

    Both the GUI status line and the downloader use this so they can never
    disagree again — no more "Authenticated as @x" while downloads 401.
    """
    import http.cookiejar
    import time as _t

    if cookies_path is None:
        cookies_path = Path(__file__).parent.parent / "data" / "cookies.txt"
    cookies_path = Path(cookies_path)

    if not cookies_path.exists():
        return {"logged_in": False, "user_id": None, "reason": "no cookies.txt"}

    try:
        jar = http.cookiejar.MozillaCookieJar(str(cookies_path))
        jar.load(ignore_expires=True, ignore_discard=True)
    except Exception as e:
        return {"logged_in": False, "user_id": None, "reason": f"unreadable cookies.txt ({e})"}

    sessionid = None
    ds_user_id = None
    expires = None
    for c in jar:
        if "instagram.com" not in (c.domain or ""):
            continue
        if c.name == "sessionid":
            sessionid = c.value
            expires = c.expires
        elif c.name == "ds_user_id":
            ds_user_id = c.value

    if not sessionid:
        return {"logged_in": False, "user_id": ds_user_id, "reason": "no sessionid in cookies.txt"}
    if expires and expires < int(_t.time()):
        return {"logged_in": False, "user_id": ds_user_id, "reason": "sessionid expired — re-login"}

    return {"logged_in": True, "user_id": ds_user_id, "reason": "ok"}


class InstagramScraper:
    def __init__(self):
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            sleep=True,  # Enable sleep between requests
            quiet=False
        )
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.username_file = self.data_dir / "ig_username.txt"
        self._load_session()

    def _load_session(self):
        """Load saved Instagram session — from saved file or cookies.txt"""
        session_loaded = False

        if self.username_file.exists():
            try:
                with open(self.username_file, 'r') as f:
                    username = f.read().strip()
                if username:
                    self.loader.load_session_from_file(username)
                    if self.loader.context.is_logged_in:
                        self._sync_session_to_cookiestxt()
                        session_loaded = True
            except Exception:
                pass  # instaloader session failed — fall through to cookies.txt

        if not session_loaded:
            self._import_session_from_cookiestxt()

    def _import_session_from_cookiestxt(self):
        """Import Instagram cookies from cookies.txt into instaloader's session."""
        import http.cookiejar

        cookies_path = self.data_dir / "cookies.txt"
        if not cookies_path.exists():
            return

        try:
            # Load Netscape-format cookies
            jar = http.cookiejar.MozillaCookieJar(str(cookies_path))
            jar.load(ignore_expires=True, ignore_discard=True)

            # Find Instagram-specific cookies we need
            insta_cookies = {}
            for c in jar:
                if 'instagram.com' in c.domain:
                    insta_cookies[c.name] = c.value

            sessionid = insta_cookies.get('sessionid')
            ds_user_id = insta_cookies.get('ds_user_id')
            if not sessionid:
                return  # No valid Instagram session

            # Set cookies on instaloader's underlying requests session
            session = self.loader.context._session
            for name, value in insta_cookies.items():
                session.cookies.set(name, value, domain='.instagram.com', path='/')

            # Try to get a display name from the cookies.txt username if saved
            username_guess = None
            if self.username_file.exists():
                try:
                    with open(self.username_file, 'r') as f:
                        username_guess = f.read().strip()
                except Exception:
                    pass

            if username_guess:
                self.loader.context.username = username_guess
            elif ds_user_id:
                # Use numeric user ID as fallback — enough for login check
                self.loader.context.username = ds_user_id

            print(f"[DEBUG] Session imported from cookies.txt: sessionid={sessionid[:20]}...")
        except Exception:
            pass  # Never let cookie import break the app

    def login(self, username, password):
        try:
            # Login to Instagram
            self.loader.login(username, password)

            # Save username for future session loading
            with open(self.username_file, 'w') as f:
                f.write(username)

            # Also export sessionid to cookies.txt so yt-dlp can use it
            self._sync_session_to_cookiestxt()

            print(f"[DEBUG] Login successful, session saved for: {username}")
            print(f"[DEBUG] Session logged in: {self.loader.context.is_logged_in}")

            return True
        except Exception as e:
            raise Exception(f"Instagram login failed: {str(e)}")

    def _sync_session_to_cookiestxt(self):
        """Copy instaloader's full live Instagram cookie set into cookies.txt
        so yt-dlp (the downloader) shares the SAME login. cookies.txt is the
        single source of truth — this keeps it in step with the live session.

        Safety: if the live session has no sessionid, this is a no-op. It never
        clears an existing valid sessionid (that's what caused silent logouts)."""
        try:
            from http.cookiejar import MozillaCookieJar
            import http.cookiejar
            import time

            cookies_path = self.data_dir / "cookies.txt"

            session = self.loader.context._session
            if not session:
                return

            # Gather every instagram.com cookie from the live session
            live_ig = {}
            for cookie in session.cookies:
                if 'instagram.com' in str(cookie.domain):
                    live_ig[cookie.name] = cookie.value

            if not live_ig.get('sessionid'):
                return  # No valid live session — never wipe what's on disk

            # Load existing cookies.txt and keep all NON-instagram cookies
            jar = MozillaCookieJar(str(cookies_path))
            if cookies_path.exists():
                try:
                    jar.load(ignore_expires=True, ignore_discard=True)
                except Exception:
                    pass

            # Drop stale instagram cookies, then write the fresh full set
            for name in list(live_ig.keys()):
                try:
                    jar.clear('.instagram.com', '/', name)
                except KeyError:
                    pass

            expiry = int(time.time()) + 365 * 86400
            for name, value in live_ig.items():
                jar.set_cookie(http.cookiejar.Cookie(
                    version=0, name=name, value=value,
                    port=None, port_specified=False,
                    domain='.instagram.com', domain_specified=True,
                    domain_initial_dot=True,
                    path='/', path_specified=True,
                    secure=True, expires=expiry, discard=False,
                    comment=None, comment_url=None, rest={}, rfc2109=False,
                ))

            jar.save(ignore_expires=True, ignore_discard=True)
        except Exception:
            pass  # Never let cookie sync break the app

    def extract_video_id(self, url):
        # Extract shortcode from URL
        # Supports both formats:
        # instagram.com/reel/ABC123 (direct)
        # instagram.com/username/reel/ABC123 (with username)
        patterns = [
            r'instagram\.com/(?:[^/]+/)?reel/([A-Za-z0-9_-]+)',
            r'instagram\.com/(?:[^/]+/)?p/([A-Za-z0-9_-]+)',
            r'instagram\.com/(?:[^/]+/)?tv/([A-Za-z0-9_-]+)',
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
            # Fetch post metadata using Instaloader
            post = instaloader.Post.from_shortcode(self.loader.context, video_id)

            # Extract caption
            caption = post.caption if post.caption else ""

            # Extract hashtags from caption
            hashtags = ""
            if caption:
                hashtag_pattern = r'#(\w+)'
                found_hashtags = re.findall(hashtag_pattern, caption)
                hashtags = ", ".join(found_hashtags) if found_hashtags else ""

            return video_id, caption, hashtags

        except Exception as e:
            # If metadata fetch fails, still return video_id so download can proceed
            print(f"Warning: Could not fetch Instagram metadata: {str(e)}")
            return video_id, "", ""

    def get_all_videos_from_profile(self, username, max_videos=50):
        """Get video URLs from an Instagram profile with rate limiting"""
        try:
            # Check if logged in
            if not self.loader.context.is_logged_in:
                raise Exception(
                    "Not logged in to Instagram.\n"
                    "Click the 'Login' button to authenticate."
                )

            print(f"Fetching profile: @{username}")

            # Get profile
            profile = instaloader.Profile.from_username(self.loader.context, username)

            video_urls = []
            post_count = 0

            print(f"Scanning posts for videos (max {max_videos})...")

            # Iterate through posts with limit
            for post in profile.get_posts():
                post_count += 1

                # Add delay every 10 posts to avoid rate limiting
                if post_count % 10 == 0:
                    print(f"Checked {post_count} posts, found {len(video_urls)} videos. Pausing to avoid rate limits...")
                    time.sleep(2)  # 2 second pause every 10 posts

                # Check if it's a video (reel, IGTV, or video post)
                if post.is_video:
                    # Construct URL
                    if post.typename == 'GraphVideo':
                        url = f"https://www.instagram.com/p/{post.shortcode}/"
                    elif post.typename == 'GraphSidecar':
                        # May contain videos in carousel
                        url = f"https://www.instagram.com/p/{post.shortcode}/"
                    else:
                        url = f"https://www.instagram.com/reel/{post.shortcode}/"

                    video_urls.append(url)
                    print(f"Found video: {post.shortcode}")

                    # Stop if we've reached max videos
                    if len(video_urls) >= max_videos:
                        print(f"Reached maximum of {max_videos} videos")
                        break

                # Safety limit: stop after checking 200 posts
                if post_count >= 200:
                    print(f"Checked {post_count} posts, stopping to avoid rate limits")
                    break

            if not video_urls:
                raise Exception(f"No videos found on profile @{username}")

            print(f"Total videos found: {len(video_urls)}")
            return video_urls

        except instaloader.exceptions.ProfileNotExistsException:
            raise Exception(f"Instagram profile '@{username}' does not exist")
        except instaloader.exceptions.LoginRequiredException:
            raise Exception(
                "Instagram login required.\n"
                "Click the 'Login' button to authenticate."
            )
        except instaloader.exceptions.QueryReturnedBadRequestException as e:
            raise Exception(
                "Instagram rate limit exceeded.\n"
                "Please wait 10-15 minutes before trying again.\n"
                "Tip: Try processing individual video URLs instead of entire profiles."
            )
        except instaloader.exceptions.ConnectionException as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                raise Exception(
                    "Instagram rate limit exceeded (401 Unauthorized).\n\n"
                    "Instagram is blocking requests. Please:\n"
                    "1. Wait 10-15 minutes\n"
                    "2. Try again with a fresh login\n"
                    "3. Or process individual video URLs instead\n\n"
                    "For better results, use cookies.txt method (see INSTAGRAM_LOGIN_GUIDE.md)"
                )
            raise Exception(f"Instagram connection error: {str(e)}")
        except Exception as e:
            if "Not logged in" in str(e) or "Login" in str(e):
                raise
            if "401" in str(e) or "Unauthorized" in str(e) or "rate" in str(e).lower():
                raise Exception(
                    "Instagram rate limit hit.\n\n"
                    "Wait 10-15 minutes and try again.\n"
                    "Or process videos one by one using direct URLs."
                )
            raise Exception(f"Failed to scrape Instagram profile: {str(e)}")


def scrape_instagram_account_urls(username, cookies_path=None, progress_callback=None):
    """
    Scrape ALL video/post URLs from an Instagram account using Instaloader.
    Uses the same cookies.txt session as InstagramScraper.

    Args:
        username: Instagram username (without @)
        cookies_path: Path to cookies.txt (default: data/cookies.txt)
        progress_callback: Optional callable(str) for progress

    Returns:
        list of full Instagram URLs (canonical, deduplicated)
    """
    import time
    from pathlib import Path

    if cookies_path is None:
        cookies_path = Path(__file__).parent.parent / "data" / "cookies.txt"
    cookies_path = Path(cookies_path)

    if not cookies_path.exists():
        raise Exception(
            "cookies.txt not found!\n"
            "Please login to Instagram first in Settings → Instagram Settings."
        )

    # Check session is valid
    status = ig_session_status(str(cookies_path))
    if not status["logged_in"]:
        raise Exception(
            f"Instagram session expired or missing: {status['reason']}\n"
            "Please re-login in Settings → Instagram Settings."
        )

    def _log(msg):
        if progress_callback:
            progress_callback(msg)

    _log(f"📡 Fetching posts from @{username} via Instaloader...")
    _log("⚠️  This may take a minute — Instagram rate-limits API calls.")

    # Reuse the existing InstagramScraper to get its loaded session
    try:
        scraper = InstagramScraper()
    except Exception as e:
        raise Exception(f"Failed to initialize Instagram session: {e}")

    if not scraper.loader.context.is_logged_in:
        raise Exception(
            "Instaloader session not logged in.\n"
            "Please login via Settings → Instagram Settings first."
        )

    try:
        import instaloader
        profile = instaloader.Profile.from_username(scraper.loader.context, username)
    except instaloader.exceptions.ProfileNotExistsException:
        raise Exception(f"Instagram profile '@{username}' does not exist")
    except instaloader.exceptions.LoginRequiredException:
        raise Exception("Instagram login required — please re-login in Settings.")
    except Exception as e:
        raise Exception(f"Failed to load profile: {e}")

    video_urls = []
    post_count = 0

    _log(f"📊 Scanning posts for videos...")

    for post in profile.get_posts():
        post_count += 1

        # Rate limiting: pause every 15 posts
        if post_count % 15 == 0:
            _log(f"  Checked {post_count} posts, found {len(video_urls)} videos (pausing for rate limits)...")
            time.sleep(2)

        if post.is_video:
            # Construct clean canonical URL
            if post.typename == 'GraphVideo':
                url = f"https://www.instagram.com/p/{post.shortcode}/"
            elif post.typename == 'GraphSidecar':
                url = f"https://www.instagram.com/p/{post.shortcode}/"
            else:
                url = f"https://www.instagram.com/reel/{post.shortcode}/"

            video_urls.append(url)

            if len(video_urls) % 20 == 0:
                _log(f"  ✅ {len(video_urls)} videos found so far...")

        # Safety limit: stop after checking 500 posts to avoid rate limiting
        if post_count >= 500:
            _log(f"⚠️  Reached 500-post safety limit (found {len(video_urls)} videos)")
            break

    if not video_urls:
        raise Exception(
            f"No videos found on profile @{username}\n\n"
            "Possible reasons:\n"
            "  • The account may have no video posts\n"
            "  • The account may be private\n"
            "  • Instagram API may be rate-limiting\n\n"
            f"Try visiting https://www.instagram.com/{username}/ in a browser."
        )

    _log(f"✅ Scraped {len(video_urls)} videos from @{username} (scanned {post_count} posts)")
    return sorted(video_urls)
