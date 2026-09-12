# POC5 Data Dictionary

Same 5 files and field shape as POC1-4 — POC5 adds no new data columns and
no new detection logic. `generate_synthetic_data.py`, `detect_and_correlate.py`,
`explain.py`, and `cached_explanations.json` are copied unchanged from POC4.
See `poc4/data_dictionary.md` for the full field list and the explanation
layer's mechanics — both are identical here.

Scope: same as POC3/POC4 — 3 products (Vans Knu Skool, Vans Old Skool, Vans
Sk8-Hi) x 3 regions (West Coast, Northeast, Midwest), 7 of the 9 possible
cells populated, 10 weeks of synthetic weekly data each.

## What's new in POC5: nothing computed, only presented

POC5 is the "Decisions to Take Today" screen the whole series was building
toward — the roadmap's own words: "the demo-ready deliverable that ties
POC1–4 together." Every number, every rule outcome, every confidence score,
and every AI explanation on this screen was already sitting in
`explained_insights.json` before POC5 started. `build_screen.py` is the
only new file, and its job is purely presentational:

- **Leads with the decision, not the evidence.** Each card opens with the
  AI narrative and the recommended action + talking point, in a prominent
  callout — the deterministic rule table, chart, and weekly data are still
  there, just tucked behind a "See the evidence" expander instead of being
  the first thing on the card (POC3/4 led with evidence; POC5 leads with
  what to do about it).
- **A summary strip at the top** — "5 decisions today: 2 Opportunities ·
  2 Product Problems · 1 Demand Not Converting" — read in two seconds
  before opening a single card.
- **A "Mark reviewed" checkbox per card** — a demo-only, browser-local
  toggle (via `localStorage`) that dims a card once it's been looked at.
  It doesn't sync anywhere, doesn't write back to any file, and doesn't
  change detection or ranking — it's there to show what daily use of this
  screen would actually feel like.
- **The footer explicitly lists what each prior POC contributed** — POC1
  (detection), POC2 (three rules), POC3 (scale + ranking), POC4 (AI
  explanation), POC5 (this presentation) — so it's traceable exactly what
  "the end-goal screen" is standing on.

## Files in this folder

| file | role |
|---|---|
| `data_dictionary.md` | this file |
| `generate_synthetic_data.py` | unchanged from POC4 — generates the 7 product/region scenarios |
| `detect_and_correlate.py` | unchanged from POC4 — 3 rules, ranking, promo discount |
| `explain.py` | unchanged from POC4 — the LLM explanation layer (live API if `ANTHROPIC_API_KEY` is set, else cached demo) |
| `cached_explanations.json` | unchanged from POC4 — Claude-generated demo explanations for this dataset |
| `build_screen.py` | **new** — builds the "Decisions to Take Today" presentation |
| `data/<product>_<region>/` | 5 CSVs each, across 7 combinations (unchanged data) |
| `insight_<scenario>.json` | per-scenario deterministic output (unchanged) |
| `ranked_insights.json` | top 5 + cut, deterministic (unchanged) |
| `explained_insights.json` | ranked insights + AI explanations (unchanged) |
| `poc5_screen.html` | **new** — the end-goal screen |
