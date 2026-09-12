"""
POC1 change detection + correlation — Vans / VF DotIQ.

Loads the 5 synthetic datasets, computes week-over-week % change per metric,
applies the single Opportunity rule (Search up + Sales up + Vans inventory
down), and — if it fires — assembles one DotIQ Insight: headline, confidence,
supporting evidence, and a recommendation naming the specific dealer(s) whose
own stock is also running low.

Deterministic only. No LLM here — that's a POC4 concern.
"""
import json
import pandas as pd

# ---------- thresholds (the only "tuning knobs" in POC1) ----------
CUM_CHANGE_THRESHOLD = 0.15      # 15% cumulative change over the window counts as a real move
CONSISTENCY_MIN = 0.6            # at least 60% of week-over-week steps must agree with the trend
DEALER_LOW_UNITS = 40            # a dealer at/under this many units on hand is "running low"
DEALER_LOW_DROP = -0.30          # ...or one that has dropped at least 30% over the window


def load():
    sales = pd.read_csv("data/sales.csv", parse_dates=["week_start"])
    inventory = pd.read_csv("data/inventory.csv", parse_dates=["week_start"])
    dealer_inv = pd.read_csv("data/dealer_inventory.csv", parse_dates=["week_start"])
    website = pd.read_csv("data/website.csv", parse_dates=["week_start"])
    customer = pd.read_csv("data/customer.csv", parse_dates=["week_start"])
    return sales, inventory, dealer_inv, website, customer


def wow_pct(series):
    return series.pct_change()


def trend_stats(series):
    """Cumulative % change end-vs-start, and the share of WoW steps moving the same direction as the overall trend."""
    wow = wow_pct(series).dropna()
    cum_change = (series.iloc[-1] - series.iloc[0]) / series.iloc[0]
    direction = 1 if cum_change > 0 else -1
    agreeing = (wow * direction > 0).sum()
    consistency = agreeing / len(wow) if len(wow) else 0
    return cum_change, consistency, wow


def main():
    sales, inventory, dealer_inv, website, customer = load()

    merged = (
        website.merge(sales, on=["product", "region", "week_start"])
        .merge(inventory, on=["product", "region", "week_start"])
        .merge(customer, on=["product", "region", "week_start"])
        .sort_values("week_start")
        .reset_index(drop=True)
    )
    product = merged["product"].iloc[0]
    region = merged["region"].iloc[0]

    search_cum, search_cons, search_wow = trend_stats(merged["searches"])
    sales_cum, sales_cons, sales_wow = trend_stats(merged["units_sold"])
    inv_cum, inv_cons, inv_wow = trend_stats(merged["vans_inventory_units"])

    search_up = search_cum >= CUM_CHANGE_THRESHOLD and search_cons >= CONSISTENCY_MIN
    sales_up = sales_cum >= CUM_CHANGE_THRESHOLD and sales_cons >= CONSISTENCY_MIN
    inv_down = inv_cum <= -CUM_CHANGE_THRESHOLD and inv_cons >= CONSISTENCY_MIN

    triggered = bool(search_up and sales_up and inv_down)

    # ---------- confidence ----------
    consistency_avg = (search_cons + sales_cons + inv_cons) / 3
    magnitude_avg = sum(min(abs(x) / 0.30, 1.0) for x in (search_cum, sales_cum, inv_cum)) / 3
    confidence = round(100 * (0.5 * consistency_avg + 0.5 * magnitude_avg)) if triggered else 0

    # ---------- dealer recommendation ----------
    dealer_recs = []
    for dealer, grp in dealer_inv.sort_values("week_start").groupby("dealer"):
        cum, cons, wow = trend_stats(grp["dealer_inventory_units"])
        current = int(grp["dealer_inventory_units"].iloc[-1])
        flagged = current <= DEALER_LOW_UNITS or cum <= DEALER_LOW_DROP
        dealer_recs.append({
            "dealer": dealer,
            "current_units": current,
            "pct_change_over_window": round(cum * 100, 1),
            "flagged_low": bool(flagged),
        })
    dealer_recs.sort(key=lambda d: d["current_units"])
    flagged_dealers = [d for d in dealer_recs if d["flagged_low"]]

    week_start = merged["week_start"].min().date().isoformat()
    week_end = merged["week_start"].max().date().isoformat()

    headline = f"Revenue Opportunity — {product}, {region}"
    if triggered:
        lead_dealer = flagged_dealers[0] if flagged_dealers else None
        narrative = (
            f"Search is up {search_cum*100:.0f}% and sales are up {sales_cum*100:.0f}% over the last "
            f"{len(merged)} weeks in {region}, while Vans-side inventory has fallen {abs(inv_cum)*100:.0f}%. "
        )
        if lead_dealer:
            narrative += (
                f"{lead_dealer['dealer']} is also running low ({lead_dealer['current_units']} units on hand, "
                f"down {abs(lead_dealer['pct_change_over_window']):.0f}% over the window) — reach out about "
                f"reallocating or replenishing stock before this becomes a stockout."
            )
        else:
            narrative += "No dealer in the region is critically low yet — monitor before it becomes a stockout."
    else:
        narrative = "Signals did not line up for an Opportunity situation in this window."

    insight = {
        "product": product,
        "region": region,
        "week_start": week_start,
        "week_end": week_end,
        "situation_type": "Opportunity",
        "triggered": triggered,
        "confidence": confidence,
        "headline": headline,
        "narrative": narrative,
        "signals": {
            "search_cum_pct": round(search_cum * 100, 1),
            "sales_cum_pct": round(sales_cum * 100, 1),
            "vans_inventory_cum_pct": round(inv_cum * 100, 1),
            "search_consistency": round(search_cons, 2),
            "sales_consistency": round(sales_cons, 2),
            "inventory_consistency": round(inv_cons, 2),
        },
        "recommendation": {
            "action": "Flag for the stocker to contact the dealer(s) below about reallocating/replenishing stock."
                       if flagged_dealers else "No dealer action needed yet — monitor.",
            "dealers": dealer_recs,
        },
        "evidence_weekly": [
            {
                "week_start": row.week_start.date().isoformat(),
                "searches": int(row.searches),
                "views": int(row.views),
                "conversion_rate": round(float(row.conversion_rate), 4),
                "units_sold": int(row.units_sold),
                "vans_inventory_units": int(row.vans_inventory_units),
                "returns": int(row.returns),
                "review_sentiment": round(float(row.review_sentiment), 3),
            }
            for row in merged.itertuples()
        ],
        "evidence_dealer_weekly": [
            {
                "dealer": row.dealer,
                "week_start": row.week_start.date().isoformat(),
                "dealer_inventory_units": int(row.dealer_inventory_units),
            }
            for row in dealer_inv.sort_values(["dealer", "week_start"]).itertuples()
        ],
    }

    with open("insight.json", "w") as f:
        json.dump(insight, f, indent=2)

    print(f"Opportunity triggered: {triggered}  confidence={confidence}")
    print(f"search {search_cum*100:+.1f}% (consistency {search_cons:.0%})")
    print(f"sales  {sales_cum*100:+.1f}% (consistency {sales_cons:.0%})")
    print(f"vans_inventory {inv_cum*100:+.1f}% (consistency {inv_cons:.0%})")
    print("dealers:", dealer_recs)
    print("Wrote insight.json")


if __name__ == "__main__":
    main()
