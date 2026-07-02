"""One-shot: tune the base case_commentary prompt to the user's exact spec
(summary 15-20s, clips ~5s, commentary spots every 30-60s) and refresh its
description. Safe — only touches the 'case_commentary' prompt.
"""
import json, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = Path("data/script_prompts.json")
data = json.loads(path.read_text(encoding="utf-8"))
p = data["prompts"]["case_commentary"]

new_prompt = """ROLE:
You are a courtroom legal analyst and storyteller. I am going to give you a full courtroom case video. Watch it carefully - understand the people, the arguments, the judge's reactions, the key evidence, and the outcome.

Your job is NOT to write a scene-by-scene narration. Instead, you will output THREE sections exactly as specified below.

========================================
OUTPUT SECTION 1: CASE SUMMARY (INTRO)
========================================

Write a short, punchy summary of the case that can be spoken in 15-20 seconds (40-55 words). This becomes the INTRO voiceover of the video. It must:
- Start with a hook that grabs attention immediately (max 12 words)
- Explain: who is suing/accusing whom + why
- End with a transition like "Here's how it unfolded." or "Here's what happened in court."
- Be written for voiceover delivery - natural, spoken language
- Your summary MUST be in {language}

========================================
OUTPUT SECTION 2: MONTAGE CLIPS
========================================

Identify 3 to 5 short clips from the video (each about 5 seconds) that capture the MOST dramatic, emotional, or key moments of the case. These are shown at the START of the video, played one after another while the intro summary voiceover plays over them.

For each clip, provide:
- START and END timestamp in this format: MM:SS-MM:SS
- A ONE-LINE description of what happens in that clip (max 8 words)

RULES for clips:
- Each clip must be about 5 seconds long (4-6 seconds acceptable)
- Clips must NOT overlap
- Sort them chronologically
- Pick clips from DIFFERENT parts of the video (not all from the first minute)
- Prioritize: emotional reactions, key evidence, judge's moment, dramatic testimony

========================================
OUTPUT SECTION 3: COMMENTARY SPOTS + CTA
========================================

Generate commentary narration spots spaced 30 to 60 seconds apart throughout the ENTIRE duration of the video. These play during the main (original) video. They are moments where you, as the legal analyst, add your insight/analysis - spots where:
- Something legally significant happens
- The viewer needs context to understand WHY something matters
- A character's reaction is more important than what is being said

IMPORTANT FREQUENCY RULE:
- Space commentary spots 30-60 seconds apart
- If the video is 5 minutes, you need ~5-10 spots
- If the video is 10 minutes, you need ~10-20 spots
- NEVER leave a gap longer than 60 seconds without commentary

For each spot, provide:
- TIMESTAMP (MM:SS) - when the commentary should start
- COMMENTARY TEXT (max 12 words) - what you would say. A short, punchy observation.
  - It must be a VALUE-ADD analysis, NOT describing what's on screen
  - Example good: "This is where the case turns against the defendant."
  - Example bad: "The judge is looking at the papers."

The commentary spots are delivered as a short voiceover / text overlay at those moments, spoken in 3-5 seconds.

LAST SPOT - CALL TO ACTION (CTA):
The FINAL commentary spot at the very end of the video must be a STRONG Call to Action. It must:
- Be the last line in the COMMENTARY SPOTS section (last timestamp in the video)
- Start with "CTA:"
- Maximum 15 words
- Ask the viewer a direct question about their opinion on the case's moral/legal dilemma
- Examples:
  "CTA: Was this justice or cruelty? What would you have decided?"
  "CTA: Do you think the punishment fit the crime? Tell us below."
  "CTA: Would you have done the same in their situation? Comment now."

========================================
OUTPUT FORMAT - EXACTLY THIS
========================================

Output ONLY the three sections below. No preamble, no explanations, no extra text.

=== CASE SUMMARY ===
[your summary text here - 40 to 55 words, in {language}]

=== MONTAGE CLIPS ===
MM:SS-MM:SS | description of clip
MM:SS-MM:SS | description of clip
MM:SS-MM:SS | description of clip

=== COMMENTARY SPOTS ===
MM:SS | commentary text
MM:SS | commentary text
... (one every 30-60 seconds throughout the full video)
MM:SS | CTA: call to action text at the very end
"""

p["narration_prompt"] = new_prompt
p["name"] = "Courtroom / Legal Cases"
p["description"] = (
    "Courtroom legal cases. Gemini watches the video and outputs: a 15-20s "
    "intro summary (hook), 3-5 montage clips (~5s each) for the intro, and "
    "commentary spots every 30-60s through the whole video plus a CTA at the end."
)

path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("Updated case_commentary:")
print("  name:", p["name"])
print("  desc:", p["description"])
print("  prompt length:", len(p["narration_prompt"]))
print("  has {language}:", "{language}" in p["narration_prompt"])
