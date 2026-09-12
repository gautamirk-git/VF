"""
POC3 synthetic data generator — Vans / VF DotIQ.

POC1 proved one rule on one product/region. POC2 proved the engine
generalizes to three rules. POC3 proves the engine scales to breadth: many
products and regions running through the same rules in a single pass, with
some situations firing, some not, and enough candidates that ranking (top 5)
actually means something. It also introduces the promo flag (flagged as a
POC3 gap in the planning doc) and proves the engine isn't fooled by a
promo-driven sales spike that otherwise looks exactly like Opportunity.

3 products x 3 regions = 9 possible cells. This POC uses 7 of them:

  1. Vans Knu Skool   / West Coast   -> Opportunity (strong, same as POC1/2)
  2. Vans Old Skool    / Northeast    -> Opportunity (weaker trend)
  3. Vans Sk8-Hi       / Midwest      -> Product Problem (strong, same as POC2)
  4. Vans Knu Skool    / Northeast    -> Product Problem (milder)
  5. Vans Old Skool    / West Coast   -> Demand Not Converting
  6. Vans Sk8-Hi       / West Coast   -> Opportunity shape, but promo-driven
  7. Vans Knu Skool    / Midwest      -> healthy baseline, nothing fires

Each region has its own 3 dealers, reused across every product sold in that
region (a dealer carries multiple Vans styles, same as in reality).
"""
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

N_WEEKS = 10
START = date(2026, 6, 1)
WEEKS = [START + timedelta(weeks=i) for i in range(N_WEEKS)]

DEALERS_BY_REGION = {
    "West Coast": ["PacSun - San Diego", "Zumiez - Santa Monica", "Tilly's - Sacramento"],
    "Northeast": ["Journeys - Boston", "Zumiez - New York", "Tilly's - Philadelphia"],
    "Midwest": ["Journeys - Chicago", "PacSun - Minneapolis", "Zumiez - Columbus"],
}


def trend(rng, start, end, n, noise_pct=0.03):
    """For count-scale metrics (searches, units, inventory) — noise scales with the range."""
    base = np.linspace(start, end, n)
    noise = rng.normal(0, noise_pct * (abs(end - start) / n + 1), n)
    return base + noise


def bounded_trend(rng, start, end, n, noise_std, lo, hi):
    """For small fixed-scale metrics (conversion_rate, sentiment) — an absolute noise
    std sized to the metric's own scale, clipped to a sane range."""
    base = np.linspace(start, end, n)
    noise = rng.normal(0, noise_std, n)
    return np.clip(base + noise, lo, hi)


def write_scenario(name, product, region, seed, searches, sales, vans_inv,
                    dealer_ranges, returns, sentiment, promo_weeks=None):
    """promo_weeks: set of week indices (0-based) where on_promo=1 for this
    product/region. None or empty = no promo activity in this scenario."""
    rng = np.random.default_rng(seed)
    out = f"data/{name}"
    promo_weeks = promo_weeks or set()

    s = trend(rng, *searches, N_WEEKS)
    v = s * rng.uniform(1.65, 1.75, N_WEEKS)

    website = pd.DataFrame({
        "product": product, "region": region, "week_start": WEEKS,
        "searches": s.round().astype(int),
        "views": v.round().astype(int),
        "conversion_rate": bounded_trend(rng, *sales["conversion"], N_WEEKS, noise_std=0.004, lo=0.005, hi=0.30).round(4),
        "on_promo": [1 if i in promo_weeks else 0 for i in range(N_WEEKS)],
    })

    units_sold = trend(rng, *sales["units"], N_WEEKS, 0.03)
    sales_df = pd.DataFrame({
        "product": product, "region": region, "week_start": WEEKS,
        "units_sold": units_sold.round().astype(int),
    })

    vans_inv_series = trend(rng, *vans_inv, N_WEEKS, 0.02)
    inventory_df = pd.DataFrame({
        "product": product, "region": region, "week_start": WEEKS,
        "vans_inventory_units": vans_inv_series.round().astype(int),
    })

    rows = []
    for dealer, rng_vals in dealer_ranges.items():
        series = trend(rng, *rng_vals, N_WEEKS, 0.03)
        for wk, val in zip(WEEKS, series):
            rows.append({
                "product": product, "region": region, "dealer": dealer,
                "week_start": wk, "dealer_inventory_units": max(0, round(val)),
            })
    dealer_df = pd.DataFrame(rows)

    returns_series = trend(rng, *returns, N_WEEKS, 0.10)
    sentiment_series = bounded_trend(rng, *sentiment, N_WEEKS, noise_std=0.035, lo=-1.0, hi=1.0)
    customer_df = pd.DataFrame({
        "product": product, "region": region, "week_start": WEEKS,
        "returns": returns_series.round().clip(min=0).astype(int),
        "review_sentiment": sentiment_series.round(3),
    })

    os.makedirs(out, exist_ok=True)
    website.to_csv(f"{out}/website.csv", index=False)
    sales_df.to_csv(f"{out}/sales.csv", index=False)
    inventory_df.to_csv(f"{out}/inventory.csv", index=False)
    dealer_df.to_csv(f"{out}/dealer_inventory.csv", index=False)
    customer_df.to_csv(f"{out}/customer.csv", index=False)
    print(f"wrote {out}/  ({product}, {region})")


# ---------- 1. Opportunity, strong (same tuning as POC1/POC2) ----------
write_scenario(
    "knu_skool_west_coast", "Vans Knu Skool", "West Coast", seed=42,
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

# ---------- 2. Opportunity, weaker trend ----------
write_scenario(
    "old_skool_northeast", "Vans Old Skool", "Northeast", seed=101,
    searches=(1100, 1300),            # +18%
    sales={"units": (130, 156), "conversion": (0.048, 0.053)},  # +20%
    vans_inv=(1600, 1300),            # -19%
    dealer_ranges={
        "Journeys - Boston": (75, 46),
        "Zumiez - New York": (65, 60),
        "Tilly's - Philadelphia": (55, 58),
    },
    returns=(8, 9),
    sentiment=(0.35, 0.34),
)

# ---------- 3. Product Problem, strong (same tuning as POC2) ----------
write_scenario(
    "sk8hi_midwest", "Vans Sk8-Hi", "Midwest", seed=7,
    searches=(1200, 1236),
    sales={"units": (140, 165), "conversion": (0.052, 0.053)},
    vans_inv=(1800, 1746),
    dealer_ranges={
        "Journeys - Chicago": (80, 76),
        "PacSun - Minneapolis": (70, 68),
        "Zumiez - Columbus": (65, 67),
    },
    returns=(8, 15),
    sentiment=(0.35, -0.20),
)

# ---------- 4. Product Problem, milder ----------
write_scenario(
    "knu_skool_northeast", "Vans Knu Skool", "Northeast", seed=55,
    searches=(1150, 1180),            # flat
    sales={"units": (135, 159), "conversion": (0.050, 0.051)},  # +18%
    vans_inv=(1700, 1660),            # flat, healthy
    dealer_ranges={
        "Journeys - Boston": (78, 75),
        "Zumiez - New York": (68, 67),
        "Tilly's - Philadelphia": (58, 60),
    },
    returns=(9, 16),                  # +78%
    sentiment=(0.35, -0.12),          # mild dip, not sharp (delta ~-0.47)
)

# ---------- 5. Demand Not Converting (same tuning as POC2) ----------
write_scenario(
    "old_skool_west_coast", "Vans Old Skool", "West Coast", seed=19,
    searches=(1200, 1620),
    sales={"units": (140, 146), "conversion": (0.055, 0.030)},
    vans_inv=(1800, 1764),
    dealer_ranges={
        "PacSun - San Diego": (80, 77),
        "Zumiez - Santa Monica": (70, 69),
        "Tilly's - Sacramento": (65, 66),
    },
    returns=(9, 9),
    sentiment=(0.38, 0.36),
)

# ---------- 6. Opportunity shape, but promo-driven (control case) ----------
# Same search/sales/inventory pattern as scenario 1 — would trigger Opportunity
# on the numbers alone — but on_promo=1 for 8 of the 10 weeks. The point of
# this scenario: prove the engine flags this as promo-influenced rather than
# reporting it as clean organic demand.
write_scenario(
    "sk8hi_west_coast", "Vans Sk8-Hi", "West Coast", seed=77,
    searches=(1200, 1550),
    sales={"units": (140, 170), "conversion": (0.050, 0.060)},
    vans_inv=(1800, 1180),
    dealer_ranges={
        "PacSun - San Diego": (85, 40),
        "Zumiez - Santa Monica": (70, 64),
        "Tilly's - Sacramento": (60, 66),
    },
    returns=(9, 9),
    sentiment=(0.39, 0.37),
    promo_weeks={2, 3, 4, 5, 6, 7, 8, 9},
)

# ---------- 7. Healthy baseline — nothing should fire ----------
write_scenario(
    "knu_skool_midwest", "Vans Knu Skool", "Midwest", seed=99,
    searches=(1150, 1170),            # flat
    sales={"units": (140, 143), "conversion": (0.052, 0.053)},  # flat
    vans_inv=(1700, 1690),            # flat, healthy
    dealer_ranges={
        "Journeys - Chicago": (75, 74),
        "PacSun - Minneapolis": (68, 69),
        "Zumiez - Columbus": (60, 61),
    },
    returns=(8, 8),
    sentiment=(0.36, 0.35),
)
