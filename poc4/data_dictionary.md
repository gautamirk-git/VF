# POC4 Data Dictionary

Same 5 files and field shape as POC1-3 — POC4 adds no new data columns.
The only thing new is a layer that reads the *output* of the deterministic
engine (`ranked_insights.json`, unchanged from POC3) and writes a plain-
language explanation next to each situation.

Scope: same as POC3 — 3 products (Vans Knu Skool, Vans Old Skool, Vans
Sk8-Hi) x 3 regions (West Coast, Northeast, Midwest), 7 of the 9 possible
cells populated, 10 weeks of synthetic weekly data each. Same `on_promo`
flag in `website.csv`. See `poc3/data_dictionary.md` for the full field
list — it's identical here.

## What's new in POC4: the explanation layer

Nothing upstream of `ranked_insights.json` changed. POC4 adds one new
step, `explain.py`, and one new output file per run:

**`explain.py`** — for each of the top 5 ranked situations (and, so the
"why cut" story is complete, the situation(s) that got cut), it:
1. Builds an **evidence pack**: a small JSON object with only numbers the
   deterministic engine already computed (situation type, product, region,
   week window, the % changes, confidence, dealer figures if relevant,
   promo caveat if relevant). No new data, nothing invented.
2. Sends that evidence pack to Claude with a fixed system prompt (see
   `explain.py`'s `SYSTEM_PROMPT`) asking for four things back: a 2-3
   sentence narrative, 3-4 evidence bullets citing specific numbers, a
   one-sentence confidence rationale, and a one-sentence talking point.
3. If `ANTHROPIC_API_KEY` is set in the environment, this is a real,
   live call to the Anthropic API. If it isn't (the case in this sandbox —
   no key was available here), it reads the matching entry from
   `cached_explanations.json` instead — text Claude generated once, from
   this exact evidence, for this fixed demo dataset. Either way the output
   shape is identical; only the source of the text differs, and switching
   from cached to live needs no other code change, just an API key.

**`ranked_insights.json`** — unchanged output from `detect_and_correlate.py`
(same as POC3). This is the ground truth: which situations are real and
how confident to be. The explanation layer never edits this.

**`explained_insights.json`** — the new output. Same top-5 + cut structure
as `ranked_insights.json`, with each insight additionally carrying:

| field | notes |
|---|---|
| `ai_explanation.narrative` | 2-3 sentence plain-language summary |
| `ai_explanation.key_evidence` | 3-4 bullet strings, each citing a real number |
| `ai_explanation.confidence_rationale` | 1 sentence explaining the score in plain language |
| `ai_explanation.suggested_talking_point` | 1 sentence — what a stocker/merchandiser would actually say |
| `ai_explanation_source` | `"live_api"` or `"cached_demo"` |
| `evidence_pack_sent_to_llm` | the exact object handed to the LLM — full transparency into what it did and didn't see |

## Why this proves the concept the roadmap called for

The planning doc's POC4 goal was: "Add the LLM layer that turns each
[situation] into a plain-language explanation with cited evidence and a
confidence score — this should sit on top of the deterministic
detection/correlation logic from POC1–3, not replace it." This POC keeps
that boundary literal in the code: `detect_and_correlate.py` is untouched
from POC3, `explain.py` only ever reads its output, and the confidence
score itself is never regenerated or overridden by the LLM step — only
explained.
