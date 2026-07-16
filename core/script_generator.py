"""
Script Generator — uses Google Gemini API to convert raw transcripts
into cinematic third-person narration scripts, plus generate
suggested titles and hashtags.

Supports multiple API keys (auto-fallback on quota exhaustion),
multiple API calling methods, and service account auth.
"""

import json
import re
import time
import sys
import base64
import io
import requests
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# TTS Calibration — voice model WPM + tone pacing factors
# Used by Script Studio & Case Commentary to constrain Gemini's
# script length so the narration fits the video at 1.2x speed.
# ═══════════════════════════════════════════════════════════════

# Natural speaking rate (WPM) of each voice at 1.0x speed.
_VOICE_WPM = {
    'Zephyr': 105,
    'Achernar': 112,
    'Gemma': 108,
    'en-US-Studio-Q': 150,
    'en-US-Studio-O': 145,
    'en-US-Studio-D': 140,
}

# Tone/Style pacing factor — how each tone changes speaking pace.
_TONE_PACING = {
    'Storytelling': 0.85,
    'Deep Storytelling': 0.80,
    'Dramatic Storytelling': 0.78,
    'Warm': 0.95,
    'Sad': 0.75,
    'Suspense': 0.85,
    'Motivational': 1.15,
    'Dramatic': 0.80,
    'Happy': 1.15,
    'Authoritative': 1.05,
    'Romantic': 0.80,
    'Mysterious': 0.80,
    'Excited': 1.20,
    'Humorous': 1.10,
}

# User's preferred TTS base speed (1.2x sounds natural for Gemini TTS)
_BASE_TTS_SPEED = 1.2


def calc_target_word_count(video_duration_sec: float,
                           voice_model: str = 'Zephyr',
                           tone_style: str = 'Storytelling') -> int:
    """Calculate how many words fit in the video at 1.2x base speed
    with the given voice model (natural WPM) and tone (pacing factor)."""
    wpm_at_1x = _VOICE_WPM.get(voice_model, 105)
    tone_factor = _TONE_PACING.get(tone_style, 0.85)
    effective_wpm = wpm_at_1x * _BASE_TTS_SPEED * tone_factor
    return max(10, int((video_duration_sec / 60.0) * effective_wpm))

class ScriptGenerator:
    """Generate cinematic narration scripts from transcripts via Gemini API"""

    MODEL_NAME = "gemini-3.5-flash"
    FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-2.0-flash-lite"]
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    BASE_URL_V1 = "https://generativelanguage.googleapis.com/v1"
    OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

    # ── Prompt template config path ─────────────────────────
    DEFAULT_PROMPTS_CONFIG_PATH = None  # auto-detected: data/script_prompts.json

    # ── Master prompt files (Write Story from Video mode) ────
    # These slugs' REAL prompt lives in data/master_prompts/<file>, NOT in
    # script_prompts.json. _build_video_prompt() reads the .txt; the prompt
    # manager edits the .txt directly so edits actually reach Gemini.
    MASTER_PROMPT_SOURCES = {
        "movies_with_dialogue": {
            "file": "Master Prompt For Movies clips With Dialougs.txt",
            "name": "Movies with Dialogue (No Narration)",
            "description":
                "Watch clips that have only original dialogue "
                "— write a complete replacement narration script",
        },
        "movies_with_voiceover": {
            "file": "ALREADY HAVE a voiceover On Movies Clips.txt",
            "name": "Movies Already Has Voiceover",
            "description":
                "Watch clips that already have a voiceover "
                "— replace it with a new script matching exact word count",
        },
        "heartwarming": {
            "file": "Heartwarming Stories Master Prompt.txt",
            "name": "Heartwarming Stories",
            "description":
                "Heartwarming human/animal interest — rescue stories, "
                "wholesome moments, faith in humanity",
        },
        "courtroom_legal": {
            "file": "Courtroom Legal Cases Master Prompt.txt",
            "name": "Courtroom / Legal Cases",
            "description":
                "Courtroom legal case narration — family disputes, "
                "criminal trials, shocking courtroom battles",
        },
        "cctv_surveillance": {
            "file": "CCTV Surveillance Footage Master Prompt.txt",
            "name": "CCTV / Surveillance Footage",
            "description":
                "Surveillance/CCTV footage narration — Gemini picks the most "
                "shocking moment for a hook-sized intro clip, then narrates "
                "the full video in grounded third-person, ending on a "
                "freeze-frame CTA",
        },
        "ocean_mysteries": {
            "file": "Ocean Mysteries Master Prompt.txt",
            "name": "Ocean Mysteries",
            "description":
                "Ocean and maritime footage — storms, ships, dark seas, "
                "haunted vessels — narrated with deep-sea philosophical "
                "tone, scene-by-scene action + moral insight",
        },
    }


    BUILTIN_NARRATION_PROMPT = """You are a professional script writer for the YouTube channel 'Continue'.

Your task is to convert the following raw transcript into a CINEMATIC THIRD-PERSON NARRATION.

STRICT RULES — FOLLOW EVERY ONE:

1. STYLE: Write in the style of the YouTube channel 'Continue' — dramatic, immersive, third-person cinematic narration. Use vivid but concise language.

2. CHARACTER NAMES: Replace ALL character names with neutral descriptions:
   - "John" → "the man" / "the husband" / "the father" (based on context)
   - "Sarah" → "the woman" / "the wife" / "the mother"
   - "Officer Martinez" → "the officer"
   - "Dr. Chen" → "the doctor"
   - Use contextually appropriate neutral labels throughout.

3. NO MEDIA REFERENCES: NEVER mention the movie name, show name, actor names, director names, or any production details.

4. WORD COUNT: Match the EXACT word count of {target_word_count} words. You may vary by up to 10% (±{word_count_tolerance} words) if needed for readability. Count carefully.

5. HOOK: Start with an engaging hook in the style of:
   - "This is the story of..."
   - "Imagine..."
   - "What would you do if..."
   - "In a world where..."

6. ENDING: End with a call-to-action encouraging comments, such as:
   - "What would YOU have done? Let us know in the comments."
   - "Would you have made the same choice? Comment below."
   - "Could you survive something like this? Tell us your thoughts."

7. NICHE ANGLE: Infuse the narration with the perspective of: {niche_angle}

8. NARRATIVE FLOW: Maintain suspense, pacing, and emotional engagement throughout. Use short punchy sentences for tension, longer flowing ones for reflection.

Original Video Title: {title}

RAW TRANSCRIPT:
{transcript}

Write the cinematic narration script now (no preamble, no explanations — just the script):"""

    BUILTIN_METADATA_PROMPT = """Based on the following transcript and its cinematic narration script, generate:

RULES FOR TITLE — FOLLOW ALL:
- Maximum 12 words, simple and natural
- Use ONLY standard punctuation (period, comma, question mark)
- NO em dashes (—), long dashes, or special characters
- NO colons or semicolons in the middle of the title
- Must read like a real human wrote it — NOT like AI
- Plain language, no clickbait formulas or overhyped structure
- Example of good title: "A 14 year old girl sues her mother for surgery"
- Example of bad title: "Teen Demands Surgery To Look Like Her Mom—Judge Makes A Decision"

2. Exactly 2 relevant hashtags (WITHOUT the # symbol, in PascalCase or TitleCase)

Niche angle: {niche_angle}

Transcript:
{transcript}

Cinematic Script:
{script}

Return ONLY valid JSON in this exact format (no markdown, no code fences, no explanation):
{{"suggested_title": "your title here (max 12 words, natural, no em dashes or special chars)", "hashtag_1": "FirstHashtag", "hashtag_2": "SecondHashtag"}}"""

    NICHE_OPTIONS = [
        "Thriller/Action",
        "Crime/Revenge",
        "Underdog/Motivation",
        "Relationship/Drama",
        "Survival/Adventure",
        "Mystery/Twist",
        "Horror/Supernatural",
    ]

    def __init__(self, api_key=None, api_keys=None, service_account_path=None,
                 prompts_config_path=None):
        self._api_keys = []
        self._current_key_index = 0
        self._exhausted_keys = set()
        self._service_account_configured = False

        if api_keys:
            self.configure_multiple(api_keys)
        elif api_key:
            self.configure(api_key)

        if service_account_path:
            self.configure_service_account(service_account_path)

        # ── Prompt template system ──────────────────────────
        self._prompts = {}        # slug -> {name, description, narration_prompt, metadata_prompt}
        self._master_prompts = {}  # slug -> same structure (Pormpts master prompts with "YOUR INPUT:")
        self._active_prompt_key = None
        self._prompts_config_path = None
        self._init_prompts(prompts_config_path)

        # ── Load user's master prompts from Pormpts/ folder ──
        self._load_master_prompts_from_pormpts()

    # ── Key management ──────────────────────────────────────

    def configure(self, api_key):
        """Configure with a single Gemini API key (AIza. or AQ. format)"""
        k = api_key.strip() if api_key else ""
        if k:
            self._api_keys = [k]
            self._current_key_index = 0
            self._exhausted_keys.clear()
            self._auth_method = "api_key"

    def configure_multiple(self, api_keys):
        """Configure with multiple API keys (list of strings).

        Keys are tried in order. When one hits quota exhaustion,
        the next key is used automatically.
        """
        clean = [k.strip() for k in api_keys if k and k.strip()]
        if clean:
            self._api_keys = clean
            self._current_key_index = 0
            self._exhausted_keys.clear()
            self._auth_method = "api_key"

    def add_key(self, api_key):
        """Add another API key to the pool"""
        k = api_key.strip()
        if k and k not in self._api_keys:
            self._api_keys.append(k)
            return True
        return False

    def remove_key(self, index):
        """Remove an API key by index"""
        if 0 <= index < len(self._api_keys):
            removed = self._api_keys.pop(index)
            if index < self._current_key_index:
                self._current_key_index -= 1
            # Clean up exhausted set
            self._exhausted_keys = {i if i < index else i - 1
                                    for i in self._exhausted_keys if i != index}
            return removed
        return None

    def get_keys(self):
        """Return list of all API keys (masked for display)"""
        return [self._mask_key(k) for k in self._api_keys]

    def get_key_count(self):
        """Number of configured API keys"""
        return len(self._api_keys)

    def reorder_key(self, old_index, new_index):
        """Move a key from old_index to new_index (drag-to-reorder)"""
        if 0 <= old_index < len(self._api_keys) and 0 <= new_index < len(self._api_keys):
            key = self._api_keys.pop(old_index)
            self._api_keys.insert(new_index, key)
            # Adjust current index tracking
            if self._current_key_index == old_index:
                self._current_key_index = new_index
            return True
        return False

    def reset_exhausted_keys(self):
        """Clear the exhausted keys list — retry all keys again"""
        self._exhausted_keys.clear()

    # ── Prompt template management ──────────────────────────

    def _resolve_prompts_config_path(self, path):
        """Resolve prompts config path — auto-detect if None"""
        if path:
            return path
        # Auto-detect: look for data/script_prompts.json next to this file
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(base, "data", "script_prompts.json")
        if os.path.isfile(candidate):
            return candidate
        return None

    def _init_prompts(self, prompts_config_path=None):
        """Load prompts from config file, or fall back to built-in defaults"""
        path = self._resolve_prompts_config_path(prompts_config_path)
        if path:
            self._prompts_config_path = path
            loaded = self._load_prompts_from_file()
            if loaded:
                self._prompts = loaded.get("prompts", {})
                active = loaded.get("active_prompt", "")
                if active in self._prompts:
                    self._active_prompt_key = active
                return

        # Fallback: use built-in defaults
        self._prompts = {
            "movies_commentary": {
                "name": "Movies Commentary",
                "description": "Dramatic third-person narration for movie/story recaps",
                "narration_prompt": self.BUILTIN_NARRATION_PROMPT,
                "metadata_prompt": self.BUILTIN_METADATA_PROMPT,
            }
        }
        self._active_prompt_key = "movies_commentary"

    def _load_prompts_from_file(self):
        """Load prompt templates from JSON config file"""
        if not self._prompts_config_path:
            return None
        try:
            with open(self._prompts_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"   ⚠️  Could not load script prompts: {e}")
            return None

    def _save_prompts_to_file(self):
        """Save current prompts back to JSON config file"""
        if not self._prompts_config_path:
            return False
        try:
            data = {
                "active_prompt": self._active_prompt_key or "",
                "prompts": self._prompts,
            }
            with open(self._prompts_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"   ⚠️  Could not save script prompts: {e}")
            return False

    def get_prompt_list(self):
        """Return list of (slug, name, description) for all prompt templates"""
        result = []
        for slug, data in self._prompts.items():
            result.append((slug, data.get("name", slug), data.get("description", "")))
        return result

    def get_prompt_names(self):
        """Return list of display names for all prompt templates"""
        return [data.get("name", slug) for slug, data in self._prompts.items()]

    def get_active_prompt_key(self):
        """Return the slug of the currently active prompt template"""
        return self._active_prompt_key

    def get_active_prompt_name(self):
        """Return the display name of the currently active prompt template"""
        if self._active_prompt_key and self._active_prompt_key in self._prompts:
            return self._prompts[self._active_prompt_key].get("name", self._active_prompt_key)
        return "Movies Commentary"

    def set_active_prompt(self, slug):
        """Switch to a different prompt template by slug"""
        if slug in self._prompts:
            self._active_prompt_key = slug
            self._save_prompts_to_file()
            return True
        return False

    def add_prompt(self, slug, name, description, narration_prompt, metadata_prompt):
        """Add a new prompt template. Returns True on success, False if slug exists."""
        if not slug or slug in self._prompts:
            return False
        self._prompts[slug] = {
            "name": name or slug,
            "description": description or "",
            "narration_prompt": narration_prompt,
            "metadata_prompt": metadata_prompt,
        }
        self._save_prompts_to_file()
        return True

    def update_prompt(self, slug, name=None, description=None,
                      narration_prompt=None, metadata_prompt=None):
        """Update an existing prompt template. Fields set to None are left unchanged."""
        if slug not in self._prompts:
            return False
        if name is not None:
            self._prompts[slug]["name"] = name
        if description is not None:
            self._prompts[slug]["description"] = description
        if narration_prompt is not None:
            self._prompts[slug]["narration_prompt"] = narration_prompt
        if metadata_prompt is not None:
            self._prompts[slug]["metadata_prompt"] = metadata_prompt
        self._save_prompts_to_file()
        return True

    def remove_prompt(self, slug):
        """Remove a prompt template by slug. Cannot remove the last one."""
        if slug not in self._prompts or len(self._prompts) <= 1:
            return False
        was_active = (self._active_prompt_key == slug)
        del self._prompts[slug]
        if was_active:
            # Switch to first available
            self._active_prompt_key = next(iter(self._prompts.keys()))
        self._save_prompts_to_file()
        return True

    def get_prompt_data(self, slug):
        """Return the full prompt template dict for a slug (or None)"""
        return self._prompts.get(slug)

    # ── User's master prompts from Pormpts/ ─────────────────

    def _load_master_prompts_from_pormpts(self):
        """Load the user's master prompt files from ChangeGUI/Pormpts/

        Master prompts (with "YOUR INPUT:" section) are stored in
        self._master_prompts.  Transcript-compatible versions (with
        {placeholder} format) live in self._prompts (loaded from JSON).

        For slugs that exist in BOTH places (heartwarming, courtroom_legal),
        the Video-to-Script tab uses the master prompt; the Script
        Generator tab uses the JSON version.

        Movies-only slugs (movies_with_*) are ONLY in Pormpts and get
        stored in BOTH dicts so the Video-to-Script tab can find them.
        """
        pormpts_dir = self.get_master_prompts_dir()
        if not pormpts_dir or not pormpts_dir.is_dir():
            return

        sources = self.MASTER_PROMPT_SOURCES

        for slug, cfg in sources.items():
            path = pormpts_dir / cfg["file"]
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            entry = {
                "name": cfg["name"],
                "description": cfg["description"],
                "narration_prompt": content,
                "metadata_prompt": self.BUILTIN_METADATA_PROMPT,
            }
            # Always store in master_prompts (for Video-to-Script tab)
            self._master_prompts[slug] = entry
            # Movies-only slugs that aren't in JSON also go in _prompts
            if slug not in self._prompts:
                self._prompts[slug] = entry

        # Default active prompt if none set
        if not self._active_prompt_key:
            if "movies_with_dialogue" in self._prompts:
                self._active_prompt_key = "movies_with_dialogue"
            elif self._prompts:
                self._active_prompt_key = next(iter(self._prompts))

    @staticmethod
    def get_master_prompts_dir():
        """Return the directory holding the master-prompt .txt files, or None.

        Prefers the in-project copy (data/master_prompts/); falls back to the
        legacy ChangeGUI/Pormpts folder so older machines keep working.
        """
        in_project = Path(__file__).resolve().parent.parent / "data" / "master_prompts"
        if in_project.is_dir():
            return in_project
        legacy_dir = Path(r"D:\GitHub\ChangeGUI\Pormpts")
        if legacy_dir.is_dir():
            return legacy_dir
        return None

    @classmethod
    def get_master_prompt_path(cls, slug):
        """Return the Path to a slug's master .txt file, or None if not file-backed."""
        cfg = cls.MASTER_PROMPT_SOURCES.get(slug)
        if not cfg:
            return None
        d = cls.get_master_prompts_dir()
        if not d:
            return None
        return d / cfg["file"]

    @classmethod
    def is_master_backed(cls, slug):
        """True if this slug's real prompt lives in a master .txt file."""
        p = cls.get_master_prompt_path(slug)
        return bool(p and p.exists())

    def _format_narration_prompt(self, transcript, title, target_word_count, niche_angle, language="english"):
        """Fill the active narration prompt template with actual values + language instruction"""
        if not self._active_prompt_key or self._active_prompt_key not in self._prompts:
            template = self.BUILTIN_NARRATION_PROMPT
        else:
            template = self._prompts[self._active_prompt_key]["narration_prompt"]

        word_count_tolerance = int(target_word_count * 0.1)

        # Niche angle dropdowns were removed — each preset is already niche-specific.
        # Fall back to a neutral phrase so the {niche_angle} slot never reads blank.
        if not niche_angle or not str(niche_angle).strip():
            niche_angle = "the natural tone of this story"

        # If template has {language} placeholder, fill it; otherwise inject instruction
        if "{language}" in template:
            return template.format(
                title=title,
                target_word_count=target_word_count,
                word_count_tolerance=word_count_tolerance,
                niche_angle=niche_angle,
                transcript=transcript,
                language=language,
            )
        else:
            base = template.format(
                title=title,
                target_word_count=target_word_count,
                word_count_tolerance=word_count_tolerance,
                niche_angle=niche_angle,
                transcript=transcript,
            )
            # Prepend language instruction if not English (default)
            lang_name = language.capitalize()
            if lang_name.lower() != "english":
                base = (f"IMPORTANT: Write the ENTIRE narration script in {lang_name}. "
                        f"Every sentence, every word must be in {lang_name} — do NOT use English.\n\n"
                        f"{base}")
            # Append overall voiceover style instruction (replaces old per-line emotion tags)
            base += (
                "\n\nVOICEOVER STYLE (overall tone — NOT per-line emotions):\n"
                "Do NOT assign different emotions to each line. Instead, decide ONE overall\n"
                "emotional tone that fits the ENTIRE narrative based on the video's context.\n"
                "\n"
                "Then, at the END of your script, add these two lines on their own:\n"
                "---\n"
                "VOICEOVER STYLE: <one sentence describing the overall narrator tone, e.g. 'Read aloud in a warm, welcoming tone.' or 'Dark suspense with storytelling flow.'>\n"
                "VOICEOVER SPEED: <recommended speaking speed in WPM for this content, 140-220 range>\n"
                "---\n"
                "ONLY if a specific line genuinely requires a different emotion may you add\n"
                "a per-line [emotion] tag (e.g. [whisper], [dramatic], [urgent]), but this\n"
                "should be RARE — not your default. The default is the overall style above.\n"
            )
            return base

    def _format_metadata_prompt(self, transcript, script, niche_angle, language="english"):
        """Fill the active metadata prompt template with actual values + language instruction"""
        if not self._active_prompt_key or self._active_prompt_key not in self._prompts:
            template = self.BUILTIN_METADATA_PROMPT
        else:
            template = self._prompts[self._active_prompt_key]["metadata_prompt"]

        lang_name = language.capitalize()

        # Niche dropdowns removed — keep the slot non-blank for prompt quality.
        if not niche_angle or not str(niche_angle).strip():
            niche_angle = "the natural tone of this story"

        # If template has {language} placeholder, fill it
        if "{language}" in template:
            return template.format(
                transcript=transcript,
                script=script,
                niche_angle=niche_angle,
                language=language,
            )
        else:
            base = template.format(
                transcript=transcript,
                script=script,
                niche_angle=niche_angle,
            )
            if lang_name.lower() != "english":
                prefix = f"IMPORTANT: Generate ALL output in {lang_name}. " \
                         f"Title, hashtags, and descriptions must be in {lang_name}.\n\n"
                base = prefix + base
            return base

    def _mask_key(self, key):
        """Return masked version for display: AQ.Ab8R...6I6w"""
        if len(key) > 10:
            return key[:7] + "..." + key[-4:]
        return key[:4] + "..."

    @property
    def active_key_label(self):
        """Masked label of the currently active key (for UI display)"""
        if not self._api_keys:
            return "None"
        return self._mask_key(self._api_keys[self._current_key_index])

    @property
    def active_key_count(self):
        return len(self._api_keys)

    @property
    def exhausted_count(self):
        return len(self._exhausted_keys)

    @property
    def all_keys_exhausted(self):
        return len(self._exhausted_keys) >= len(self._api_keys) > 0

    # ── Internal: active key selection ──────────────────────

    def _get_current_api_key(self):
        """Return the current API key, or None if all exhausted"""
        if self._exhausted_keys:
            # Find first non-exhausted key after current index
            for _ in range(len(self._api_keys)):
                self._current_key_index = (self._current_key_index + 1) % len(self._api_keys)
                if self._current_key_index not in self._exhausted_keys:
                    return self._api_keys[self._current_key_index]
            return None  # all exhausted
        return self._api_keys[self._current_key_index] if self._api_keys else None

    def _mark_current_key_exhausted(self):
        """Mark the current key as exhausted (quota used up)"""
        self._exhausted_keys.add(self._current_key_index)
        # Auto-rotate to next available key
        for _ in range(len(self._api_keys)):
            self._current_key_index = (self._current_key_index + 1) % len(self._api_keys)
            if self._current_key_index not in self._exhausted_keys:
                break

    # ── Service account config ──────────────────────────────

    def configure_service_account(self, json_path):
        """Configure using a service account JSON key file"""
        import os
        json_path = str(json_path)
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Service account file not found: {json_path}")

        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            self._sa_credentials = service_account.Credentials.from_service_account_file(
                json_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._sa_credentials.refresh(Request())
            self._auth_method = "service_account"
            self._service_account_configured = True
        except ImportError:
            raise ImportError(
                "google-auth library required for service accounts. "
                "Run: pip install google-auth"
            )
        except Exception as e:
            raise ValueError(f"Failed to load service account: {e}")

    def clear_auth(self):
        """Clear stored authentication"""
        self._api_keys = []
        self._current_key_index = 0
        self._exhausted_keys.clear()
        self._service_account_configured = False
        if hasattr(self, '_sa_credentials'):
            del self._sa_credentials

    def is_configured(self):
        """Check if authentication has been configured"""
        return bool(self._api_keys) or self._service_account_configured

    # ── Core API call with model + key fallback ─────────────

    def _call_gemini(self, prompt, timeout=60):
        """Make a request to the Gemini API with automatic key rotation.

        Strategy:
          1. Try current API key with primary MODEL_NAME
          2. If quota error → mark key exhausted → try next key
          3. If all keys exhausted → reset and return error
          4. Within each key, try FALLBACK_MODELS and different auth methods
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured."}

        # If all keys are exhausted, reset once so the user gets a second chance
        if self.all_keys_exhausted:
            self._exhausted_keys.clear()

        # Try each non-exhausted key
        tried_keys = set()
        while len(tried_keys) < self.get_key_count():
            key = self._get_current_api_key()
            if key is None or self._current_key_index in tried_keys:
                break
            tried_keys.add(self._current_key_index)

            # Try this key with model fallback
            result = self._try_key_with_models(prompt, timeout, key)
            if "error" not in result:
                return result

            error_msg = result["error"]
            status_code = result.get("_status", "")
            # Quota error → mark key exhausted, continue to next
            is_quota = (
                status_code == 429
                and ("quota" in error_msg.lower()
                     or "RESOURCE_EXHAUSTED" in error_msg)
            )
            if is_quota:
                print(f"   ⚠️  Key {self._mask_key(key)} quota exhausted (HTTP {status_code}), switching keys...")
                self._mark_current_key_exhausted()
                continue

            # Non-quota error (auth, model, etc.) — return it, no point trying other keys
            return result

        # All keys exhausted — include the last error details so the user
        # knows what really happened (may not be a quota issue at all).
        last_status = result.get("_status", "?") if result else "?"
        last_error = result.get("error", "?")[:200] if result else "?"
        return {
            "error": (
                f"All {self.get_key_count()} API key(s) failed. "
                f"Last error (HTTP {last_status}): {last_error}"
            )
        }

    def _try_key_with_models(self, prompt, timeout, api_key):
        """Try a single API key across multiple models and auth methods."""
        all_errors = []
        models_to_try = [self.MODEL_NAME] + self.FALLBACK_MODELS

        for model in models_to_try:
            original_model = self.MODEL_NAME
            self.MODEL_NAME = model

            # Method 1: Standard query param auth
            result = self._call_gemini_standard(prompt, timeout, self.BASE_URL, api_key)
            self.MODEL_NAME = original_model

            if "error" not in result:
                self.MODEL_NAME = model
                return result

            error_msg = result["error"]
            all_errors.append((f"{model} query-param", error_msg[:100]))
            error_msg_lower = error_msg.lower()

            # Quota → stop trying models on this key, move to next key
            status_code = result.get("_status", "")
            is_quota = (
                status_code == 429
                and ("quota" in error_msg_lower
                     or "RESOURCE_EXHAUSTED" in error_msg)
            )
            if is_quota:
                return result  # caller will mark key exhausted

            # PREPAY_MODE / billing → try different auth methods on same model
            if "PREPAY_MODE" in error_msg or "billing" in error_msg_lower or "403" in error_msg:
                self.MODEL_NAME = model

                # Method 2: x-goog-api-key header
                result2 = self._call_gemini_header(prompt, timeout, self.BASE_URL, api_key)
                self.MODEL_NAME = original_model
                if "error" not in result2:
                    self.MODEL_NAME = model
                    return result2
                all_errors.append((f"{model} header", result2["error"][:100]))

                # Method 3: v1 (stable) API
                self.MODEL_NAME = model
                result3 = self._call_gemini_standard(prompt, timeout, self.BASE_URL_V1, api_key)
                self.MODEL_NAME = original_model
                if "error" not in result3:
                    self.MODEL_NAME = model
                    return result3
                all_errors.append((f"{model} v1", result3["error"][:100]))

                # Method 4: OpenAI-compatible endpoint
                self.MODEL_NAME = model
                result4 = self._call_gemini_openai(prompt, timeout, api_key)
                self.MODEL_NAME = original_model
                if "error" not in result4:
                    self.MODEL_NAME = model
                    return result4
                all_errors.append((f"{model} OpenAI", result4["error"][:100]))

                return result  # still failing with this key

            # Model not found → try next model
            if "404" in str(result.get("_status", "")) or "not found" in error_msg_lower:
                continue

        # All models failed for this key — return combined error
        error_summary = "\n".join([f"   [{m}] {e}" for m, e in all_errors])
        return {
            "error": (
                f"Key {self._mask_key(api_key)} failed across all models:\n{error_summary}"
            )
        }

    # ── Video upload to Gemini File API ─────────────────────

    def _upload_video(self, video_path, api_key=None, progress_callback=None):
        """Upload a video to Gemini File API and return file_uri + mime_type.

        Uses the google.genai SDK which handles resumable uploads,
        chunking, and processing-poll internally — much more reliable
        than raw HTTP for large files.

        Args:
            video_path: Path to video file
            api_key: Optional API key override
            progress_callback: Optional callable(msg) for status updates

        Returns dict with keys: file_uri, mime_type
        Or dict with key: error on failure.
        """
        import google.genai as genai

        # ── Gather usable keys ──────────────────────────────
        keys_to_try = []
        if api_key:
            keys_to_try.append(api_key)
        elif self._api_keys:
            keys_to_try = list(self._api_keys)

        if not keys_to_try:
            return {"error": "No API key available for video upload."}

        video_path = Path(video_path)
        if not video_path.exists():
            return {"error": f"Video file not found: {video_path}"}

        file_size = video_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        if progress_callback:
            progress_callback(f"📤 Video file: {file_size_mb:.0f} MB")

        import tempfile
        import shutil

        last_error = ""
        # ── ASCII-safe temp path (Windows encoding workaround) ──
        ext = video_path.suffix.lower()
        if ext not in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".flv", ".wmv"):
            ext = ".mp4"
        safe_path = Path(tempfile.mktemp(suffix=ext))
        try:
            if progress_callback:
                progress_callback("📋 Copying video to temp location...")
            shutil.copy2(video_path, safe_path)
        except Exception as e:
            safe_path.unlink(missing_ok=True)
            return {"error": f"Failed to copy video for upload: {e}"}

        try:
            for key in keys_to_try:
                try:
                    if progress_callback:
                        progress_callback("☁️ Uploading video to Gemini... (this may take a while for large files)")
                    client = genai.Client(api_key=key)

                    # Upload from the safe temp path (ASCII-only, no encoding issues)
                    gemini_file = client.files.upload(file=str(safe_path))

                    # Poll until ACTIVE (or FAILED)
                    if progress_callback:
                        progress_callback("⏳ Waiting for Gemini to process video...")
                    max_wait = 180 if file_size_mb < 100 else 300
                    waited = 0
                    while True:
                        state = gemini_file.state
                        state_name = state.name if state else "PROCESSING"
                        if state_name == "ACTIVE":
                            if progress_callback:
                                progress_callback("✅ Video uploaded and processed!")
                            return {
                                "file_uri": gemini_file.uri,
                                "mime_type": gemini_file.mime_type or "video/mp4",
                            }
                        if state_name == "FAILED":
                            last_error = "Gemini server failed to process the video"
                            break  # try next key

                        time.sleep(3)
                        waited += 3
                        if waited >= max_wait:
                            return {
                                "error":
                                    f"Video processing timed out after {max_wait}s "
                                    f"(file: {file_size_mb:.0f} MB)"
                            }
                        if progress_callback and waited % 30 == 0:
                            progress_callback(f"⏳ Still processing... ({waited}s)")
                        gemini_file = client.files.get(name=gemini_file.name)

                except Exception as e:
                    last_error = str(e)
                    err_lower = last_error.lower()
                    # Retry on quota, connection, or timeout errors
                    if any(x in last_error or x in err_lower
                           for x in ["429", "quota", "resource_exhausted",
                                     "timeout", "connection", "abort"]):
                        if progress_callback:
                            progress_callback(f"🔄 Key failed ({last_error[:60]}), trying next...")
                        continue
                    # Other errors — stop and report immediately
                    break
        finally:
            safe_path.unlink(missing_ok=True)

        return {"error": f"Video upload failed: {last_error}"}

    # ── HTTP methods ────────────────────────────────────────

    def _call_gemini_standard(self, prompt, timeout=60, base_url=None, api_key=None):
        """Method 1: Standard Gemini REST API — key as URL query param"""
        if base_url is None:
            base_url = self.BASE_URL
        key = api_key or (self._api_keys[self._current_key_index] if self._api_keys else None)
        url = f"{base_url}/models/{self.MODEL_NAME}:generateContent"

        headers = {"Content-Type": "application/json"}
        params = {}

        if key:
            params["key"] = key
        elif self._service_account_configured:
            from google.auth.transport.requests import Request
            self._sa_credentials.refresh(Request())
            headers["Authorization"] = f"Bearer {self._sa_credentials.token}"
        else:
            return {"error": "No API key or service account configured."}

        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(url, params=params, headers=headers,
                                     json=payload, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        return {"text": text}
                return {"error": "Empty response from Gemini API — no content returned"}
            else:
                error_body = response.text[:500]
                error_detail = ""
                try:
                    err_data = response.json()
                    err_info = err_data.get("error", {})
                    error_detail = err_info.get("message", "") or err_info.get("status", "")
                except Exception:
                    error_detail = error_body
                return {
                    "error": f"Gemini API error (HTTP {response.status_code}): {error_detail}",
                    "_raw_error": error_detail,
                    "_status": response.status_code,
                }

        except requests.exceptions.Timeout:
            return {"error": "Gemini API request timed out. Check your internet connection."}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Gemini API. Check your internet connection."}
        except Exception as e:
            return {"error": f"Gemini API request failed: {str(e)}"}

    def _call_gemini_header(self, prompt, timeout=60, base_url=None, api_key=None):
        """Method 2: Standard Gemini REST API — key as x-goog-api-key header."""
        if base_url is None:
            base_url = self.BASE_URL
        key = api_key or (self._api_keys[self._current_key_index] if self._api_keys else None)
        if not key:
            return {"error": "API key required."}

        url = f"{base_url}/models/{self.MODEL_NAME}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        return {"text": text}
                return {"error": "Empty response — no content returned"}
            else:
                error_body = response.text[:500]
                error_detail = ""
                try:
                    err_data = response.json()
                    err_info = err_data.get("error", {})
                    error_detail = err_info.get("message", "") or err_info.get("status", "")
                except Exception:
                    error_detail = error_body
                return {"error": f"Header auth error (HTTP {response.status_code}): {error_detail}"}

        except requests.exceptions.Timeout:
            return {"error": "Header auth request timed out."}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect for header auth."}
        except Exception as e:
            return {"error": f"Header auth request failed: {str(e)}"}

    def _call_gemini_openai(self, prompt, timeout=60, api_key=None):
        """Method 3: OpenAI-compatible Gemini endpoint — key as Bearer token."""
        key = api_key or (self._api_keys[self._current_key_index] if self._api_keys else None)
        if not key:
            return {"error": "API key required for OpenAI-compatible method."}

        url = f"{self.OPENAI_BASE_URL}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        payload = {"model": self.MODEL_NAME, "messages": [{"role": "user", "content": prompt}]}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        return {"text": content}
                return {"error": "Empty response from OpenAI-compatible endpoint — no content returned"}
            else:
                error_body = response.text[:500]
                error_detail = ""
                try:
                    err_data = response.json()
                    err_info = err_data.get("error", {})
                    error_detail = err_info.get("message", "") or str(err_info)
                except Exception:
                    error_detail = error_body
                return {"error": f"OpenAI endpoint error (HTTP {response.status_code}): {error_detail}"}

        except Exception as e:
            return {"error": f"OpenAI-compatible endpoint request failed: {str(e)}"}

    # ── Public API ──────────────────────────────────────────

    def test_connection(self):
        """Test the Gemini API connection with a simple prompt"""
        if not self.is_configured():
            return False, "API key not configured. Please enter your Gemini API key first."

        result = self._call_gemini("Say 'OK' and nothing else.")
        if "error" in result:
            return False, f"FAIL: {result['error'][:200]}"
        text = result.get("text", "")
        if text and "OK" in text:
            return True, f"OK (key #{self._current_key_index + 1}: {self.active_key_label})"
        return False, f"Unexpected response: {text[:100]}"

    def generate_script(self, transcript, title, duration, word_count, wpm, niche_angle, language="english"):
        """
        Generate a full script package from a transcript.

        Args:
            transcript: Raw speech transcription text
            title: Original video title
            duration: Video duration in seconds
            word_count: Word count of transcript (for matching)
            wpm: Words per minute of original
            niche_angle: Content niche (e.g. "Thriller/Action")
            language: Target language for script generation (e.g. "english", "russian", "arabic")

        Returns:
            dict with keys:
                script (str): Generated narration script
                suggested_title (str): Suggested video title
                hashtag_1 (str): First suggested hashtag (no #)
                hashtag_2 (str): Second suggested hashtag (no #)
                generated_word_count (int): Word count of generated script
                error (str, optional): Error message if something failed
        """
        if not self.is_configured():
            return {"error": "Gemini API key not configured."}

        try:
            script = self._generate_narration(transcript, title, word_count, niche_angle, language)
            if not script:
                return {"error": "Failed to generate script from Gemini."}

            # Parse voiceover style/speed from Gemini output, then strip formatting
            script, voiceover_style, voiceover_speed = self._parse_voiceover_metadata(script)
            script = self._clean_script(script)
            generated_word_count = len(script.split())

            metadata = self._generate_metadata(transcript, script, niche_angle, language)
            if not metadata:
                metadata = {}

            return {
                "script": script,
                "suggested_title": metadata.get("suggested_title", ""),
                "hashtag_1": metadata.get("hashtag_1", ""),
                "hashtag_2": metadata.get("hashtag_2", ""),
                "generated_word_count": generated_word_count,
                "voiceover_style": voiceover_style,
                "voiceover_speed": voiceover_speed,
            }

        except Exception as e:
            return {"error": f"Script generation failed: {str(e)}"}

    def _generate_narration(self, transcript, title, target_word_count, niche_angle, language="english"):
        """Convert transcript to narration using the active prompt template"""
        prompt = self._format_narration_prompt(
            transcript=transcript,
            title=title,
            target_word_count=target_word_count,
            niche_angle=niche_angle,
            language=language,
        )

        result = self._call_gemini(prompt)
        if "error" in result:
            raise Exception(result["error"])
        text = result.get("text", "")
        return text.strip() if text else ""

    @staticmethod
    def _clean_script(text):
        """Strip timestamp markers, word counts, beat types, and running totals from Gemini output.

        Gemini returns narration lines in this format when using output-format prompts:
            [0:00] | Narration line | (12) | [hook]
            // Running total: X words of Y //

        This strips all that metadata so only the clean narration text remains for TTS.
        """
        # Remove // Running total: X words of Y //
        text = re.sub(r'// Running total:.*?//', '', text)
        # Remove [N:NN] |  prefix on each line
        text = re.sub(r'^\s*\[\d+:\d+\]\s*\|\s*', '', text, flags=re.MULTILINE)
        # Remove | (word count) | [beat] suffix on each line
        text = re.sub(r'\s*\|\s*\(\d+\)\s*\|\s*\[.*?\]\s*$', '', text, flags=re.MULTILINE)
        # Remove bare | CTA-type markers (e.g. | [close] or | [CTA] without word count)
        text = re.sub(r'\s*\|\s*\[.*?\]\s*$', '', text, flags=re.MULTILINE)
        # Collapse multiple blank lines into one
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _parse_voiceover_metadata(text):
        """Extract VOICEOVER STYLE and VOICEOVER SPEED from Gemini output, then strip them.

        The new prompts ask Gemini to append at the end:
            ---
            VOICEOVER STYLE: <description>
            VOICEOVER SPEED: <WPM>
            ---

        Returns:
            tuple: (clean_text, voiceover_style, voiceover_speed_wpm)
        """
        style = ""
        speed = 0

        # Match the VOICEOVER block at the end of the text
        m = re.search(
            r'(?P<before>.*?)'
            r'[-]{3,}\s*\n'
            r'VOICEOVER\s+STYLE:\s*(.+?)\s*\n'
            r'VOICEOVER\s+SPEED:\s*(\d+).*?'
            r'(?:\n[-]{3,})?'
            r'\s*$',
            text, re.DOTALL
        )
        if m:
            style = m.group(2).strip()
            speed = int(m.group(3))
            text = m.group(1).strip()
        else:
            # Fallback: line-by-line extraction (no --- wrapper)
            lines = text.split('\n')
            clean_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.upper().startswith('VOICEOVER STYLE:'):
                    style = stripped.split(':', 1)[1].strip()
                elif stripped.upper().startswith('VOICEOVER SPEED:'):
                    speed_str = stripped.split(':', 1)[1].strip()
                    try:
                        speed = int(''.join(c for c in speed_str if c.isdigit()))
                    except ValueError:
                        speed = 0
                else:
                    clean_lines.append(line)
            text = '\n'.join(clean_lines).strip()

        return text, style, speed

    def _generate_metadata(self, transcript, script, niche_angle, language="english"):
        """Generate a suggested title and two hashtags using the active prompt template"""
        prompt = self._format_metadata_prompt(
            transcript=transcript,
            script=script,
            niche_angle=niche_angle,
            language=language,
        )

        result = self._call_gemini(prompt)
        if "error" in result:
            raise Exception(result["error"])
        text = result.get("text", "")

        if not text:
            return {}

        text = text.strip()
        text = re.sub(r"```(?:json)?\s*", "", text).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            title_match = re.search(r'"suggested_title"\s*:\s*"([^"]+)"', text)
            hash1_match = re.search(r'"hashtag_1"\s*:\s*"([^"]+)"', text)
            hash2_match = re.search(r'"hashtag_2"\s*:\s*"([^"]+)"', text)
            return {
                "suggested_title": title_match.group(1) if title_match else "",
                "hashtag_1": hash1_match.group(1) if hash1_match else "",
                "hashtag_2": hash2_match.group(1) if hash2_match else "",
            }

    def generate_script_with_retry(
        self, transcript, title, duration, word_count, wpm, niche_angle,
        language="english", max_retries=2
    ):
        """Call generate_script with retry logic for transient failures"""
        for attempt in range(max_retries + 1):
            result = self.generate_script(
                transcript, title, duration, word_count, wpm, niche_angle, language
            )
            if "error" not in result:
                return result
            if attempt < max_retries:
                time.sleep(2 ** attempt)
        return result

    # ── Video-based script generation ─────────────────────────

    def generate_script_from_video(self, video_url=None, video_path=None, language="english",
                                   niche_angle="", style_preference="", context="",
                                   transcript=None, wpm=None, progress_callback=None):
        """Generate a narration script by having Gemini watch a video (visuals + audio).

        For YouTube URLs — Gemini watches natively via URL.
        For local files / non-YouTube URLs — uploaded to Gemini File API first.

        Args:
            video_url: YouTube/other URL for Gemini to watch
            video_path: Local video file path (used if no URL, or for non-YouTube upload)
            language: Target language (e.g. "english", "russian")
            niche_angle: Content niche/style
            transcript: Optional transcript text to supplement what Gemini hears
            progress_callback: Optional callable(msg) for real-time status updates

        Returns:
            dict with keys: script, suggested_title, hashtag_1, hashtag_2,
                            generated_word_count, or error on failure
        """
        if not self.is_configured():
            return {"error": "Gemini API key not configured."}

        if progress_callback:
            progress_callback("🚀 Starting video script generation...")


        try:
            # ── Resolve video file (download if YouTube URL) ────
            if progress_callback:
                progress_callback("📥 Resolving video file...")
            local_path = self._resolve_video(video_url, video_path)
            if isinstance(local_path, dict) and "error" in local_path:
                return local_path

            # Upload to Gemini File API
            upload = self._upload_video(local_path, progress_callback=progress_callback)
            if "error" in upload:
                return upload

            # ── Detect video duration & calculate target word count ────
            # Gemini is bad at counting words by ear from a video.
            # We measure the actual file duration and calculate a precise
            # target so the script fits perfectly — no cutoff at the end.
            video_duration = 0.0
            target_word_count = 0
            try:
                import subprocess, json as _json
                res = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "json", local_path],
                    capture_output=True, text=True, timeout=15,
                )
                if res.returncode == 0:
                    info = _json.loads(res.stdout)
                    video_duration = float(info.get("format", {}).get("duration", 0))
                    # WPM: use calibration tables by default (Zephyr/Storytelling ~107 WPM
                    # effective at 1.2x), caller overrides for slower engines (qwen3=110)
                    if wpm:
                        effective_wpm = wpm
                        target_word_count = int((video_duration / 60.0) * effective_wpm)
                    else:
                        target_word_count = calc_target_word_count(video_duration,
                                                                    'Zephyr', 'Storytelling')
                        effective_wpm = (target_word_count / (video_duration / 60.0)
                                         if video_duration > 0 else 107)
            except Exception:
                pass  # non-critical — prompt falls back to "count by ear"

            if progress_callback:
                progress_callback(f"📝 Building narration prompt ({target_word_count} words for {video_duration:.0f}s video)...")
            full_prompt = self._build_video_prompt(
                language, niche_angle, transcript,
                style_preference=style_preference, context=context,
                video_duration=video_duration,
                target_word_count=target_word_count,
                wpm=effective_wpm,
            )

            # Make the API call with the uploaded file
            result = self._call_gemini_with_file(full_prompt, upload, progress_callback=progress_callback)

            if "error" in result:
                return result

            raw_script = result.get("text", "").strip()
            if not raw_script:
                return {"error": "Empty response from Gemini."}

            # Parse voiceover style/speed from Gemini output, then strip formatting
            script, voiceover_style, voiceover_speed = self._parse_voiceover_metadata(raw_script)

            generated_word_count = len(script.split())

            # ── Generate metadata (title + hashtags) ─────
            try:
                meta_prompt = self._format_metadata_prompt(
                    transcript=transcript or script,
                    script=script,
                    niche_angle=niche_angle,
                    language=language,
                )
                meta_result = self._call_gemini(meta_prompt)
                metadata = {}
                if "error" not in meta_result:
                    meta_text = meta_result.get("text", "").strip()
                    if meta_text:
                        meta_text = re.sub(r"```(?:json)?\s*", "", meta_text).strip()
                        try:
                            metadata = json.loads(meta_text)
                        except json.JSONDecodeError:
                            tm = re.search(r'"suggested_title"\s*:\s*"([^"]+)"', meta_text)
                            h1 = re.search(r'"hashtag_1"\s*:\s*"([^"]+)"', meta_text)
                            h2 = re.search(r'"hashtag_2"\s*:\s*"([^"]+)"', meta_text)
                            if tm or h1 or h2:
                                metadata = {
                                    "suggested_title": tm.group(1) if tm else "",
                                    "hashtag_1": h1.group(1) if h1 else "",
                                    "hashtag_2": h2.group(1) if h2 else "",
                                }
            except Exception:
                metadata = {}

            return {
                "script": script,
                "suggested_title": metadata.get("suggested_title", ""),
                "hashtag_1": metadata.get("hashtag_1", ""),
                "hashtag_2": metadata.get("hashtag_2", ""),
                "generated_word_count": generated_word_count,
                "voiceover_style": voiceover_style,
                "voiceover_speed": voiceover_speed,
            }

        except Exception as e:
            return {"error": f"Script generation failed: {str(e)}"}

    def _call_gemini_with_file(self, prompt, file_info, timeout=600, progress_callback=None):
        """Call Gemini with an uploaded file reference (video/image).

        Args:
            prompt: The text prompt to send alongside the file
            file_info: Dict with file_uri and mime_type from _upload_video
            timeout: HTTP request timeout in seconds
            progress_callback: Optional callable(msg) for status updates

        Returns dict with keys: text, or error on failure.
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured."}

        if self.all_keys_exhausted:
            self._exhausted_keys.clear()

        file_data = {"mime_type": file_info["mime_type"], "file_uri": file_info["file_uri"]}

        tried_keys = set()
        while len(tried_keys) < self.get_key_count():
            key = self._get_current_api_key()
            if key is None or self._current_key_index in tried_keys:
                break
            tried_keys.add(self._current_key_index)

            # Try primary model only (file may not work on all fallbacks)
            url = f"{self.BASE_URL}/models/{self.MODEL_NAME}:generateContent"
            params = {"key": key}
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [
                        {"file_data": file_data},
                        {"text": prompt},
                    ]
                }]
            }

            try:
                if progress_callback:
                    progress_callback("🤖 Asking Gemini to analyze the video and write script...")
                response = requests.post(url, params=params, headers=headers,
                                         json=payload, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            if text:
                                return {"text": text}
                    return {"error": "Empty response from Gemini — no content returned"}
                else:
                    error_detail = ""
                    try:
                        err_data = response.json()
                        err_info = err_data.get("error", {})
                        error_detail = err_info.get("message", "") or err_info.get("status", "")
                    except Exception:
                        error_detail = response.text[:500]

                    status = response.status_code
                    is_quota = (status == 429 and ("quota" in error_detail.lower()
                                or "RESOURCE_EXHAUSTED" in error_detail))
                    if is_quota:
                        self._mark_current_key_exhausted()
                        continue

                    return {
                        "error": f"Gemini API error (HTTP {status}): {error_detail}",
                        "_status": status,
                    }

            except requests.exceptions.Timeout:
                return {"error": "Gemini API request timed out."}
            except requests.exceptions.ConnectionError:
                return {"error": "Failed to connect to Gemini API."}
            except Exception as e:
                return {"error": f"Gemini API request failed: {str(e)}"}

        return {"error": f"All {self.get_key_count()} API key(s) failed on video request."}

    # ── Helpers for video script generation ─────────────────

    def _resolve_video(self, video_url=None, video_path=None):
        """Get a local video file path — download from YouTube if needed.

        Returns:
            str: Path to local video file, or dict with "error" on failure.
        """
        # Direct file path
        if video_path and Path(video_path).exists():
            return str(Path(video_path).resolve())

        # YouTube URL — download to temp
        if video_url and ('youtube.com' in video_url.lower() or 'youtu.be' in video_url.lower()):
            import yt_dlp
            import tempfile
            import shutil

            tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_video_"))
            out_tmpl = str(tmp_dir / "%(id)s.%(ext)s")
            try:
                ydl_opts = {
                    'format': 'best[height<=720]',
                    'outtmpl': out_tmpl,
                    'quiet': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    local_path = str(tmp_dir / f"{info['id']}.{info['ext']}")
                    if Path(local_path).exists():
                        return local_path
                    # yt-dlp may use a different filename — scan temp dir
                    for f in tmp_dir.iterdir():
                        if f.suffix in ('.mp4', '.webm', '.mkv', '.mov'):
                            return str(f)
                shutil.rmtree(str(tmp_dir), ignore_errors=True)
                return {"error": "YouTube download produced no video file."}
            except Exception as e:
                shutil.rmtree(str(tmp_dir), ignore_errors=True)
                return {"error": f"YouTube download failed: {str(e)}"}

        if video_path:
            return str(Path(video_path).resolve())

        return {"error": "No video URL or file path provided."}

    def _build_video_prompt(self, language, niche_angle, transcript=None,
                            style_preference="", context="",
                            video_duration=0.0, target_word_count=0, wpm=None):
        """Build the prompt for video-based script generation.

        If the active prompt is a master prompt (from Pormpts/) that has a
        "YOUR INPUT:" section, that section gets filled with the user's
        selections.  Otherwise falls back to the generic prompt.

        When video_duration and target_word_count are provided (from the
        actual downloaded file), they are injected into the YOUR INPUT
        section so Gemini doesn't have to guess the word count by ear —
        that guesswork was the root cause of cut-off voiceovers.
        """
        # ── Master-prompt-aware path ──────────────────────────
        # Prefer _master_prompts (Pormpts version with "YOUR INPUT:" section)
        source = None
        if self._active_prompt_key:
            if self._active_prompt_key in self._master_prompts:
                source = self._master_prompts
            elif self._active_prompt_key in self._prompts:
                source = self._prompts
        if source:
            template = source[self._active_prompt_key].get("narration_prompt", "")
            marker = "YOUR INPUT:"
            if marker in template:
                split_idx = template.index(marker)
                base = template[:split_idx]

                # Inject language instruction if not English — the master
                # prompt template has no {language} placeholder, so without
                # this, Gemini gets zero language guidance and defaults to
                # English (only the metadata step respects language).
                lang_name = language.capitalize()
                if lang_name.lower() != "english":
                    base = (
                        f"IMPORTANT: Write the ENTIRE narration script in {lang_name}. "
                        f"Every sentence, every word must be in {lang_name}"
                        f" — do NOT use English.\n\n"
                        f"{base}"
                    )

                style = style_preference or "Pure thriller pace — like \"Continue\" channel"
                filled_input = (
                    "YOUR INPUT:\n"
                    "\n"
                    "VIDEO LINK: [Uploaded — Gemini is watching this video directly]\n"
                    "\n"
                    + (f"VIDEO DURATION: {video_duration:.0f} seconds\n"
                       f"TARGET WORD COUNT: {target_word_count} words"
                       f" — (calculated at {wpm if wpm else 165} WPM for the full duration).\n"
                       f"Your script MUST hit this EXACT word count."
                       f" If you end up with more words than fit, the last lines get CUT OFF.\n"
                       f"\n" if video_duration > 0 and target_word_count > 0 else "")
                    + f"NICHE ANGLE:\n[✓] {niche_angle or 'Thriller / Action'}\n"
                    "\n"
                    f"STYLE PREFERENCE:\n[✓] {style}\n"
                    "\n"
                    f"CONTEXT (optional but powerful):\n"
                    f"{context or '(No context provided)'}\n"
                    "\n"
                    "VOICEOVER STYLE (overall tone — NOT per-line emotions):\n"
                    "Do NOT assign different emotions to each line. Watch the entire video,\n"
                    "understand the context and niche, then decide ONE overall emotional tone\n"
                    "that fits the ENTIRE narrative.\n"
                    "\n"
                    "At the END of your script, add these two lines on their own:\n"
                    "---\n"
                    "VOICEOVER STYLE: <one sentence describing the overall narrator tone, e.g. 'Read aloud in a warm, welcoming tone.' or 'Dark suspense with storytelling flow.'>\n"
                    "VOICEOVER SPEED: <recommended speaking speed in WPM for this content, 140-220 range>\n"
                    "---\n"
                    "RARE EXCEPTION — ONLY if a specific line genuinely requires a different\n"
                    "emotion may you add a per-line [emotion] tag like [whisper], [dramatic],\n"
                    "or [urgent]. The default should be the overall style above.\n"
                )

                full_prompt = base + filled_input

                if transcript and transcript.strip():
                    full_prompt += (
                        f"\n\nADDITIONAL CONTEXT — VIDEO TRANSCRIPT:\n"
                        f"{transcript.strip()}"
                    )

                return full_prompt

        # ── Fallback: generic prompt ──────────────────────────
        parts = [
            "Watch this video carefully. Pay close attention to BOTH the visuals "
            "and the audio/dialogue. Describe everything you see and hear."
        ]

        if transcript and transcript.strip():
            parts.append(
                f"\n\nHere is the transcript from the video to help you:\n{transcript.strip()}"
            )

        angle_text = niche_angle if niche_angle else "general audience"
        parts.append(
            f"\n\nBased on EVERYTHING you see and hear, write a dramatic third-person "
            f"narration script in {language}.\n\n"
            f"Niche / Style: {angle_text}\n\n"
            "Guidelines:\n"
            "- Narrate the key events, actions, emotions, and context you see on screen\n"
            "- Incorporate the dialogue naturally where relevant\n"
            "- Build tension, pacing, and engagement throughout\n"
            "- Write in vivid, cinematic language\n"
            "- Use short punchy sentences for tension, longer flowing ones for reflection\n\n"
            "Write the narration script now (no preamble, no explanations — just the script):"
        )

        return "\n".join(parts)
