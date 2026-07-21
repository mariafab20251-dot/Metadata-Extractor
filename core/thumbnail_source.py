"""
Thumbnail Source — download the *original* published thumbnail for a video.
============================================================================
Platform-pluggable: each source knows how to (a) recognise its URLs and
(b) fetch the highest-quality published thumbnail.  YouTube is implemented
now; TikTok / Instagram are stubbed so they can be filled in later without
touching the callers.

A "proper" thumbnail means the uploader published a real designed cover
image (e.g. YouTube ``maxresdefault.jpg``, a 1280x720 custom upload).  Auto
generated frame grabs (``hqdefault`` etc.) are NOT proper — the caller then
falls back to grabbing a frame from the video itself.

Public API
----------
    fetch_original_thumbnail(url, out_path, log=None) -> dict
        {"path": str|None, "is_proper": bool, "platform": str, "error": str}
"""

from __future__ import annotations

import re
from pathlib import Path


def _noop_log(level, msg):
    print(f"[{level.upper()}] {msg}")


# ── Platform detection ───────────────────────────────────────────────────

def detect_platform(url: str) -> str:
    """Return 'youtube' | 'tiktok' | 'instagram' | 'unknown'."""
    u = (url or "").lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "tiktok.com" in u:
        return "tiktok"
    if "instagram.com" in u:
        return "instagram"
    return "unknown"


def _youtube_id(url: str) -> str:
    m = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})', url or "")
    return m.group(1) if m else ""


# ── Downloaders ──────────────────────────────────────────────────────────

def _download(url: str, out_path: Path, log, timeout: int = 30) -> bool:
    """GET *url* into *out_path*.  Returns True on a non-empty 200 image."""
    import requests
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        log('warn', f'Thumbnail source: request failed — {e}')
        return False
    if r.status_code != 200 or not r.content:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(r.content)
    return out_path.is_file() and out_path.stat().st_size > 1024


def _fetch_youtube(url: str, out_path: Path, log) -> dict:
    """YouTube: prefer maxresdefault (custom-upload 1280x720).

    ``maxresdefault.jpg`` exists ONLY when the uploader set a real thumbnail
    (or the video is HD).  ``sddefault``/``hqdefault`` always exist but are
    auto frame grabs — so maxres present == "proper" designed thumbnail.
    """
    vid = _youtube_id(url)
    if not vid:
        return {"path": None, "is_proper": False, "platform": "youtube",
                "error": "could not parse YouTube video id"}

    base = f"https://i.ytimg.com/vi/{vid}"
    # maxresdefault → proper designed thumbnail; others → auto grab (not proper)
    if _download(f"{base}/maxresdefault.jpg", out_path, log):
        log('ok', f'Thumbnail source: got maxresdefault for {vid} (proper)')
        return {"path": str(out_path), "is_proper": True,
                "platform": "youtube", "error": ""}
    # Fall back to a lower-res auto grab so the caller at least has *an* image,
    # but flag it as not-proper so it uses the current frame+text settings.
    for q in ("sddefault.jpg", "hqdefault.jpg"):
        if _download(f"{base}/{q}", out_path, log):
            log('info', f'Thumbnail source: only {q} for {vid} (auto grab)')
            return {"path": str(out_path), "is_proper": False,
                    "platform": "youtube", "error": ""}
    return {"path": None, "is_proper": False, "platform": "youtube",
            "error": "no thumbnail available"}


def _fetch_stub(platform: str, url: str, out_path: Path, log) -> dict:
    """Placeholder for TikTok / Instagram — to be implemented later.

    yt-dlp already exposes ``info['thumbnail']`` for both platforms, so the
    future implementation is: extract_info(download=False) → download that
    URL → decide is_proper.  Left unimplemented on purpose for now.
    """
    log('info', f'Thumbnail source: {platform} not implemented yet — '
                f'falling back to frame grab')
    return {"path": None, "is_proper": False, "platform": platform,
            "error": f"{platform} thumbnail download not implemented yet"}


# ── Public entry point ───────────────────────────────────────────────────

def fetch_original_thumbnail(url: str, out_path, log=None) -> dict:
    """Download the original published thumbnail for *url*.

    Returns a dict: ``{"path", "is_proper", "platform", "error"}``.
      - ``path``      local file path (str) or None
      - ``is_proper`` True when it's a real designed cover worth recreating
      - ``platform``  detected platform
      - ``error``     empty on success
    """
    log = log or _noop_log
    out_path = Path(out_path)
    platform = detect_platform(url)

    if platform == "youtube":
        return _fetch_youtube(url, out_path, log)
    if platform in ("tiktok", "instagram"):
        return _fetch_stub(platform, url, out_path, log)
    return {"path": None, "is_proper": False, "platform": platform,
            "error": "unsupported or missing URL"}
