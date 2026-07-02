# Script Studio Cleanup Summary — 2026-06-28

## What Was Done

### 1. Fixed hardcoded cross-project path ✅
- **Before:** `script_generator.py:355` reached into `D:\GitHub\ChangeGUI\Pormpts` by absolute path
- **After:** Master prompts copied into `data/master_prompts/`, script_generator now resolves project-relative with legacy fallback
- **Impact:** Project is now portable, no longer depends on a sibling repo

### 2. Merged two tabs into one "Script Studio" tab ✅
- **Before:** "Script Generator" (transcript) + "Video to Script" (video) as separate tabs
- **After:** One "Script Studio" tab with a clear top-level Mode dropdown:
  - *"Rewrite Existing Script — video already has narration/commentary"*
  - *"Write Story from Video — Gemini watches the video (for dialogue-only clips)"*
- **Impact:** Users immediately understand which mode to use; no more confusion between overlapping tabs

### 3. Renamed all 11 prompts for clarity ✅
Every preset now has a self-explanatory name that describes exactly what it does.

**Rewrite mode (7 transcript-based presets):**
| Old name | New clear name |
|----------|----------------|
| Simple Rewrite with Hook | **Rewrite - Same Length + Hook** |
| Movies Commentary | **Movie/Story Recap (dramatic)** |
| Replace Existing Narration | **Replace Voiceover (from transcript)** |
| Dialogue to Narration | **Dialogue to Narration (from transcript)** |
| Educational / Fascinating Facts | **Educational / Facts** |
| Courtroom / Legal Cases | **Courtroom / Legal** |
| Heartwarming Stories | **Heartwarming Stories** |

**Write Story mode (3 video-based presets):**
| Old name | New clear name |
|----------|----------------|
| Movies with Dialogue (No Narration) | **Dialogue-Only Clip to Story Script** |
| Movies Already Has Voiceover | **Clip Has Voiceover - Replace It** |
| Movies Voiceover - Timed Scene Sync | **Timed Scene-by-Scene Sync (matches video timing)** |

`case_commentary` left untouched (used by the separate Case Commentary tab).

### 4. Filtered dropdowns by mode ✅
- **Before:** Both tabs showed all 11 prompts, including ones that didn't work for that mode
- **After:** 
  - Rewrite mode shows only the 7 transcript prompts
  - Write Story mode shows only the 3 video prompts
  - `case_commentary` excluded from both (Case Commentary tab uses it directly)
- **Impact:** No more selecting a prompt that silently fails because it's the wrong type

### 5. Removed confusing flavor dropdowns ✅
- **Removed:** "Niche Angle", "Niche / Style", "Style Preference" dropdowns (they were fake genre lists that didn't correspond to real prompts)
- **Kept:** Language picker (real user choice), Preset picker (the actual prompt), "Manage Presets" button (to edit prompts in-app)
- **What now appears:**
  - **Rewrite mode:** Language + Preset + Manage Presets button
  - **Write Story mode:** Preset + Language
- **Impact:** One dropdown = one clear job. No more choosing "Thriller/Action" when no such preset exists.

### 6. Handled empty niche gracefully in prompts ✅
- The old dropdowns fed `niche_angle` and `style_preference` params to prompts. With dropdowns removed, these are now empty strings.
- **Fix:** Prompt formatters now default empty `niche_angle` to `"the natural tone of this story"` (neutral, doesn't degrade quality)
- Video prompts already had `or` fallbacks for empty values
- **Impact:** No blank "Niche angle:" lines in prompts; quality preserved

## Files Modified
- `core/script_generator.py` — path fix + niche fallback
- `gui/dashboard.py` — merged tab, renamed labels, filtered dropdowns, removed flavor widgets
- `data/script_prompts.json` — renamed all 11 prompt display names
- `data/master_prompts/*.txt` — copied into project (4 files)

## Files Backed Up
All backups in `_backup_before_merge_20260628/`:
- `dashboard.py.bak` (159 KB)
- `script_generator.py.bak` (61 KB)
- `script_prompts.json.bak` (91 KB)

## What Was NOT Touched
- Case Commentary tab (genuinely different: montage clips, intro/outro/CTA)
- All 11 prompts remain accessible and functional
- Excel bulk workflow (Rewrite mode)
- Channel batch processing (Write Story mode)
- Multi-API-key rotation
- "Manage Presets" prompt editor

## Verification
- ✅ Both files compile clean
- ✅ All 11 prompts format without crash (tested empty niche)
- ✅ GUI builds, mode switching works
- ✅ Rewrite dropdown shows exactly 7 prompts, Write Story shows exactly 3
- ✅ `_get_active_prompt_slug()` resolves renamed names back to slugs correctly
- ✅ No references to removed widgets remain
- ✅ Headless smoke test passes

## Result
**Before:** 11 prompts, 3 overlapping tabs, 4 confusing dropdowns with fake genre lists, cross-project hardcoded path.

**After:** 11 prompts (all renamed clearly), 1 unified tab, 2 clear modes, 1 preset dropdown per mode (filtered), no fake flavor lists, portable project.

Users now see exactly what each preset does and which mode to use, with zero ambiguity.

---

## Case Commentary — Niche System (2026-06-28, part 2)

### 7. Real niche dropdown + Edit/Add button ✅
- **Before:** Case Commentary had a dead static `NICHE_OPTIONS` dropdown that fed nothing; generation always used the single hardcoded `case_commentary` prompt.
- **After:**
  - **Niche dropdown** (`cc_niche_menu`) populated live from every `case_commentary*` prompt (base + any `case_commentary_<niche>` you add). Selecting one shows its description in a help box.
  - **"✏️ Edit / Add Niche Prompt"** button opens the prompt manager filtered to ONLY Case Commentary niches (not all 11 prompts).
  - Generation (`_cc_generate`) now uses the **selected** niche's slug, not a hardcoded one.

### 8. Add a new niche with NO code ✅
- Click **Edit / Add Niche Prompt → Add New**. The new niche is **seeded from the base courtroom prompt** so it keeps the required 3-section output format (`=== CASE SUMMARY ===`, `=== MONTAGE CLIPS ===`, `=== COMMENTARY SPOTS ===`) that the parser and Automation Studio depend on.
- You type a short slug (e.g. `movies`) and it's **auto-prefixed** to `case_commentary_movies` so it's discovered as a niche.
- After closing the manager, the new niche **appears in the dropdown automatically** (via `on_close` refresh).
- Edit the seeded text to tell Gemini how to behave for that niche (movie clips, sports, true-crime, etc.) — keep the three `=== ... ===` markers intact.

### 9. Tuned the base Courtroom prompt to spec ✅
The `case_commentary` base prompt now instructs Gemini to output exactly:
- **Intro summary** speakable in **15-20s** (40-55 words), hook-first, ends on a transition line.
- **3-5 montage clips** (~5s each, non-overlapping, chronological, from different parts) for the intro.
- **Commentary spots every 30-60s** through the whole video (value-add analysis, ≤12 words each).
- **CTA** as the final spot (a direct opinion question, ≤15 words).

### Architecture (how niches are discovered)
- Convention: a Case Commentary niche is any prompt whose slug is `case_commentary` (base) or starts with `case_commentary_`.
- `Dashboard.CC_SLUG_PREFIX = "case_commentary"`; helpers `_cc_prompt_entries()`, `_cc_refresh_presets()`, `_cc_selected_slug()`, `_cc_update_preset_help()`, `_cc_edit_prompt()`.
- `PromptManagerDialog` gained `category=` (filters listbox to the prefix) and `on_close=` (refreshes the dropdown). Category-mode `_add_prompt` seeds from base; `_save_current` auto-prefixes the slug.

### Verification (part 2)
- ✅ `dashboard.py` compiles
- ✅ Dropdown populates from `case_commentary*` prompts; base preselected with help text
- ✅ Edit/Add manager shows ONLY case_commentary niches
- ✅ Add New seeds from base (keeps `=== ... ===` format), saves with auto-prefixed slug, appears in dropdown after close
- ✅ Selecting a new niche resolves to its slug; `_cc_generate` uses it
- ✅ Parser still extracts summary + clips + spots from the tuned prompt output
- ✅ Test niche cleaned up — JSON has only `case_commentary`
