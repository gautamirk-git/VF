"""
POC2 synthetic data generator — Vans / VF DotIQ.

POC1 proved the Opportunity rule on one tuned scenario. POC2 proves the
correlation engine generalizes to two more rules — Product Problem and
Demand Not Converting — without touching the Opportunity logic.

Same product/region and same 5-dataset shape as POC1 (Vans Knu Skool, West
Coast, 3 dealers, 10 weeks). Three independent synthetic windows are
generated, one per situation type, each tuned so exactly one rule fires:

  - opportunity/             (re-tuned copy of the POC1 scenario)
  - product_problem/         Sales up + Returns up + Sentiment down
  - demand_not_converting/   Search up + Conversion down, sales flat

These are illustrative snapshots, not one continuous timeline — a real
product can't be in three states in the same 10 weeks, so each scenario is
its own self-contained window.
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta

PRODUCT = "Vans Knu Skool"
REGION = "West Coast"
N_WEEKS = 10
START = date(2026, 6, 1)
WEEKS = [START + timedelta(weeks=i) for i in range(N_WEEKS)]
DEALERS = ["PacSun - San Diego", "Zumiez - Santa Monica", "Tilly's - Sacramento"]


def trend(rng, start, end, n, noise_pct=0.03):
    """For count-scale metrics (searches, units, inventory) — noise scales with the range."""
    base = np.linspace(start, end, n)
    noise = rng.normal(0, noise_pct * (abs(end - start) / n + 1), n)
    return base + noise


def bounded_trend(rng, start, end, n, noise_std, lo, hi):
    """For small fixed-scale metrics (conversion_rate, sentiment) — an absolute noise
    std appropriate to the metric's own scale, clipped to a sane range. `trend()`'s
    range-relative formula breaks down here: a range of ~0.01 makes its noise term
    collapse to a flat +1, which is enormous next to a 0.05 or 0.4 baseline."""
    base = np.linspace(start, end, n)
    noise = rng.normal(0, noise_std, n)
    return np.clip(base + noise, lo, hi)


def write_scenario(name, seed, searches, sales, vans_inv, dealer_ranges, returns, sentiment):
    rng = np.random.default_rng(seed)
    out = f"data/{name}"

    s = trend(rng, *searches, N_WEEKS)
    v = s * rng.uniform(1.65, 1.75, N_WEEKS)

    website = pd.DataFrame({
        "product": PRODUCT, "region": REGION, "week_start": WEEKS,
        "searches": s.round().astype(int),
        "views": v.round().astype(int),
        "conversion_rate": bounded_trend(rng, *sales["conversion"], N_WEEKS, noise_std=0.004, lo=0.005, hi=0.30).round(4),
    })

    units_sold = trend(rng, *sales["units"], N_WEEKS, 0.03)
    sales_df = pd.DataFrame({
        "product": PRODUCT, "region": REGION, "week_start": WEEKS,
        "units_sold": units_sold.round().astype(int),
    })

    vans_inv_series = trend(rng, *vans_inv, N_WEEKS, 0.02)
    inventory_df = pd.DataFrame({
        "product": PRODUCT, "region": REGION, "week_start": WEEKS,
        "vans_inventory_units": vans_inv_series.round().astype(int),
    })

    rows = []
    for dealer, rng_vals in dealer_ranges.items():
        series = trend(rng, *rng_vals, N_WEEKS, 0.03)
        for wk, val in zip(WEEKS, series):
            rows.append({
                "product": PRODUCT, "region": REGION, "dealer": dealer,
                "week_start": wk, "dealer_inventory_units": max(0, round(val)),
            })
    dealer_df = pd.DataFrame(rows)

    returns_series = trend(rng, *returns, N_WEEKS, 0.10)
    sentiment_series = bounded_trend(rng, *sentiment, N_WEEKS, noise_std=0.035, lo=-1.0, hi=1.0)
    customer_df = pd.DataFrame({
        "product": PRODUCT, "region": REGION, "week_start": WEEKS,
        "returns": returns_series.round().clip(min=0).astype(int),
        "review_sentiment": sentiment_series.round(3),
    })

    import os
    os.makedirs(out, exist_ok=True)
    website.to_csv(f"{out}/website.csv", index=False)
    sales_df.to_csv(f"{out}/sales.csv", index=False)
    inventory_df.to_csv(f"{out}/inventory.csv", index=False)
    dealer_df.to_csv(f"{out}/dealer_inventory.csv", index=False)
    customer_df.to_csv(f"{out}/customer.csv", index=False)
    print(f"wrote {out}/")


# ---------- Scenario A: Opportunity (re-tuned copy of POC1) ----------
write_scenario(
    "opportunity", seed=42,
    searches=(1200, 1560),
    sales={"units": (140, 171), "conversion": (0.050, 0.061)},
    vans_inv=(1800, 1170),
    dealer_ranges={
        "PacSun - San Diego": (90, 28),
        "Zumiez - Santa Monica": (70, 63),
        "Tilly's - Sacramento": (60, 68),
    },
    returns=(9, 9),
    sentiment=(0.40, 0.38),
)

# ---------- Scenario B: Product Problem ----------
# Sales still climbing, but returns spike and sentiment turns negative —
# search/inventory stay flat so Opportunity's legs don't fire.
write_scenario(
    "product_problem", seed=7,
    searches=(1200, 1236),           # +3%, flat (not a driving signal)
    sales={"units": (140, 165), "conversion": (0.052, 0.053)},  # sales +18%
    vans_inv=(1800, 1746),           # -3%, healthy
    dealer_ranges={
        "PacSun - San Diego": (80, 76),
        "Zumiez - Santa Monica": (70, 68),
        "Tilly's - Sacramento": (65, 67),
    },
    returns=(8, 15),                 # +88%
    sentiment=(0.35, -0.20),         # sharp swing negative
)

# ---------- Scenario C: Demand Not Converting ----------
# Interest climbs (search/views up) but it isn't turning into sales —
# conversion falls while sales stay roughly flat.
write_scenario(
    "demand_not_converting", seed=19,
    searches=(1200, 1620),           # +35%
    sales={"units": (140, 146), "conversion": (0.055, 0.030)},  # conversion -45%
    vans_inv=(1800, 1764),           # -2%, healthy
    dealer_ranges={
        "PacSun - San Diego": (80, 77),
        "Zumiez - Santa Monica": (70, 69),
        "Tilly's - Sacramento": (65, 66),
    },
    returns=(9, 9),
    sentiment=(0.38, 0.36),
)
