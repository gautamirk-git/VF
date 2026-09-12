# POC2 Data Dictionary

Same 5 files and fields as POC1 — POC2 doesn't add columns, it adds two more rules that read the columns already here (`returns` / `review_sentiment` for Product Problem, `searches` / `conversion_rate` for Demand Not Converting).

Scope: 1 product (Vans Knu Skool), 1 region (West Coast), 3 dealers in that region, 10 weeks of synthetic weekly data (2026-06-01 through 2026-08-03) — generated **3 times**, once per situation type, into `data/opportunity/`, `data/product_problem/`, and `data/demand_not_converting/`. Each is its own independent synthetic window (a real product can't be in three states over the same 10 weeks); `detect_and_correlate.py` runs all 3 rules against all 3 folders to prove each fires only its own rule.

All five files share the same `product` and `region` values so they join cleanly on `(product, region, week_start)`, with `dealer` as the extra key on the two dealer-level files.

## 1. sales.csv

| field | type | notes |
|---|---|---|
| product | string | "Vans Knu Skool" |
| region | string | "West Coast" |
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
| dealer | string | dealer name, one of 3 in the region |
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

## 5. customer.csv

| field | type | notes |
|---|---|---|
| product | string | |
| region | string | |
| week_start | date | |
| returns | int | weekly units returned |
| review_sentiment | float | -1 (negative) to +1 (positive), average of that week's reviews |

## Derived, not stored

- Week-over-week (WoW) % change per metric, plus an absolute-delta check for `review_sentiment` (a bounded -1..+1 score, where a ratio-style % change doesn't mean much) — computed, not generated (`detect_and_correlate.py`)
- Three rule outcomes per scenario — Opportunity, Product Problem, Demand Not Converting — each with its own confidence score and recommendation — computed output (`insight_<scenario>.json`)
