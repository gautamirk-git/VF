# POC1 Data Dictionary

Scope: 1 product (Vans Knu Skool), 1 region (West Coast), 3 dealers in that region, 10 weeks of synthetic weekly data (2026-06-01 through 2026-08-03).

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

- Week-over-week (WoW) % change per metric — computed, not generated (`detect_and_correlate.py`)
- The Opportunity insight, confidence score, and recommendation — computed output (`insight.json`)
