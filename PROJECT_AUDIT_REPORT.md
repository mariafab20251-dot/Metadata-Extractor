# Project Audit Report — VideoTextExtractor

**Audit date:** 2026-06-28
**Scope:** Full architecture, prompt engineering, UX, code quality, scalability
**Codebase size:** ~8,700 LOC across 17 Python modules + 113 KB of prompt JSON + 4 external master-prompt files
**Nature:** Analysis & recommendations only — **no refactors were performed.**

---

## 1. Executive Summary

VideoTextExtractor is a **dual-purpose application** that has organically grown two distinct products under one roof:

1. **A multi-platform video scraper / metadata harvester** (YouTube, Instagram, TikTok, Facebook, Xiaohongshu) → download → OCR overlay text + Whisper transcription → SQLite + Excel/CSV/JSON reports.
2. **An AI script-generation studio** (Gemini-based) that turns transcripts *or* raw video into short-form narration scripts across many content niches.

The application **works and is in active daily use**, but it carries the structural debt typical of a fast-moving solo project: a 3,453-line GUI god-file, three near-identical Excel exporters, eleven prompts that are 70–85 % copy-paste of each other, a hardcoded cross-project file path, and invalid model IDs that only survive because of a silent fallback chain.

**The single highest-leverage change** is not a bug fix — it is **collapsing the prompt sprawl into a composable template system**. That one change unlocks the stated goal of scaling to 50–200 niches; today each new niche means copying ~250 lines of boilerplate.

### Top 5 priorities (detail in §13)

| # | Item | Severity | Effort |
|---|------|----------|--------|
| 1 | Hardcoded cross-project path `D:\GitHub\ChangeGUI\Pormpts` | 🔴 Critical | XS (1 hr) |
| 2 | Invalid Gemini model IDs (`gemini-3.5-flash`, `gemini-3.1-flash-lite`) | 🔴 Critical | XS (30 min) |
| 3 | Prompt architecture → composable template system | 🟠 High | L (2–3 days) |
| 4 | Consolidate 3 Excel exporters + split GUI god-file | 🟠 High | M (1–2 days) |
| 5 | Multi-LLM abstraction layer (provider-agnostic) | 🟡 Medium | M (1–2 days) |

---

## 2. Current Architecture

### 2.1 Module map

```
main.py (517)              VideoProcessor — orchestrates scrape→extract→export
config.py (34)             Paths, WHISPER_MODEL, FRAME_INTERVAL, flags
│
├── core/
│   ├── database.py (129)        VideoDatabase — SQLite, schema-migrate-on-boot
│   ├── downloader.py (417)      yt-dlp wrapper
│   ├── extractor.py (441)       MediaExtractor — Whisper + EasyOCR
│   ├── metadata_scanner.py(844) Fast flat-playlist channel scan
│   ├── exporter.py (430)        DataExporter — CSV/JSON/TXT/Excel (×3 variants)
│   └── script_generator.py(1404) ScriptGenerator — ALL Gemini logic
│
├── platforms/
│   ├── youtube.py (62)          metadata + URL normalization
│   ├── instagram.py (310)       heaviest scraper (session/login)
│   ├── tiktok.py (48)
│   ├── facebook.py (32)
│   └── xiaohongshu.py (593)     CDP interception, cookie domain reversal
│
├── gui/
│   └── dashboard.py (3453)      ⚠️ GOD FILE — all 7 tabs + helpers
│
└── data/
    ├── script_prompts.json (113 KB, 11 prompts)
    ├── processed.db, results.{csv,json,xlsx}
    └── service-account-key.json, gemini_config.json  (gitignored ✅)
```

### 2.2 Data flow

**Scrape path:**
`URL → VideoProcessor.parse_input() → platform scraper (metadata) → downloader (yt-dlp) → MediaExtractor (Whisper transcript + EasyOCR frames) → VideoDatabase.save → DataExporter → per-channel reports/`

**Script path (transcript):**
`DB transcript → ScriptGenerator.generate_script() → niche prompt template (JSON) → Gemini → parsed script → scripts_export.xlsx`

**Script path (video):**
`Video file → ScriptGenerator._upload_video() (Gemini File API) → _build_video_prompt() (master prompt from Pormpts/) → Gemini watches video → structured script`

### 2.3 Architectural observations

- **Two products, one process.** The scraper and the script studio share only the SQLite DB and the GUI shell. They could be split into independently runnable tools with no functional loss.
- **The GUI owns business logic.** `dashboard.py` doesn't just render — it contains batch loops, Excel assembly, response parsing (`_cc_parse_response`), and orchestration. This is why it's 3,453 lines and why every feature touches it.
- **`ScriptGenerator` is a second god-object** (1,404 lines): auth (4 methods), key rotation, quota fallback, model fallback, prompt loading from *two* sources (JSON + external folder), video upload, and response parsing — all in one class.

---

## 3. Video-to-Script Module Review

**Strengths**
- Genuinely differentiated: Gemini watches the video directly (File API upload), so it captures visual beats OCR/transcript miss.
- Batch channel processing with per-video status tracking is a real productivity feature.
- Optional context/backstory textarea is a smart escape hatch for nuance.

**Weaknesses**
- `_build_video_prompt()` depends on master prompts loaded from a **hardcoded foreign repo path** (§6.1). On any other machine this tab silently degrades.
- The "optional transcript" toggle duplicates intent with the Script Generator tab — users can't tell which tab to use for a given job (§8).
- Batch loop runs **synchronously on the GUI thread region** (status flips to "processing" but a long upload blocks). No cancel, no per-item retry surfaced to UI.
- Video upload has no size/duration guard before hitting the File API.

---

## 4. Script Generator Module Review

**Strengths**
- Mature multi-key rotation with exhaustion tracking (`_exhausted_keys`) and round-robin (`_get_current_api_key`).
- Four auth methods give resilience against Gemini's shifting endpoints.

**Weaknesses**
- **Invalid model IDs** (§6.2) — the primary model literally doesn't exist; the app only works because the fallback chain catches it. Every first call wastes a round-trip on a guaranteed 404.
- Prompt loading is **bifurcated**: JSON prompts for transcript mode, external `.txt` master prompts for video mode, with slugs that overlap (`heartwarming`, `courtroom_legal`) resolving differently per tab. This is documented in a docstring (lines 341–354) precisely *because* it's confusing — a sign the design is wrong, not the comment.
- Hardcoded `Path(r"D:\GitHub\ChangeGUI\Pormpts")` makes the class non-portable.
- Response parsing is string-splitting on section headers — brittle to model wording drift.

---

## 5. Case Commentary Module Review

**Strengths**
- Clear, opinionated output structure (Summary / Montage Clips / Commentary Spots) presented in a 3-tab results notebook.
- Solves a real workflow (react/commentary content) end-to-end.

**Weaknesses**
- **Functional overlap with Video-to-Script.** Both upload a video to Gemini and produce a script-shaped artifact. The only real difference is the output schema. This should be *one* "Analyze Video" engine with selectable output templates, not two tabs with two code paths and two Excel exporters.
- `_cc_parse_response()` is another bespoke header-splitter — third independent parser in the codebase.
- `case_commentary` exists as an 11th JSON prompt *and* has its own tab logic — the prompt and the consumer are coupled across files.

---

## 6. Bugs Report

### 6.1 🔴 Hardcoded cross-project path
`core/script_generator.py:355`
```python
pormpts_dir = Path(r"D:\GitHub\ChangeGUI\Pormpts")
```
The script-generation core of one project reaches into a *sibling project's* folder by absolute Windows path. Breaks on any other machine, any path change, and couples two repos that should be independent.
**Fix:** Move the 4 master-prompt `.txt` files into this repo (`data/master_prompts/`), reference via `BASE_DIR`. ~1 hr including the file move.

### 6.2 🔴 Invalid Gemini model IDs
`core/script_generator.py:23-24`
```python
MODEL_NAME = "gemini-3.5-flash"              # does not exist
FALLBACK_MODELS = ["gemini-2.5-flash",
                   "gemini-3.1-flash-lite",  # does not exist
                   "gemini-2.0-flash-lite"]
```
Real current IDs are `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`. The primary and one fallback are fictional; every cold call burns a 404 before the chain finds `gemini-2.5-flash`.
**Fix:** Set `MODEL_NAME = "gemini-2.5-flash"`; prune fictional fallbacks. 30 min. **Verify current IDs against the live Gemini model list before committing.**

### 6.3 🟡 Synchronous batch on UI thread
Video-to-Script and Case Commentary batch loops block during upload/inference with no cancel. Long jobs freeze the window.
**Fix:** Move to a worker thread with a queue + cancel flag (the pattern already exists elsewhere in the GUI).

### 6.4 🟡 No video size/duration guard before File API upload
Large files fail late (after upload) instead of early with a clear message.

### 6.5 🟢 Brittle response parsing (×3)
Three independent header-split parsers (`generate_script`, `_build_video_prompt` consumer, `_cc_parse_response`). Any model wording change silently corrupts output.
**Fix:** Ask the model for JSON output (Gemini supports `response_mime_type: application/json`) and parse once.

> **Correction to a prior finding:** I initially flagged `service-account-key.json` as committed. **It is not** — `.gitignore` covers `data/*.json` and `data/cookies.txt`, and `git ls-files` confirms none of the secrets are tracked. No credential exposure in version control. ✅

---

## 7. Master Prompt Audit

### 7.1 Inventory

**JSON prompts** (`data/script_prompts.json`, 11 total, 111 KB of prompt text):
`movies_commentary`, `replace_existing_narration`, `dialogue_to_narration`, `educational_facts`, `courtroom_legal`, `heartwarming`, `movies_with_dialogue`, `simple_rewrite`, `case_commentary`, `movies_with_voiceover`, `movies_voiceover_timed`

**External master prompts** (`ChangeGUI/Pormpts/`, 4 files, 1,307 lines):
- `Master Prompt For Movies clips With Dialougs.txt` (440 lines)
- `ALREADY HAVE a voiceover On Movies Clips.txt` (367 lines)
- `Courtroom Legal Cases Master Prompt.txt` (284 lines)
- `Heartwarming Stories Master Prompt.txt` (216 lines)

### 7.2 Duplication — measured, not estimated

| Prompt | chars | lines | PHASE blocks |
|--------|------:|------:|-------------:|
| `dialogue_to_narration` | 7,958 | 233 | 9 |
| `replace_existing_narration` | 6,796 | 185 | 6 |

These two share the **same skeleton**: `ROLE → PHASE 1 ANALYZE → PHASE 2 STRICT RULES → PHASE 3 HOOK → PHASE 4 SCRIPT → PHASE 5 CLOSE/CTA → PHASE 6 DELIVERABLES → PHASE 7 SELF-CHECK`. The same is true across the external master prompts — the courtroom and movies-dialogue files differ mainly in the ROLE paragraph and a handful of niche rules; the PHASE machinery (word-count formula at 270 WPM, naming rules, deliverables package, self-check) is **near-identical boilerplate repeated 11 times**.

**Estimated redundancy: 70–85 % of prompt text is shared scaffolding.** Of ~113 KB, roughly 80–90 KB is duplicated structure.

### 7.3 Merge / obsolete candidates

- **Merge:** `replace_existing_narration` ⊕ `movies_with_voiceover` ⊕ `movies_voiceover_timed` — all three are "a voiceover already exists, replace it." Differ only in timing strictness → should be **one prompt + a `timing_mode` parameter**.
- **Merge:** `dialogue_to_narration` ⊕ `movies_with_dialogue` — both are "only dialogue exists, write narration." Near-duplicates living in JSON *and* the external folder.
- **Likely obsolete:** `simple_rewrite`, `movies_commentary` — verify usage; if unused, archive.
- **Cross-file duplication:** `heartwarming` and `courtroom_legal` exist as *both* JSON and external `.txt`, resolved differently per tab (§4).

---

## 8. Prompt Architecture Proposal

Replace the flat 11-prompt JSON + external-folder split with a **composable template system**:

```
data/prompts/
  _base/
    role.md            # shared role framing (parameterized by {channel_style})
    phases.md          # PHASE 1–7 scaffolding with {slots}
    rules.md           # naming, WPM formula, deliverables, self-check
    output_schema.json # the JSON shape the model must return
  niches/
    courtroom.yaml     # ONLY: role override + niche rules + examples
    heartwarming.yaml  # ONLY: role override + niche rules + examples
    movies.yaml        # role + mode flags (dialogue|voiceover|timed)
    ...
```

A niche file becomes ~20–40 lines instead of ~250:
```yaml
name: Courtroom / Legal Cases
extends: _base
role: >
  You are a legal story narrator for YouTube Shorts, style "Law&Order_Live"…
mode: video            # transcript | video
wpm: 270
rules:
  - Use role labels ("the daughter", "the defendant"), never surnames
  - Never reference channel/creator names
examples: [...]
```

**Build prompt at runtime** by composing `_base` + niche overrides. Benefits:
- New niche = one small file (the 50–200 niche goal becomes feasible).
- Fix the WPM formula or self-check **once**, not 11 times.
- Single source of truth eliminates the JSON-vs-external-folder bifurcation and the cross-project path.
- `output_schema.json` enables structured JSON responses → kills all three bespoke parsers.

---

## 9. UX Review

| Issue | Impact |
|-------|--------|
| **Three tabs that all "make a script from a video"** (Script Gen, Video-to-Script, Case Commentary) with overlapping inputs | Users can't predict which tab to use; cognitive load |
| Niche / language / style dropdowns **repeated on 3 tabs** with no shared state | Re-selecting the same settings per tab |
| Two separate "Add API key" UIs | Confusion about which keys apply where |
| Batch jobs block the window, no progress/cancel | Feels frozen on long runs |
| "Optional transcript" toggle meaning unclear | Users unsure what it changes |

**Recommendation:** Collapse the three script tabs into **one "Generate Script" tab** with a single top-level choice — *Source* (Transcript / Upload Video / Channel Video) and *Output Template* (Narration / Commentary / Timed Voiceover). One settings bar, one batch engine, one exporter.

---

## 10. Product Improvements

1. **Unify the three script workflows** into one engine (biggest UX win, §9).
2. **Preset profiles** — save a (niche + language + style + source) combo as a named preset; one click to re-run a channel's standard pipeline.
3. **Cost/quota meter** in the UI — show tokens/requests used per key (the data already exists in the rotation logic).
4. **Dry-run / preview** — show the assembled prompt before spending a Gemini call.
5. **Output history** — the DB already stores `generated_script`; surface a "previously generated" view to avoid regenerating.

---

## 11. Code Quality & Technical Debt

| Item | Where | Note |
|------|-------|------|
| GUI god-file | `dashboard.py` (3,453) | Split per-tab into `gui/tabs/*.py`; move batch/export/parse logic out of UI |
| ScriptGenerator god-class | `script_generator.py` (1,404) | Separate auth, rotation, prompt-loading, video-upload, parsing |
| 3× Excel exporters | `exporter.py` (`generate_excel_report`, `export_scripts_excel`) + Case Commentary tab | Collapse into one parameterized exporter |
| 3× response parsers | script_generator + dashboard | Replace with single JSON-schema parse |
| Schema-migrate-on-boot | `database.py` (8× `_add_column_if_missing`) | Works, but a real migration table would be cleaner as columns grow |
| Hardcoded GPU=False | `extractor.py:39,45` | EasyOCR forced to CPU; expose a config flag (you have NVENC elsewhere) |
| Magic constants | 270 WPM, `FRAME_INTERVAL=10` | Centralize in config / prompt params |

**Dead/uncertain code:** verify `simple_rewrite`, `movies_commentary` prompts and any unused scraper paths before removal.

---

## 12. Scalability Review

**Goal: multi-LLM support + 50–200 niches.**

### 12.1 Multi-LLM
Today Gemini is hardwired (auth methods, model IDs, File API upload all Gemini-specific). To support OpenAI / Anthropic / local models:
- Introduce a **`LLMProvider` interface**: `generate(prompt, media?) -> structured_response`.
- Implement `GeminiProvider` (wrap existing logic), then `OpenAIProvider`, `AnthropicProvider`.
- Video handling differs per provider (Gemini File API vs. frame-sampling for others) — the interface must express "native video" vs "frames" capability so niches that need video can route to capable providers.

### 12.2 50–200 niches
**Blocked today** by the copy-paste prompt model (§7–8). With the composable template system (§8), adding a niche is a 20–40 line YAML file. Add:
- A **niche registry** (auto-discover `niches/*.yaml`) so the GUI dropdown populates dynamically.
- Per-niche **eval examples** to catch regressions when the shared `_base` changes.

---

## 13. AI Model Cost Optimization

- **Default to `gemini-2.5-flash`** for narration (cheap, fast, sufficient). Reserve `gemini-2.5-pro` for complex video analysis only — make it a per-niche flag.
- **Stop the 404 tax** (§6.2): every cold call currently fails one invalid model first.
- **Structured JSON output** reduces re-prompts caused by parse failures.
- **Frame-sampling fallback** for non-video-native providers is far cheaper than full video upload when visual fidelity isn't critical.
- For *this audit-style* analysis work, cheaper models (Flash/Haiku-tier) are the right tool — reserve premium models for the actual creative generation.

---

## 14. Prioritized Improvement Roadmap

### Phase 0 — Stop the bleeding (½ day) 🔴
1. Fix invalid model IDs (§6.2) — 30 min
2. Move master prompts into repo, kill hardcoded path (§6.1) — 1 hr
3. Verify & archive obsolete prompts (§7.3) — 1 hr

### Phase 1 — Structural foundation (3–4 days) 🟠
4. Composable prompt template system (§8) — 2–3 days
5. Single JSON-schema response parser (§6.5) — ½ day
6. Consolidate 3 Excel exporters (§11) — ½ day

### Phase 2 — UX unification (2–3 days) 🟠
7. Merge 3 script tabs into one engine (§9) — 2 days
8. Split `dashboard.py` into per-tab modules (§11) — 1 day
9. Background worker + cancel for batch jobs (§6.3) — ½ day

### Phase 3 — Scale enablement (3–4 days) 🟡
10. `LLMProvider` abstraction + GeminiProvider (§12.1) — 2 days
11. Niche registry + auto-discovery (§12.2) — 1 day
12. Cost/quota meter + presets (§10) — 1 day

**Total to a clean, scalable base: ~9–11 working days.** Phase 0 alone (½ day) removes the two critical portability/correctness bugs and should ship immediately.

---

## Appendix — Audit method & confidence

- **High confidence** (read directly): `script_generator.py`, `database.py`, `extractor.py`, `exporter.py` signatures, `dashboard.py` tabs 3–5, all prompt files, git tracking state, prompt size/duplication (measured programmatically).
- **Medium confidence** (sampled): platform scrapers, `downloader.py`, `metadata_scanner.py`, Settings/Activity-Log tabs.
- **Verify before acting:** current Gemini model IDs against the live API; actual usage of `simple_rewrite`/`movies_commentary`; whether any external tooling depends on the current 3-exporter Excel formats.
- **No code was modified.** All findings are advisory.
