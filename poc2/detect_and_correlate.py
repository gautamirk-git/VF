"""
POC2 change detection + correlation — Vans / VF DotIQ.

Same deterministic approach as POC1 (week-over-week % change, no LLM), now
generalized to three situation types instead of one:

  - Opportunity           Search up + Sales up + Vans Inventory down
  - Product Problem       Sales up + Returns up + Sentiment down
  - Demand Not Converting Search up + Conversion down

Runs all three rules against all three synthetic scenarios and asserts each
scenario fires exactly the rule it was tuned for — that's the actual POC2
proof: one engine, three rules, no cross-triggering.
"""
import json
import pandas as pd

CUM_CHANGE_THRESHOLD = 0.15   # 15% cumulative change counts as a real move
CONSISTENCY_MIN = 0.6         # >=60% of weekly steps must agree with the trend
SENTIMENT_DROP_THRESHOLD = -0.30  # absolute drop on the -1..+1 scale
DEALER_LOW_UNITS = 40
DEALER_LOW_DROP = -0.30

SCENARIOS = {
    "opportunity": "Opportunity",
    "product_problem": "Product Problem",
    "demand_not_converting": "Demand Not Converting",
}


def load(scenario):
    base = f"data/{scenario}"
    sales = pd.read_csv(f"{base}/sales.csv", parse_dates=["week_start"])
    inventory = pd.read_csv(f"{base}/inventory.csv", parse_dates=["week_start"])
    dealer_inv = pd.read_csv(f"{base}/dealer_inventory.csv", parse_dates=["week_start"])
    website = pd.read_csv(f"{base}/website.csv", parse_dates=["week_start"])
    customer = pd.read_csv(f"{base}/customer.csv", parse_dates=["week_start"])
    merged = (
        website.merge(sales, on=["product", "region", "week_start"])
        .merge(inventory, on=["product", "region", "week_start"])
        .merge(customer, on=["product", "region", "week_start"])
        .sort_values("week_start")
        .reset_index(drop=True)
    )
    return merged, dealer_inv


def pct_trend(series):
    """Cumulative % change end-vs-start, and share of WoW steps agreeing with that direction."""
    wow = series.pct_change().dropna()
    cum_change = (series.iloc[-1] - series.iloc[0]) / series.iloc[0]
    direction = 1 if cum_change > 0 else -1
    consistency = (wow * direction > 0).sum() / len(wow) if len(wow) else 0
    return cum_change, consistency


def abs_trend(series):
    """Absolute end-vs-start change (for bounded metrics like sentiment), and step consistency."""
    diffs = series.diff().dropna()
    delta = series.iloc[-1] - series.iloc[0]
    direction = 1 if delta > 0 else -1
    consistency = (diffs * direction > 0).sum() / len(diffs) if len(diffs) else 0
    return delta, consistency


def confidence_from(legs):
    """legs: list of (cum_or_delta, consistency, cap) -> 0-100 score."""
    consistency_avg = sum(c for _, c, _ in legs) / len(legs)
    magnitude_avg = sum(min(abs(v) / cap, 1.0) for v, _, cap in legs) / len(legs)
    return round(100 * (0.5 * consistency_avg + 0.5 * magnitude_avg))


def dealer_summary(dealer_inv):
    recs = []
    for dealer, grp in dealer_inv.sort_values("week_start").groupby("dealer"):
        cum, cons = pct_trend(grp["dealer_inventory_units"])
        current = int(grp["dealer_inventory_units"].iloc[-1])
        flagged = current <= DEALER_LOW_UNITS or cum <= DEALER_LOW_DROP
        recs.append({
            "dealer": dealer, "current_units": current,
            "pct_change_over_window": round(cum * 100, 1), "flagged_low": bool(flagged),
        })
    recs.sort(key=lambda d: d["current_units"])
    return recs


def check_opportunity(merged, dealer_inv):
    search_cum, search_cons = pct_trend(merged["searches"])
    sales_cum, sales_cons = pct_trend(merged["units_sold"])
    inv_cum, inv_cons = pct_trend(merged["vans_inventory_units"])

    search_up = search_cum >= CUM_CHANGE_THRESHOLD and search_cons >= CONSISTENCY_MIN
    sales_up = sales_cum >= CUM_CHANGE_THRESHOLD and sales_cons >= CONSISTENCY_MIN
    inv_down = inv_cum <= -CUM_CHANGE_THRESHOLD and inv_cons >= CONSISTENCY_MIN
    triggered = bool(search_up and sales_up and inv_down)

    dealers = dealer_summary(dealer_inv)
    flagged = [d for d in dealers if d["flagged_low"]]
    lead = flagged[0] if flagged else None

    narrative = (
        f"Search is up {search_cum*100:.0f}% and sales are up {sales_cum*100:.0f}% over the window, "
        f"while Vans-side inventory has fallen {abs(inv_cum)*100:.0f}%."
    )
    if lead:
        narrative += (f" {lead['dealer']} is also running low ({lead['current_units']} units on hand, "
                       f"down {abs(lead['pct_change_over_window']):.0f}% over the window) — reach out about "
                       f"reallocating or replenishing stock before this becomes a stockout.")

    return {
        "situation_type": "Opportunity",
        "triggered": triggered,
        "confidence": confidence_from([(search_cum, search_cons, 0.30), (sales_cum, sales_cons, 0.30), (inv_cum, inv_cons, 0.30)]) if triggered else 0,
        "narrative": narrative,
        "signals": {"search_cum_pct": round(search_cum*100, 1), "sales_cum_pct": round(sales_cum*100, 1),
                    "vans_inventory_cum_pct": round(inv_cum*100, 1)},
        "recommendation": {
            "action": "Flag for the stocker to contact the dealer(s) below about reallocating/replenishing stock." if flagged
                       else "No dealer action needed yet — monitor.",
            "dealers": dealers,
        },
    }


def check_product_problem(merged):
    sales_cum, sales_cons = pct_trend(merged["units_sold"])
    returns_cum, returns_cons = pct_trend(merged["returns"])
    sentiment_delta, sentiment_cons = abs_trend(merged["review_sentiment"])

    sales_up = sales_cum >= CUM_CHANGE_THRESHOLD and sales_cons >= CONSISTENCY_MIN
    returns_up = returns_cum >= CUM_CHANGE_THRESHOLD and returns_cons >= CONSISTENCY_MIN
    sentiment_down = sentiment_delta <= SENTIMENT_DROP_THRESHOLD
    triggered = bool(sales_up and returns_up and sentiment_down)

    narrative = (
        f"Sales are still up {sales_cum*100:.0f}%, but returns have risen {returns_cum*100:.0f}% and review "
        f"sentiment has dropped {abs(sentiment_delta):.2f} points over the window (ending at "
        f"{merged['review_sentiment'].iloc[-1]:+.2f}) — worth a quality check before it drags sales down too."
    )

    return {
        "situation_type": "Product Problem",
        "triggered": triggered,
        "confidence": confidence_from([(sales_cum, sales_cons, 0.30), (returns_cum, returns_cons, 0.30), (sentiment_delta, sentiment_cons, 0.6)]) if triggered else 0,
        "narrative": narrative,
        "signals": {"sales_cum_pct": round(sales_cum*100, 1), "returns_cum_pct": round(returns_cum*100, 1),
                    "sentiment_delta": round(sentiment_delta, 3)},
        "recommendation": {
            "action": "Flag for merchandising/quality review — check the product for a defect or sizing/fit issue before the next replenishment order."
                       if triggered else "No quality issue detected.",
        },
    }


def check_demand_not_converting(merged):
    search_cum, search_cons = pct_trend(merged["searches"])
    conv_cum, conv_cons = pct_trend(merged["conversion_rate"])

    search_up = search_cum >= CUM_CHANGE_THRESHOLD and search_cons >= CONSISTENCY_MIN
    conv_down = conv_cum <= -CUM_CHANGE_THRESHOLD and conv_cons >= CONSISTENCY_MIN
    triggered = bool(search_up and conv_down)

    narrative = (
        f"Search is up {search_cum*100:.0f}% but conversion has fallen {abs(conv_cum)*100:.0f}% over the window "
        f"— interest is climbing but isn't turning into purchases. Worth checking the product page, price, or "
        f"checkout flow for friction."
    )

    return {
        "situation_type": "Demand Not Converting",
        "triggered": triggered,
        "confidence": confidence_from([(search_cum, search_cons, 0.30), (conv_cum, conv_cons, 0.30)]) if triggered else 0,
        "narrative": narrative,
        "signals": {"search_cum_pct": round(search_cum*100, 1), "conversion_cum_pct": round(conv_cum*100, 1)},
        "recommendation": {
            "action": "Flag for the merchandising/UX team to review the product page, pricing, and checkout flow."
                       if triggered else "No conversion issue detected.",
        },
    }


def build_evidence(merged, dealer_inv):
    weekly = [{
        "week_start": row.week_start.date().isoformat(),
        "searches": int(row.searches), "views": int(row.views),
        "conversion_rate": round(float(row.conversion_rate), 4),
        "units_sold": int(row.units_sold), "vans_inventory_units": int(row.vans_inventory_units),
        "returns": int(row.returns), "review_sentiment": round(float(row.review_sentiment), 3),
    } for row in merged.itertuples()]
    dealer_weekly = [{
        "dealer": row.dealer, "week_start": row.week_start.date().isoformat(),
        "dealer_inventory_units": int(row.dealer_inventory_units),
    } for row in dealer_inv.sort_values(["dealer", "week_start"]).itertuples()]
    return weekly, dealer_weekly


def main():
    all_results = {}
    for scenario, expected_type in SCENARIOS.items():
        merged, dealer_inv = load(scenario)
        checks = {
            "Opportunity": check_opportunity(merged, dealer_inv),
            "Product Problem": check_product_problem(merged),
            "Demand Not Converting": check_demand_not_converting(merged),
        }
        fired = [t for t, c in checks.items() if c["triggered"]]
        status = "OK" if fired == [expected_type] else "MISMATCH"
        print(f"[{status}] scenario={scenario:<22} expected={expected_type:<22} fired={fired}")

        result = checks[expected_type]
        weekly, dealer_weekly = build_evidence(merged, dealer_inv)
        insight = {
            "scenario": scenario,
            "product": merged["product"].iloc[0],
            "region": merged["region"].iloc[0],
            "week_start": merged["week_start"].min().date().isoformat(),
            "week_end": merged["week_start"].max().date().isoformat(),
            "headline": f"{result['situation_type']} — {merged['product'].iloc[0]}, {merged['region'].iloc[0]}",
            **result,
            "all_rule_results": {t: {"triggered": c["triggered"], "confidence": c["confidence"]} for t, c in checks.items()},
            "evidence_weekly": weekly,
            "evidence_dealer_weekly": dealer_weekly,
        }
        with open(f"insight_{scenario}.json", "w") as f:
            json.dump(insight, f, indent=2)
        all_results[scenario] = insight

    print("\nWrote insight_<scenario>.json for:", ", ".join(SCENARIOS))


if __name__ == "__main__":
    main()
