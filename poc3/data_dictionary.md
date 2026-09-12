# POC3 Data Dictionary

Same 5 files and field shape as POC1/POC2, with one addition: `website.csv` now
carries an `on_promo` flag (0/1), the promo/pricing gap flagged in the planning
doc as a POC3 addition. No other new columns.

Scope: 3 products (Vans Knu Skool, Vans Old Skool, Vans Sk8-Hi) x 3 regions
(West Coast, Northeast, Midwest), 7 of the 9 possible product/region cells
populated, 10 weeks of synthetic weekly data each (2026-06-01 through
2026-08-03). Each region has its own 3 dealers, shared across every product
sold in that region. Data lives under `data/<scenario>/`, one folder per
product/region combination:

| folder | product | region | tuned to trigger |
|---|---|---|---|
| `knu_skool_west_coast` | Vans Knu Skool | West Coast | Opportunity (strong) |
| `old_skool_northeast` | Vans Old Skool | Northeast | Opportunity (weaker) |
| `sk8hi_midwest` | Vans Sk8-Hi | Midwest | Product Problem (strong) |
| `knu_skool_northeast` | Vans Knu Skool | Northeast | Product Problem (milder) |
| `old_skool_west_coast` | Vans Old Skool | West Coast | Demand Not Converting |
| `sk8hi_west_coast` | Vans Sk8-Hi | West Coast | Opportunity shape, but promo-driven |
| `knu_skool_midwest` | Vans Knu Skool | Midwest | nothing (healthy baseline) |

Each is its own independent synthetic window — a real product/region can't be
in three states at once, so `detect_and_correlate.py` runs all 3 rules
against all 7 folders in one pass to prove the engine scales and doesn't
cross-trigger.

All five files share `product` and `region` so they join cleanly on
`(product, region, week_start)`, with `dealer` as the extra key on the two
dealer-level files.

## 1. sales.csv

| field | type | notes |
|---|---|---|
| product | string | one of 3 Vans styles |
| region | string | one of 3 regions |
| week_start | date | Monday of the week, ISO format |
| units_sold | int | weekly units sold, region-wide |

## 2. inventory.csv (Vans-side)

| field | type | notes |
|---|---|---|
| product | string | |
| region | string | |
| week_start | date | |
| vans_inventory_units | int | Vans-owned on-hand stock (warehouse/DC) available to ship into this region |

## 3. dealer_inventory.csv

| field | type | notes |
|---|---|---|
| product | string | |
| region | string | |
| dealer | string | one of 3 dealers in the region, shared across products |
| week_start | date | |
| dealer_inventory_units | int | units on the dealer's own shelf/stockroom |

## 4. website.csv

| field | type | notes |
|---|---|---|
| product | string | |
| region | string | |
| week_start | date | |
| searches | int | weekly on-site searches for the product |
| views | int | weekly product page views |
| conversion_rate | float | views → purchase rate, 0-1 |
| **on_promo** | int (0/1) | **new in POC3** — whether the product was on a promotion/discount that week |

## 5. customer.csv

| field | type | notes |
|---|---|---|
| product | string | |
| region | string | |
| week_start | date | |
| returns | int | weekly units returned |
| review_sentiment | float | -1 (negative) to +1 (positive), average of that week's reviews |

## Derived, not stored

- Week-over-week (WoW) % change per metric, plus an absolute-delta check for
  `review_sentiment` — computed, not generated (`detect_and_correlate.py`)
- Three rule outcomes per product/region — Opportunity, Product Problem,
  Demand Not Converting — each with its own confidence score, computed output
  (`insight_<scenario>.json`, one per triggered combo)
- **New in POC3 — promo-adjusted confidence:** when a triggering trend's
  window is majority (`>=50%`) on-promo, confidence is discounted 25% and the
  insight is flagged `promo_influenced: true` with the raw and discounted
  confidence both shown.
- **New in POC3 — ranking:** every triggered situation across every
  product/region is sorted by confidence and only the top 5 are surfaced
  (`ranked_insights.json`, with the rest listed as "cut").
