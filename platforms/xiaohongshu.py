import re
import requests
import json
import time
from urllib.parse import urlparse
from pathlib import Path
from http.cookiejar import MozillaCookieJar

class XiaohongshuScraper:
    SUPPORTED_DOMAINS = ['xiaohongshu.com', 'rednote.com']

    def __init__(self, profile_url=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.xiaohongshu.com/',
        }
        self.base_url = self._detect_base_url(profile_url)
        self.domain = self._extract_domain(profile_url) if profile_url else 'xiaohongshu.com'
        self.cookies_file = Path(__file__).parent.parent / "cookies.txt"
        self.session = self._create_session()

    def _detect_base_url(self, url):
        """Return the base URL for requests.

        rednote.com is the canonical domain for programmatic access;
        xiaohongshu.com returns a security-limited (安全限制) error page
        for individual /explore/{noteId} requests.  The two domains share
        the same backend IP and xsec_tokens are cross-compatible.
        """
        return 'https://www.rednote.com'

    def _extract_domain(self, url):
        """Extract the raw domain name from a URL (for display only)"""
        if url:
            match = re.search(r'(?:www\.)?([a-z0-9-]+\.[a-z]+)', url)
            if match:
                return match.group(1)
        return 'rednote.com'

    def _create_session(self):
        """Create a requests session with cookies if available"""
        session = requests.Session()
        session.headers.update(self.headers)

        # Load cookies if available
        if self.cookies_file.exists():
            try:
                import http.cookiejar
                cookie_jar = MozillaCookieJar(str(self.cookies_file))
                cookie_jar.load(ignore_discard=True, ignore_expires=True)

                # Clone xiaohongshu.com cookies as rednote.com cookies so
                # they are sent when we request www.rednote.com
                for c in list(cookie_jar):
                    if 'xiaohongshu.com' in c.domain:
                        clone = http.cookiejar.Cookie(
                            version=c.version, name=c.name, value=c.value,
                            port=c.port, port_specified=c.port_specified,
                            domain='rednote.com', domain_specified=True,
                            domain_initial_dot=False,
                            path=c.path, path_specified=c.path_specified,
                            secure=c.secure, expires=c.expires,
                            discard=c.discard, comment=c.comment,
                            comment_url=c.comment_url,
                            rest=getattr(c, 'rest', {'HttpOnly': None}),
                        )
                        cookie_jar.set_cookie(clone)

                session.cookies = cookie_jar
                print(f"[+] Loaded cookies from {self.cookies_file}")
            except Exception as e:
                print(f"[!] Could not load cookies: {e}")

        return session

    def extract_video_id(self, url):
        """Extract video ID from Xiaohongshu/RedNote URLs"""
        patterns = [
            r'(?:xiaohongshu|rednote)\.com/explore/([a-f0-9]+)',
            r'(?:xiaohongshu|rednote)\.com/discovery/item/([a-f0-9]+)',
            r'xhslink\.com/\w+/([a-f0-9]+)',
            r'user/profile/[\w]+\?.*note_id=([a-f0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Handle shortened xhslink.com URLs
        if 'xhslink.com' in url:
            try:
                response = requests.head(url, headers=self.headers, allow_redirects=True, timeout=10)
                return self.extract_video_id(response.url)
            except:
                pass

        # Try to extract any hex string that looks like a note ID
        hex_match = re.search(r'([a-f0-9]{24})', url)
        if hex_match:
            return hex_match.group(1)

        return None

    def get_post_metadata(self, url):
        """Get metadata for a Xiaohongshu post"""
        video_id = self.extract_video_id(url)
        if not video_id:
            return None, "", ""

        try:
            # Basic metadata extraction
            # Note: Xiaohongshu has anti-scraping measures, so detailed metadata
            # extraction may require cookies or API access
            # For now, return basic info and let yt-dlp handle the download
            return video_id, "", ""
        except Exception:
            return video_id, "", ""

    def get_all_videos_from_profile(self, user_url, max_videos=None):
        """Get all videos from a Xiaohongshu user profile"""
        # Keep the original rednote.com domain — xiaohongshu.com has a
        # security page (安全限制 url is invalid 300017) for explore URLs.
        self.domain = self._extract_domain(user_url)
        self.base_url = self._detect_base_url(user_url)

        # Normalise any xiaohongshu.com URLs → rednote.com
        user_url = re.sub(r'(?:www\.)?xiaohongshu\.com', 'www.rednote.com', user_url)
        print(f"[*] Scraping Xiaohongshu/RedNote profile: {user_url}")

        try:
            # Extract user ID from profile URL
            user_id_match = re.search(r'user/profile/([a-f0-9]+)', user_url)
            if not user_id_match:
                raise ValueError("Invalid Xiaohongshu profile URL. Expected format: rednote.com/user/profile/USER_ID")

            user_id = user_id_match.group(1)

            # Method 1: Try Selenium with scrolling to get ALL videos (most reliable)
            print(f"[*] Trying Selenium with scrolling to get all videos...")
            video_urls = self._fetch_with_selenium_scrolling(user_url, max_videos)

            if video_urls:
                print(f"[+] Found {len(video_urls)} video(s) via Selenium scrolling")
                return video_urls

            # Method 2: Try yt-dlp
            print(f"[!] Selenium failed, trying yt-dlp...")
            video_urls = self._fetch_with_ytdlp(user_url, max_videos or 50)

            if video_urls:
                print(f"[+] Found {len(video_urls)} video(s) via yt-dlp")
                return video_urls

            # Method 3: Fall back to static HTML scraping (limited to ~30 videos)
            print(f"[!] yt-dlp failed, trying static HTML scraping (limited)...")
            return self._fetch_with_html_scraping(user_url, user_id, max_videos or 50)

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Xiaohongshu profile: {str(e)}")
        except Exception as e:
            raise Exception(f"Error scraping Xiaohongshu profile: {str(e)}")

    def _fetch_with_ytdlp(self, user_url, max_videos=50):
        """Try to fetch profile videos using yt-dlp"""
        import subprocess
        import sys

        try:
            # Normalize — use rednote.com (xiaohongshu.com returns security blocks)
            yt_url = re.sub(r'(?:www\.)?xiaohongshu\.com', 'www.rednote.com', user_url)

            # Build yt-dlp command
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--flat-playlist",
                "--dump-json",
                "--no-warnings",
                yt_url
            ]

            # Add cookies if available
            if self.cookies_file.exists():
                cmd.extend(["--cookies", str(self.cookies_file)])

            # Run yt-dlp
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            video_urls = []
            for line in proc.stdout:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    video_id = entry.get('id', '')

                    # Try to get the full URL with token from yt-dlp
                    url = entry.get('url') or entry.get('webpage_url')

                    # If no URL provided, construct it
                    if not url:
                        url = f"{self.base_url}/explore/{video_id}"

                    # Check if URL has xsec_token, if not and we have it in entry, add it
                    if 'xsec_token' not in url and video_id:
                        # Try to extract token from entry
                        xsec_token = entry.get('xsec_token') or entry.get('xsecToken')
                        if xsec_token:
                            url = f"{self.base_url}/explore/{video_id}?xsec_token={xsec_token}&xsec_source=pc_user"
                            print(f"  -> Found: {video_id} with token from yt-dlp")
                        else:
                            print(f"  -> Found: {video_id} (no token in yt-dlp output)")
                    else:
                        print(f"  -> Found: {video_id}")

                    if url:
                        video_urls.append(url)

                    if len(video_urls) >= max_videos:
                        proc.kill()
                        break
                except json.JSONDecodeError:
                    continue

            proc.wait()
            return video_urls

        except Exception as e:
            print(f"[!]  yt-dlp method failed: {e}")
            return []

    def _fetch_with_selenium_scrolling(self, user_url, max_videos=None):
        """Use Selenium + CDP to intercept the signed API responses

        The profile page SSR on both xiaohongshu.com and rednote.com sets
        noteId to \"\" for ALL notes — note IDs are only returned by the
        signed API (webapi.rednote.com/api/sns/web/v1/user_posted) which
        requires dynamic X-S / X-T headers generated by client-side JS.

        This method loads the profile in a real Chrome session, waits for
        the SPA to call the API, and captures the JSON responses via CDP
        performance logging.  Each API call returns ~30 notes with real
        noteId + xsecToken pairs.  Scrolling the page triggers more calls.
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            import time, json

            print(f"[*] Using Selenium + CDP to intercept API responses...")

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            # Enable CDP performance logging to catch API responses
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

            driver = webdriver.Chrome(options=chrome_options)

            # Override webdriver detection properties
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
                '''
            })

            try:
                # Load cookies into browser
                if self.cookies_file.exists():
                    print(f"[*] Loading cookies into browser...")
                    driver.get(self.base_url)

                    from http.cookiejar import MozillaCookieJar
                    cookie_jar = MozillaCookieJar(str(self.cookies_file))
                    cookie_jar.load(ignore_discard=True, ignore_expires=True)

                    for cookie in cookie_jar:
                        if not any(d in cookie.domain for d in self.SUPPORTED_DOMAINS):
                            continue
                        domain = cookie.domain.lstrip('.')
                        target_domain = None
                        if 'rednote.com' in domain:
                            target_domain = domain
                        elif 'xiaohongshu.com' in domain:
                            suffix = domain.replace('xiaohongshu.com', '')
                            if suffix in ('', 'www.', '.'):
                                target_domain = suffix + 'rednote.com'
                        if target_domain:
                            c = {
                                'name': cookie.name, 'value': cookie.value,
                                'domain': target_domain, 'path': cookie.path,
                                'secure': cookie.secure,
                            }
                            if cookie.expires:
                                c['expiry'] = int(cookie.expires)
                            try:
                                driver.add_cookie(c)
                            except:
                                pass

                # Navigate to profile
                print(f"[*] Loading profile page to trigger API calls...")
                driver.get(user_url)

                # Collect note data from user_posted API responses by polling
                # the performance log.  CDP buffers response bodies only
                # briefly, so we poll frequently (every 500ms) to catch them.
                seen_ids = set()
                all_notes = []
                tried_req_ids = set()
                seen_pages = set()  # track cursor values to detect new pages

                def poll_api_responses():
                    """Check performance logs for user_posted API responses
                    and extract note data before the CDP buffer evicts them."""
                    count = 0
                    logs = driver.get_log('performance')
                    for entry in logs:
                        try:
                            msg = json.loads(entry['message'])
                            evt = msg.get('message', {})
                            if evt.get('method') != 'Network.responseReceived':
                                continue
                            url = evt.get('params', {}).get('response', {}).get('url', '')
                            if 'user_posted' not in url:
                                continue
                            req_id = evt.get('params', {}).get('requestId', '')
                            if req_id in tried_req_ids:
                                continue
                            tried_req_ids.add(req_id)
                            try:
                                body = driver.execute_cdp_cmd(
                                    'Network.getResponseBody', {'requestId': req_id}
                                )
                                raw = body.get('body', '')
                                if len(raw) < 10:
                                    continue
                                data = json.loads(raw)
                                notes = data.get('data', {}).get('notes', [])
                                if not notes:
                                    # Try 'items' field (different API version)
                                    notes = data.get('data', {}).get('items', [])
                                for note in notes:
                                    nid = note.get('note_id', '') or note.get('id', '')
                                    if nid and nid not in seen_ids:
                                        seen_ids.add(nid)
                                        all_notes.append(note)
                                        count += 1
                            except:
                                pass
                        except:
                            pass
                    return count

                # Poll during initial load (up to ~15 seconds)
                for _ in range(30):
                    n = poll_api_responses()
                    if n:
                        print(f"   -> +{n} notes from API")
                    if len(all_notes) >= 30 and _ > 10:
                        break
                    time.sleep(0.5)

                # Scroll to trigger pagination
                print(f"[*] Scrolling to load more notes...")
                last_height = driver.execute_script("return document.body.scrollHeight")
                no_change_count = 0
                scroll_count = 0

                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    scroll_count += 1

                    # Poll for new API responses after scroll (up to ~5 sec)
                    for _ in range(10):
                        n = poll_api_responses()
                        if n:
                            print(f"   -> +{n} notes from API after scroll")
                        time.sleep(0.5)

                    if len(all_notes) > 0:
                        print(f"   -> Collected {len(all_notes)} notes total (scroll {scroll_count})")

                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        no_change_count += 1
                        if no_change_count >= 4:
                            print(f"[*] Reached end of profile after {scroll_count} scrolls")
                            break
                    else:
                        no_change_count = 0
                        last_height = new_height

                    if scroll_count > 100:
                        print(f"[*] Reached safety limit of 100 scrolls")
                        break

                    if max_videos and len(all_notes) >= max_videos:
                        print(f"[*] Reached target of {max_videos} videos")
                        break

                # Build explore URLs from real noteId + xsecToken pairs
                video_urls = []
                for note in all_notes:
                    note_id = note.get('note_id', '') or note.get('id', '')
                    token = note.get('xsec_token', '')
                    if note_id:
                        if token:
                            url = f"{self.base_url}/explore/{note_id}?xsec_token={token}&xsec_source=pc_user"
                        else:
                            url = f"{self.base_url}/explore/{note_id}"
                        video_urls.append(url)

                print(f"[+] Extracted {len(video_urls)} video URLs via API interception")
                return video_urls

            finally:
                driver.quit()

        except Exception as e:
            print(f"[!] Selenium API interception failed: {e}")
            return []

    def _fetch_with_html_scraping(self, user_url, user_id, max_videos=50):
        """Fallback: Scrape HTML directly (limited to first page)"""
        print(f"[*] Fetching profile page HTML...")

        # Use session with cookies
        response = self.session.get(user_url, timeout=30)
        response.raise_for_status()

        html_content = response.text

        # Debug: Save HTML to file for inspection
        debug_file = Path(__file__).parent.parent / "debug_xiaohongshu.html"
        debug_file.write_text(html_content, encoding='utf-8')
        print(f"[DEBUG] Debug: Saved HTML to {debug_file}")

        # Extract video URLs from the page
        # Xiaohongshu embeds data in window.__INITIAL_STATE__ JSON
        video_urls = []

        # 1. Extract from __INITIAL_STATE__ JSON (fixes for
        #    undefined → null, unbalanced braces, trailing commas)
        state_match = re.search(
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?)</script>',
            html_content, re.DOTALL
        )

        if state_match:
            try:
                raw = state_match.group(1).rstrip(';').strip()

                # Balance braces — extract only the top-level JSON object
                brace_count = 0
                end_pos = 0
                for i, ch in enumerate(raw):
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                if end_pos == 0:
                    raise ValueError("Unbalanced braces in __INITIAL_STATE__")
                json_str = raw[:end_pos]

                # Fix JS-to-JSON conversions that break json.loads
                json_str = re.sub(r':undefined', ':null', json_str)
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # trailing commas
                state_data = json.loads(json_str)

                print(f"[+] Parsed __INITIAL_STATE__ ({len(json_str)} bytes)")

                # Save for debugging
                debug_json = Path(__file__).parent.parent / "debug_xiaohongshu.json"
                debug_json.write_text(
                    json.dumps(state_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )

                # Collect notes from the state tree.  Xiaohongshu stores
                # user-profile notes in user.notes as a list of pages,
                # where each page is a list of {noteCard, xsecToken, …}
                # items.  Newer SSR no longer includes noteId (it is
                # always "") — note IDs are only returned by a signed
                # API the SPA calls after mount.
                raw_notes = []
                user_state = state_data.get('user', {})
                if 'notes' in user_state:
                    pages = user_state['notes']
                    if isinstance(pages, list):
                        for page in pages:
                            if isinstance(page, list):
                                raw_notes.extend(page)

                if not raw_notes:
                    # Fallback deep search
                    def deep_search(obj, depth=0):
                        if depth > 5:
                            return []
                        found = []
                        if isinstance(obj, dict):
                            if 'noteCard' in obj and 'xsecToken' in obj:
                                found.append(obj)
                            for v in obj.values():
                                found.extend(deep_search(v, depth + 1))
                        elif isinstance(obj, list):
                            for item in obj:
                                found.extend(deep_search(item, depth + 1))
                        return found
                    raw_notes = deep_search(state_data)

                print(f"[+] Found {len(raw_notes)} note entries in state")

                # Extract — noteId may be empty string, so try to
                # scavenge a 24-hex-char ID from cover image URLs
                # (the first 24 chars of a CDN hash often match)
                seen = set()
                for item in raw_notes:
                    if isinstance(item, dict):
                        # Walk into noteCard if present
                        nc = item.get('noteCard') or item
                        note_id = nc.get('noteId') or item.get('id') or ''
                        xsec = nc.get('xsecToken') or item.get('xsecToken') or ''
                        cover = nc.get('cover', {}) or {}

                        # DISABLED: cover-URL hash prefix fallback.  CDN URLs
                        # contain 32-hex-char hashes (e.g. sns-webpic-qc.xhscdn.com/.../8e6894d16bd29f13e4ba5ee1e0bc28/...).
                        # Their first 24 chars are NOT valid noteIds — they
                        # produce 404 errors (error 300031).  Note IDs are
                        # only available after JS execution.

                        if note_id and note_id not in seen:
                            seen.add(note_id)
                            if xsec:
                                url = f"{self.base_url}/explore/{note_id}?xsec_token={xsec}&xsec_source=pc_user"
                            else:
                                url = f"{self.base_url}/explore/{note_id}"
                            video_urls.append(url)

                            if len(video_urls) >= max_videos:
                                break

            except (json.JSONDecodeError, ValueError) as e:
                print(f"[!]  __INITIAL_STATE__ parse failed: {e}")
        else:
            print(f"[!]  No __INITIAL_STATE__ found in HTML")

        # 2. Direct explore-URL extraction from HTML (unlikely with SSR
        #    but cheap to try)
        if len(video_urls) == 0:
            print(f"[*] Looking for explore URLs in HTML...")
            for m in re.finditer(r'href="(/explore/[a-f0-9]+(?:\?[^"]*)?)"', html_content):
                video_urls.append(f"{self.base_url}{m.group(1)}")
                if len(video_urls) >= max_videos:
                    break

        if len(video_urls) == 0:
            instruct = (
                "Could not extract any videos from Xiaohongshu profile.\n\n"
                "Xiaohongshu no longer exposes note IDs in server-rendered HTML on "
                "either xiaohongshu.com or rednote.com.  The notes are only loaded "
                "via signed API calls after JavaScript executes.\n\n"
                "Workarounds:\n"
                "1. Make sure ChromeDriver is installed and Selenium can run\n"
                "2. Open the profile in your browser, scroll to load all videos, "
                "then copy the explore URLs from the browser's developer tools\n"
                "3. Manually copy each video URL from the browser address bar\n"
                "4. Export cookies from xiaohongshu.com via 'Get cookies.txt LOCALLY' "
                "extension and place cookies.txt in the project root"
            )
            raise Exception(instruct)

        print(f"[+] Found {len(video_urls)} video(s) from profile")

        # Add delay to avoid rate limiting
        time.sleep(2)

        return video_urls
