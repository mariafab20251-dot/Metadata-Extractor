"""One-shot: rename prompt display names for clarity. Safe — only edits 'name'."""
import json, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = Path("data/script_prompts.json")
data = json.loads(path.read_text(encoding="utf-8"))
prompts = data.get("prompts", {})

# slug -> new clear display name (ASCII-only to avoid console/encoding issues)
renames = {
    # Rewrite mode (transcript-based)
    "simple_rewrite": "Rewrite - Same Length + Hook",
    "movies_commentary": "Movie/Story Recap (dramatic)",
    "replace_existing_narration": "Replace Voiceover (from transcript)",
    "dialogue_to_narration": "Dialogue to Narration (from transcript)",
    "educational_facts": "Educational / Facts",
    "courtroom_legal": "Courtroom / Legal",
    "heartwarming": "Heartwarming Stories",
    # Write Story mode (video-based)
    "movies_with_dialogue": "Dialogue-Only Clip to Story Script",
    "movies_with_voiceover": "Clip Has Voiceover - Replace It",
    "movies_voiceover_timed": "Timed Scene-by-Scene Sync (matches video timing)",
    # case_commentary: left untouched (used by Case Commentary tab)
}

changed = []
for slug, new_name in renames.items():
    if slug in prompts:
        old = prompts[slug].get("name", "")
        if old != new_name:
            prompts[slug]["name"] = new_name
            changed.append(f"  {slug}: {old!r} -> {new_name!r}")

path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Renamed {len(changed)} prompts:")
print("\n".join(changed))
