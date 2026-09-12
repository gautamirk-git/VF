"""
POC1 synthetic data generator — Vans / VF DotIQ.

Produces 5 CSVs under ./data for 1 product, 1 region, 3 dealers, 10 weeks,
tuned so the Opportunity story is visible: search + sales climbing while
Vans-side inventory falls, and one dealer (PacSun - San Diego) also running
low so the recommendation has a specific dealer to point at.
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(42)

PRODUCT = "Vans Knu Skool"
REGION = "West Coast"
N_WEEKS = 10
START = date(2026, 6, 1)  # Monday
weeks = [START + timedelta(weeks=i) for i in range(N_WEEKS)]

DEALERS = ["PacSun - San Diego", "Zumiez - Santa Monica", "Tilly's - Sacramento"]


def trend(start, end, n, noise_pct=0.03):
    base = np.linspace(start, end, n)
    noise = rng.normal(0, noise_pct * (abs(end - start) / n + 1), n)
    return base + noise


# ---------- 1. website.csv ----------
searches = trend(1200, 1560, N_WEEKS, 0.02)          # +30% over the window
views = searches * rng.uniform(1.65, 1.75, N_WEEKS)   # ~1.7x searches
conversion = trend(0.050, 0.061, N_WEEKS, 0.03)       # +22%

website = pd.DataFrame({
    "product": PRODUCT, "region": REGION, "week_start": weeks,
    "searches": searches.round().astype(int),
    "views": views.round().astype(int),
    "conversion_rate": conversion.round(4),
})

# ---------- 2. sales.csv ----------
units_sold = trend(140, 171, N_WEEKS, 0.03)  # +22%
sales = pd.DataFrame({
    "product": PRODUCT, "region": REGION, "week_start": weeks,
    "units_sold": units_sold.round().astype(int),
})

# ---------- 3. inventory.csv (Vans-side) ----------
vans_inv = trend(1800, 1170, N_WEEKS, 0.02)  # -35%
inventory = pd.DataFrame({
    "product": PRODUCT, "region": REGION, "week_start": weeks,
    "vans_inventory_units": vans_inv.round().astype(int),
})

# ---------- 4. dealer_inventory.csv ----------
dealer_trends = {
    "PacSun - San Diego": trend(90, 28, N_WEEKS, 0.04),     # -69%, the one to flag
    "Zumiez - Santa Monica": trend(70, 63, N_WEEKS, 0.03),  # mild decline, still healthy
    "Tilly's - Sacramento": trend(60, 68, N_WEEKS, 0.03),   # stable/slightly up
}
rows = []
for dealer, series in dealer_trends.items():
    for wk, val in zip(weeks, series):
        rows.append({
            "product": PRODUCT, "region": REGION, "dealer": dealer,
            "week_start": wk, "dealer_inventory_units": max(0, round(val)),
        })
dealer_inventory = pd.DataFrame(rows)

# ---------- 5. customer.csv ----------
returns = rng.normal(9, 1.3, N_WEEKS).round().clip(min=0).astype(int)
sentiment = rng.normal(0.40, 0.04, N_WEEKS).round(3)
customer = pd.DataFrame({
    "product": PRODUCT, "region": REGION, "week_start": weeks,
    "returns": returns, "review_sentiment": sentiment,
})

# ---------- write ----------
website.to_csv("data/website.csv", index=False)
sales.to_csv("data/sales.csv", index=False)
inventory.to_csv("data/inventory.csv", index=False)
dealer_inventory.to_csv("data/dealer_inventory.csv", index=False)
customer.to_csv("data/customer.csv", index=False)

print("Synthetic data written to ./data/")
print(f"  product={PRODUCT!r}  region={REGION!r}  weeks={weeks[0]}..{weeks[-1]}")
print(f"  dealers={DEALERS}")
