"""One-shot: add a JSON stub for the master-only slug `cctv_surveillance`
so _slug_for_name / Manage-Presets preselect / display-name resolution work
the same way they do for the other Write Story master slugs (movies_*,
courtroom_legal, heartwarming — all of which have JSON stubs too).

The actual prompt used by Write Story still comes from the master .txt
(_build_video_prompt prefers _master_prompts). This stub just supplies the
display name + description for the dropdown/resolver. Safe — only adds one key.
"""
import json, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = Path("data/script_prompts.json")
data = json.loads(path.read_text(encoding="utf-8"))
prompts = data["prompts"]

# Mirror the master .txt content into the JSON narration_prompt so the stub is
# self-consistent if ever read directly; master .txt still wins for generation.
master_txt = Path("data/master_prompts/CCTV Surveillance Footage Master Prompt.txt")
content = master_txt.read_text(encoding="utf-8") if master_txt.exists() else ""

# Seed metadata_prompt from an existing master slug so the shape matches.
seed = prompts.get("courtroom_legal", {})

prompts["cctv_surveillance"] = {
    "name": "CCTV / Surveillance Footage",
    "description": (
        "Surveillance/CCTV footage narration — Gemini picks the most shocking "
        "moment for a hook-sized intro clip, then narrates the full video in "
        "grounded third-person, ending on a freeze-frame CTA."
    ),
    "narration_prompt": content,
    "metadata_prompt": seed.get("metadata_prompt", ""),
}

path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("Added JSON stub cctv_surveillance:")
print("  name:", prompts["cctv_surveillance"]["name"])
print("  narration_prompt length:", len(prompts["cctv_surveillance"]["narration_prompt"]))
print("  distinct from case_commentary_cctv:",
      "case_commentary_cctv" in prompts and prompts["case_commentary_cctv"]["name"])
