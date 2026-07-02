"""One-shot: add a CCTV / Surveillance niche to the Case Commentary tab.

Adds prompt slug `case_commentary_cctv` in the SAME three-section output
format the Case Commentary parser + Automation Studio require
(=== CASE SUMMARY ===, === MONTAGE CLIPS ===, === COMMENTARY SPOTS ===),
but with CCTV surveillance narration tone, a shocking-moment intro, and a
freeze-frame CTA as the final spot. Safe — only adds one new key.
"""
import json, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = Path("data/script_prompts.json")
data = json.loads(path.read_text(encoding="utf-8"))
prompts = data["prompts"]

# Seed from the base case_commentary so it keeps required fields, then override.
base = dict(prompts["case_commentary"])

narration_prompt = """ROLE:
You are a CCTV / surveillance footage analyst and short-form narrator. I am going to give you a piece of surveillance or CCTV footage. Watch it carefully - read the location, the people, the camera angle, the key moment where everything changes, and what the camera caught that the people in the frame did not notice.

Your tone is grounded and observational - like a news anchor narrating breaking footage, combined with a true-crime documentary narrator. Serious, not sensational. Always third person ("the man", "the woman", "the individual", "the suspect", "the bystander"). Use "appears to" when intent is unclear. Never invent facts not visible. Never use real names of unknown people. Never say "in this video" or "on screen".

Your job is NOT to write a scene-by-scene script. Instead, output THREE sections EXACTLY as specified below.

========================================
OUTPUT SECTION 1: CASE SUMMARY (INTRO HOOK)
========================================

This becomes the INTRO voiceover, spoken over the single most shocking moment of the footage (see Section 2). Write a short, punchy hook that can be spoken in 8-15 seconds (25-45 words). It must:
- Open with a scroll-stopping hook line (max 10 words) - make it impossible to look away
- NEVER reveal the outcome
- Speak to what the camera caught that the people in the frame missed
- End on a transition like "Watch closely." or "Here is what the camera saw."
- Be written for voiceover delivery - grounded, news-anchor tone
- Your summary MUST be in {language}

========================================
OUTPUT SECTION 2: MONTAGE CLIPS
========================================

Identify the MOST shocking / important moment in the footage - the frame where everything changes - and 1 to 3 short clips (each about 5 seconds) around it and other key beats. These are shown at the START while the intro hook voiceover plays.

For each clip, provide:
- START and END timestamp in this format: MM:SS-MM:SS
- A ONE-LINE description of what happens (max 8 words)

RULES for clips:
- The FIRST clip must be the single most shocking moment
- Each clip about 5 seconds long (4-6 seconds acceptable)
- Clips must NOT overlap
- Sort them chronologically
- Prioritize: the key moment, the reaction, the detail others missed

========================================
OUTPUT SECTION 3: COMMENTARY SPOTS + CTA
========================================

After the intro, the ORIGINAL footage plays in full. Generate commentary narration spots spaced 30 to 60 seconds apart across the ENTIRE duration, so the voiceover covers the whole video. These are the moments where you, as the analyst, add insight - what the subject is doing, what others fail to notice, the exact moment things change, and what the camera reveals.

IMPORTANT FREQUENCY RULE:
- Space commentary spots 30-60 seconds apart
- NEVER leave a gap longer than 60 seconds without commentary
- If the video is 3 minutes, you need ~3-6 spots; if 6 minutes, ~6-12 spots

For each spot, provide:
- TIMESTAMP (MM:SS) - when the commentary should start
- COMMENTARY TEXT (max 12 words) - a short, grounded observation
  - VALUE-ADD analysis, NOT describing the obvious
  - Use CCTV language: "enters the frame", "approaches", "undetected", "in plain sight", "without hesitation"
  - Example good: "Nobody behind the counter notices his left hand."
  - Example bad: "The man is standing in the store."

LAST SPOT - CALL TO ACTION (CTA) over the FROZEN final frame:
The FINAL commentary spot at the very end must be a STRONG Call to Action. The editor freezes the last frame while it is spoken. It must:
- Be the last line in the COMMENTARY SPOTS section (last timestamp)
- Start with "CTA:"
- Maximum 15 words
- Ask the viewer a direct question about what they would have done or noticed
- Examples:
  "CTA: What would you have done if you saw this? Comment below."
  "CTA: Did you catch the moment it all changed? Drop the timestamp."
  "CTA: Did they deserve what happened next? Tell me your verdict."

========================================
OUTPUT FORMAT - EXACTLY THIS
========================================

Output ONLY the three sections below. No preamble, no category label, no analysis, no extra text.

=== CASE SUMMARY ===
[your intro hook here - 25 to 45 words, in {language}]

=== MONTAGE CLIPS ===
MM:SS-MM:SS | most shocking moment
MM:SS-MM:SS | description of clip
MM:SS-MM:SS | description of clip

=== COMMENTARY SPOTS ===
MM:SS | commentary text
MM:SS | commentary text
... (one every 30-60 seconds across the full video)
MM:SS | CTA: call to action over the frozen final frame
"""

base["narration_prompt"] = narration_prompt
base["name"] = "CCTV / Surveillance Footage"
base["description"] = (
    "Surveillance/CCTV footage. Gemini finds the most shocking moment for a "
    "hook intro clip, picks 1-3 montage clips, then narrates the full video "
    "as grounded commentary spots every 30-60s, ending on a freeze-frame CTA."
)

prompts["case_commentary_cctv"] = base

path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("Added case_commentary_cctv:")
print("  name:", base["name"])
print("  prompt length:", len(base["narration_prompt"]))
print("  has {language}:", "{language}" in base["narration_prompt"])
print("  has 3 markers:", all(m in base["narration_prompt"] for m in
      ("=== CASE SUMMARY ===", "=== MONTAGE CLIPS ===", "=== COMMENTARY SPOTS ===")))
