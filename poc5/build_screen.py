"""
Builds the POC5 page — "Decisions to Take Today," the end-goal screen the
whole POC series was building toward.

Nothing new is computed here. This reads explained_insights.json, the exact
same output POC4 produced (same detection from POC1, same 3 rules from
POC2, same scale + ranking from POC3, same AI explanation layer from POC4).
POC5's only job is presentation: turn that into a screen a store operations
lead could actually open every morning — leading with the plain-language
decision and recommended action, with the full deterministic evidence one
click away instead of front and center.
"""
import json

EXPLAINED = json.load(open("explained_insights.json"))
TOP5 = EXPLAINED["top5"]
CUT = EXPLAINED["cut"]

W, H = 860, 280
PAD_L, PAD_R, PAD_T, PAD_B = 46, 46, 20, 30

CARD_COLOR = {"Opportunity": "var(--core)", "Product Problem": "var(--status-critical)", "Demand Not Converting": "var(--accent)"}
BADGE_BG = {"Opportunity": "var(--core-soft)", "Product Problem": "var(--status-critical-soft)", "Demand Not Converting": "var(--accent-soft)"}
CATEGORY_ICON = {"Opportunity": "▲", "Product Problem": "■", "Demand Not Converting": "●"}


def indexed_series(weekly, key):
    base = weekly[0][key]
    return [round(w[key] / base * 100, 1) for w in weekly]


def xy(i, val, n, y_min, y_max):
    x = PAD_L + ((W - PAD_L - PAD_R) * i / (n - 1))
    y = PAD_T + (H - PAD_T - PAD_B) * (1 - (val - y_min) / (y_max - y_min))
    return x, y


def indexed_chart(weekly, series_specs):
    n = len(weekly)
    all_vals = []
    series_idx = {}
    for label, key, color in series_specs:
        idx = indexed_series(weekly, key)
        series_idx[label] = idx
        all_vals += idx
    y_min, y_max = min(all_vals) - 8, max(all_vals) + 8
    week_labels = [w["week_start"] for w in weekly]

    paths, circles, end_labels = [], [], []
    for label, key, color in series_specs:
        idx = series_idx[label]
        pts = [xy(i, v, n, y_min, y_max) for i, v in enumerate(idx)]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        for i, (x, y) in enumerate(pts):
            circles.append(
                f'<circle class="pt" data-series="{label}" data-week="{week_labels[i]}" '
                f'data-value="{weekly[i][key]}" data-index="{idx[i]:.0f}" '
                f'cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>'
            )
        lx, ly = pts[-1]
        end_labels.append(f'<text x="{lx:.1f}" y="{ly-9:.1f}" text-anchor="end" font-family="var(--font-mono)" font-size="10.5" font-weight="600" fill="{color}">{label} {idx[-1]:.0f}</text>')

    base_y = xy(0, 100, n, y_min, y_max)[1]
    legend = "".join(f'<span><i style="background:{color}"></i>{label}</span>' for label, _, color in series_specs)

    svg = f'''
    <svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Indexed trend chart, week 1 = 100, for {', '.join(l for l,_,_ in series_specs)}.">
      <line x1="{PAD_L}" y1="{base_y:.1f}" x2="{W-PAD_R}" y2="{base_y:.1f}" stroke="var(--border)" stroke-width="1" stroke-dasharray="3,3"/>
      <text x="{W-PAD_R+4}" y="{base_y+3:.1f}" font-family="var(--font-mono)" font-size="9" fill="var(--muted)">100</text>
      {"".join(paths)}
      {"".join(circles)}
      {"".join(end_labels)}
      <text x="{PAD_L}" y="{H-6}" font-family="var(--font-mono)" font-size="9.5" fill="var(--muted)">{week_labels[0]}</text>
      <text x="{W-PAD_R}" y="{H-6}" text-anchor="end" font-family="var(--font-mono)" font-size="9.5" fill="var(--muted)">{week_labels[-1]}</text>
    </svg>
    <div class="legend">{legend}</div>
    '''
    return svg


def sentiment_chart(weekly):
    n = len(weekly)
    vals = [w["review_sentiment"] for w in weekly]
    y_min, y_max = -1.0, 1.0
    week_labels = [w["week_start"] for w in weekly]
    pts = [xy(i, v, n, y_min, y_max) for i, v in enumerate(vals)]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    zero_y = xy(0, 0, n, y_min, y_max)[1]

    cross_i = next((i for i, v in enumerate(vals) if v < 0), None)
    shade = ""
    cross_label = ""
    if cross_i is not None:
        cx = pts[cross_i][0]
        shade = f'<rect x="{cx:.1f}" y="{PAD_T}" width="{W-PAD_R-cx:.1f}" height="{zero_y-PAD_T:.1f}" fill="var(--status-critical-soft)"/>'
        cross_label = (f'<text x="{cx+6:.1f}" y="{PAD_T+14:.1f}" font-family="var(--font-body)" font-size="10.5" '
                        f'font-weight="600" fill="var(--status-critical)">turned negative — {week_labels[cross_i]}</text>')

    circles = "".join(
        f'<circle class="pt" data-series="Sentiment" data-week="{week_labels[i]}" data-value="{vals[i]:+.2f}" data-index="" '
        f'cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="var(--ink)"/>' for i, (x, y) in enumerate(pts)
    )
    lx, ly = pts[-1]
    return f'''
    <svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Review sentiment line, {vals[0]:+.2f} to {vals[-1]:+.2f}, crossing negative at {week_labels[cross_i] if cross_i is not None else 'no point'}.">
      {shade}
      <line x1="{PAD_L}" y1="{zero_y:.1f}" x2="{W-PAD_R}" y2="{zero_y:.1f}" stroke="var(--border-strong)" stroke-width="1" stroke-dasharray="3,3"/>
      <text x="{W-PAD_R+4}" y="{zero_y+3:.1f}" font-family="var(--font-mono)" font-size="9" fill="var(--muted)">0</text>
      <path d="{d}" fill="none" stroke="var(--ink)" stroke-width="2"/>
      {circles}
      <text x="{lx:.1f}" y="{ly-9:.1f}" text-anchor="end" font-family="var(--font-mono)" font-size="10.5" font-weight="600" fill="var(--ink)">{vals[-1]:+.2f}</text>
      {cross_label}
      <text x="{PAD_L}" y="{H-6}" font-family="var(--font-mono)" font-size="9.5" fill="var(--muted)">{week_labels[0]}</text>
      <text x="{W-PAD_R}" y="{H-6}" text-anchor="end" font-family="var(--font-mono)" font-size="9.5" fill="var(--muted)">{week_labels[-1]}</text>
    </svg>
    '''


def dealer_bar_chart(dealers):
    DW, DH = 860, 210
    d_pad_l, d_pad_r, d_pad_t, d_pad_b = 40, 40, 20, 44
    d_plot_w = DW - d_pad_l - d_pad_r
    d_plot_h = DH - d_pad_t - d_pad_b
    d_max = max(d["current_units"] for d in dealers) * 1.25
    n_dealers = len(dealers)
    bar_gap = 46
    bar_w = (d_plot_w - bar_gap * (n_dealers - 1)) / n_dealers
    bars = []
    for i, d in enumerate(sorted(dealers, key=lambda d: d["current_units"])):
        bx = d_pad_l + i * (bar_w + bar_gap)
        bh = d_plot_h * (d["current_units"] / d_max)
        by = d_pad_t + d_plot_h - bh
        color = "var(--status-critical)" if d["flagged_low"] else "var(--muted-fill)"
        low_label = (f'<text x="{bx+bar_w/2:.1f}" y="{by-26:.1f}" text-anchor="middle" font-family="var(--font-body)" '
                     f'font-size="10" font-weight="700" letter-spacing="0.06em" fill="var(--status-critical)">LOW STOCK</text>') if d["flagged_low"] else ""
        bars.append(f'''<g>
          <rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="4" fill="{color}"/>
          <text x="{bx+bar_w/2:.1f}" y="{by-10:.1f}" text-anchor="middle" font-family="var(--font-mono)" font-size="14" font-weight="600" fill="var(--ink)">{d['current_units']}</text>
          {low_label}
          <text x="{bx+bar_w/2:.1f}" y="{d_pad_t+d_plot_h+18:.1f}" text-anchor="middle" font-family="var(--font-body)" font-size="11" fill="var(--ink)" font-weight="600">{d['dealer']}</text>
          <text x="{bx+bar_w/2:.1f}" y="{d_pad_t+d_plot_h+33:.1f}" text-anchor="middle" font-family="var(--font-mono)" font-size="10" fill="var(--muted)">{d['pct_change_over_window']:+.0f}%</text>
        </g>''')
    aria = ", ".join(f'{d["dealer"]} at {d["current_units"]}' for d in dealers)
    return f'<svg class="chart" viewBox="0 0 {DW} {DH}" role="img" aria-label="Dealer inventory bars: {aria}.">{"".join(bars)}</svg>'


def evidence_table(weekly):
    rows = "\n".join(
        f'<tr><td>{w["week_start"]}</td><td>{w["searches"]:,}</td><td>{"Yes" if w.get("on_promo") else "—"}</td>'
        f'<td>{w["conversion_rate"]*100:.1f}%</td><td>{w["units_sold"]}</td><td>{w["vans_inventory_units"]:,}</td>'
        f'<td>{w["returns"]}</td><td>{w["review_sentiment"]:+.2f}</td></tr>'
        for w in weekly
    )
    return f'''<div class="table-wrap"><table>
      <thead><tr><th>Week</th><th>Searches</th><th>On promo</th><th>Conv. rate</th><th>Units sold</th><th>Vans inventory</th><th>Returns</th><th>Sentiment</th></tr></thead>
      <tbody>{rows}</tbody></table></div>'''


def evidence_chart_for(insight):
    situation_type = insight["situation_type"]
    weekly = insight["evidence_weekly"]
    if situation_type == "Opportunity":
        chart_html = indexed_chart(weekly, [
            ("Search", "searches", "var(--chart-blue)"),
            ("Sales", "units_sold", "var(--chart-orange)"),
            ("Vans Inv.", "vans_inventory_units", "var(--chart-aqua)"),
        ])
        chart_html += f'<div class="sub" style="margin-top:16px;">Dealer inventory — {insight["week_end"]}</div>' + dealer_bar_chart(insight["recommendation"]["dealers"])
    elif situation_type == "Product Problem":
        chart_html = indexed_chart(weekly, [
            ("Sales", "units_sold", "var(--chart-blue)"),
            ("Returns", "returns", "var(--chart-orange)"),
        ])
        chart_html += '<div class="sub" style="margin-top:16px;">Review sentiment (-1 to +1)</div>' + sentiment_chart(weekly)
    else:
        chart_html = indexed_chart(weekly, [
            ("Search", "searches", "var(--chart-blue)"),
            ("Conversion", "conversion_rate", "var(--chart-orange)"),
        ])
    return chart_html


def build_card(insight, rank):
    situation_type = insight["situation_type"]
    color = CARD_COLOR[situation_type]
    badge_bg = BADGE_BG[situation_type]
    icon = CATEGORY_ICON[situation_type]
    ai = insight["ai_explanation"]
    weekly = insight["evidence_weekly"]

    promo_line = ""
    if insight.get("promo_influenced"):
        promo_line = f'<p class="promo-inline">Note: {insight["promo_share_pct"]:.0f}% of this window ran on promo — confidence already reflects that ({insight["raw_confidence"]} → {insight["confidence"]}).</p>'

    ai_evidence = "".join(f"<li>{e}</li>" for e in ai["key_evidence"])
    rule_rows = "".join(
        f'<tr><td>{t}</td><td>{"fired" if r["triggered"] else "—"}</td><td>{r["confidence"] if r["triggered"] else "—"}</td></tr>'
        for t, r in insight["all_rule_results"].items()
    )
    card_id = f"card-{insight['scenario']}"

    return f'''
    <section class="decision" id="{card_id}" style="border-left:4px solid {color};">
      <div class="dhead">
        <span class="rank">#{rank}</span>
        <span class="badge" style="background:{badge_bg};color:{color};">{icon} {situation_type}</span>
        <span class="pill hot" style="color:{color};border-color:{color};">{insight['confidence']}% confidence</span>
        <span class="pill">{insight['product']} · {insight['region']}</span>
      </div>

      <p class="lead">{ai["narrative"]}</p>

      <div class="action-row">
        <div class="action-box" style="background:{badge_bg};border-color:{color};">
          <div class="action-label" style="color:{color};">Recommended action</div>
          <p>{insight['recommendation']['action']}</p>
          <p class="talk">&ldquo;{ai["suggested_talking_point"]}&rdquo;</p>
        </div>
        <label class="review-toggle">
          <input type="checkbox" data-review-id="{card_id}">
          <span>Mark reviewed</span>
        </label>
      </div>
      {promo_line}

      <details class="evidence">
        <summary>See the evidence — deterministic detection + AI explanation detail</summary>
        <div class="evidence-body">
          <div class="ev-cols">
            <div>
              <div class="sub2label">Key evidence cited</div>
              <ul class="ai-evidence">{ai_evidence}</ul>
              <div class="sub2label">Why this confidence score</div>
              <p class="rationale">{ai["confidence_rationale"]}</p>
            </div>
            <div>
              <div class="sub2label">Rule check (all 3 rules, this product/region)</div>
              <div class="table-wrap"><table>
                <thead><tr><th>Rule</th><th>Result</th><th>Confidence</th></tr></thead>
                <tbody>{rule_rows}</tbody>
              </table></div>
            </div>
          </div>
          <div class="chartwrap">{evidence_chart_for(insight)}</div>
          {evidence_table(weekly)}
        </div>
      </details>
    </section>
    '''


cards = "".join(build_card(insight, i + 1) for i, insight in enumerate(TOP5))

# ---- summary strip ----
from collections import Counter
PLURAL = {"Opportunity": "Opportunities", "Product Problem": "Product Problems", "Demand Not Converting": "Demand Not Converting situations"}
type_counts = Counter(i["situation_type"] for i in TOP5)
summary_bits = " · ".join(f"{n} {t if n == 1 else PLURAL[t]}" for t, n in type_counts.items())
latest_week = max(i["week_end"] for i in TOP5)

# ---- below-the-cut ----
cut_blocks = "".join(f'''
  <div class="cut-item">
    <div class="cut-item-head">
      <span class="badge sm" style="background:{BADGE_BG[c["situation_type"]]};color:{CARD_COLOR[c["situation_type"]]};">{CATEGORY_ICON[c["situation_type"]]} {c["situation_type"]}</span>
      <span class="pill">{c["product"]} · {c["region"]}</span>
      <span class="pill hot">{c["confidence"]}% confidence</span>
    </div>
    <p class="cut-narrative">{c["ai_explanation"]["narrative"]}</p>
  </div>''' for c in CUT)

cut_section = ""
if CUT:
    cut_section = f'''
    <section class="cutbox">
      <h3>Not in today's top 5</h3>
      <p class="sub2">{len(CUT)} more situation{"s" if len(CUT) != 1 else ""} detected today but ranked below the cutoff — still worth a glance.</p>
      {cut_blocks}
    </section>
    '''

MODE_LINE = (
    "live Anthropic API" if EXPLAINED["mode"] == "live_api" else "cached demo explanations (no API key in this environment)"
)

HTML = f"""<title>Decisions to Take Today</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
  :root{{
    --ink:#1B2430; --muted:#5B6472; --paper:#F4F6F9; --surface:#FFFFFF;
    --border:#D9DEE6; --border-strong:#C3CAD6;
    --core:#2F6690; --core-soft:#E4EEF4;
    --accent:#C87F1E; --accent-soft:#FBEBD4;
    --chart-blue:#2a78d6; --chart-orange:#eb6834; --chart-aqua:#1baf7a;
    --status-critical:#d03b3b; --status-critical-soft:#FBE7E7;
    --muted-fill:#C3CAD6;
    --ai:#6E4FC4; --ai-soft:#F0EBFB; --ai-border:#D9CCF0;
    --font-display:'Archivo','Arial Narrow',sans-serif;
    --font-body:'IBM Plex Sans',-apple-system,sans-serif;
    --font-mono:'IBM Plex Mono','SFMono-Regular',monospace;
  }}
  @media (prefers-color-scheme: dark){{
    :root:not([data-theme="light"]){{
      --ink:#E8EBF1; --muted:#98A1B2; --paper:#10141B; --surface:#171C25;
      --border:#2B323F; --border-strong:#3A4353;
      --core:#7FB2D6; --core-soft:#1C2E3B;
      --accent:#E8A94C; --accent-soft:#3A2C15;
      --chart-blue:#3987e5; --chart-orange:#d95926; --chart-aqua:#199e70;
      --status-critical:#e66767; --status-critical-soft:#3A1E1E;
      --muted-fill:#3A4353;
      --ai:#B49AEA; --ai-soft:#241C38; --ai-border:#4A3A6E;
    }}
  }}
  :root[data-theme="dark"]{{
    --ink:#E8EBF1; --muted:#98A1B2; --paper:#10141B; --surface:#171C25;
    --border:#2B323F; --border-strong:#3A4353;
    --core:#7FB2D6; --core-soft:#1C2E3B;
    --accent:#E8A94C; --accent-soft:#3A2C15;
    --chart-blue:#3987e5; --chart-orange:#d95926; --chart-aqua:#199e70;
    --status-critical:#e66767; --status-critical-soft:#3A1E1E;
    --muted-fill:#3A4353;
    --ai:#B49AEA; --ai-soft:#241C38; --ai-border:#4A3A6E;
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-body);padding:40px 20px 64px;}}
  .page{{max-width:940px;margin:0 auto;display:flex;flex-direction:column;gap:26px;}}
  header{{display:flex;flex-direction:column;gap:12px;}}
  .brandrow{{display:flex;align-items:center;gap:12px;}}
  .kicker{{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;letter-spacing:0.09em;color:var(--muted);}}
  h1{{font-family:var(--font-display);font-weight:700;font-size:clamp(26px,5vw,36px);margin:0;text-wrap:balance;}}
  .asof{{font-family:var(--font-mono);font-size:12.5px;color:var(--muted);}}
  .dek{{font-size:14.5px;line-height:1.6;color:var(--muted);max-width:74ch;margin:0;}}
  .summary-strip{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 18px;}}
  .summary-strip .big{{font-family:var(--font-display);font-weight:700;font-size:18px;color:var(--ink);}}
  .summary-strip .breakdown{{font-size:13px;color:var(--muted);}}
  .mode-line{{font-family:var(--font-mono);font-size:11px;color:var(--ai);}}

  .decision{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px clamp(14px,3vw,30px);}}
  .dhead{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px;}}
  .rank{{font-family:var(--font-display);font-weight:700;font-size:22px;color:var(--muted);min-width:36px;}}
  .badge{{font-family:var(--font-mono);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;padding:4px 10px;border-radius:5px;}}
  .badge.sm{{font-size:10px;padding:3px 8px;}}
  .pill{{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-mono);font-size:11px;color:var(--muted);border:1px solid var(--border-strong);border-radius:999px;padding:3px 10px;}}
  .pill.hot{{font-weight:600;}}
  .lead{{font-size:16px;line-height:1.65;color:var(--ink);max-width:80ch;margin:0 0 18px;}}

  .action-row{{display:flex;gap:14px;align-items:stretch;flex-wrap:wrap;margin-bottom:8px;}}
  .action-box{{flex:1 1 420px;border:1px solid;border-radius:10px;padding:14px 18px;}}
  .action-label{{font-family:var(--font-mono);font-size:10.5px;text-transform:uppercase;letter-spacing:0.07em;font-weight:700;margin-bottom:4px;}}
  .action-box p{{margin:2px 0 0;font-size:13.5px;line-height:1.55;color:var(--ink);}}
  .action-box .talk{{margin-top:8px;font-style:italic;color:var(--muted);}}
  .review-toggle{{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);cursor:pointer;padding:6px 4px;user-select:none;}}
  .review-toggle input{{width:16px;height:16px;accent-color:var(--core);cursor:pointer;}}
  .decision.reviewed{{opacity:0.55;}}
  .decision.reviewed .lead{{text-decoration:none;}}

  .promo-inline{{font-size:12px;color:var(--muted);margin:2px 0 10px;}}

  details.evidence{{margin-top:12px;border-top:1px solid var(--border);padding-top:4px;}}
  details.evidence summary{{cursor:pointer;font-family:var(--font-display);font-weight:700;font-size:13px;padding:8px 0;color:var(--muted);list-style:none;display:flex;align-items:center;gap:8px;}}
  details.evidence summary::-webkit-details-marker{{display:none;}}
  details.evidence summary::before{{content:"+";font-family:var(--font-mono);color:var(--core);width:16px;}}
  details.evidence[open] summary::before{{content:"–";}}
  .ev-cols{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:14px;}}
  @media (max-width:640px){{ .ev-cols{{grid-template-columns:1fr;}} }}
  .sub2label{{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;color:var(--ai);margin:10px 0 4px;}}
  .sub2label:first-child{{margin-top:0;}}
  .ai-evidence{{margin:0;padding-left:18px;font-size:12.5px;line-height:1.6;color:var(--ink);}}
  .rationale{{font-size:12.5px;line-height:1.6;color:var(--ink);margin:0;}}
  .chartwrap{{margin:10px 0 6px;}}
  svg.chart{{display:block;width:100%;height:auto;overflow:visible;}}
  .sub{{font-size:12px;color:var(--muted);font-weight:600;}}
  .legend{{display:flex;gap:16px;flex-wrap:wrap;margin-top:4px;}}
  .legend span{{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);}}
  .legend i{{width:9px;height:9px;border-radius:2px;display:inline-block;}}

  .table-wrap{{overflow-x:auto;border:1px solid var(--border);border-radius:8px;margin:10px 0;}}
  table{{border-collapse:collapse;width:100%;min-width:480px;font-size:12px;}}
  th,td{{text-align:left;padding:7px 11px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums;}}
  thead th{{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);font-weight:500;background:var(--paper);}}
  tbody tr:last-child td{{border-bottom:none;}}

  .cutbox{{background:var(--surface);border:1px dashed var(--border-strong);border-radius:10px;padding:20px clamp(12px,3vw,28px);}}
  .cutbox h3{{font-family:var(--font-display);font-weight:700;font-size:16px;margin:0 0 4px;}}
  .sub2{{font-size:13px;color:var(--muted);margin:2px 0 12px;}}
  .cut-item{{border-top:1px solid var(--border);padding-top:14px;margin-top:14px;}}
  .cut-item:first-of-type{{border-top:none;margin-top:6px;padding-top:0;}}
  .cut-item-head{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}}
  .cut-narrative{{font-size:13px;line-height:1.6;color:var(--muted);margin:8px 0 0;}}

  #tooltip{{position:absolute;pointer-events:none;background:var(--ink);color:var(--paper);font-family:var(--font-mono);font-size:11px;line-height:1.5;padding:7px 9px;border-radius:6px;opacity:0;transform:translate(-50%,-110%);transition:opacity .08s;white-space:nowrap;z-index:5;}}

  footer{{font-size:12px;color:var(--muted);border-top:1px solid var(--border);padding-top:16px;line-height:1.7;}}
  footer .poc-list{{margin:6px 0 0;padding-left:18px;}}
</style>

<div class="page">
  <header>
    <div class="brandrow">
      <svg width="28" height="28" viewBox="0 0 30 30" aria-hidden="true">
        <line x1="6" y1="23" x2="15" y2="7" stroke="var(--border-strong)" stroke-width="1.5"/>
        <line x1="15" y1="7" x2="24" y2="23" stroke="var(--border-strong)" stroke-width="1.5"/>
        <line x1="6" y1="23" x2="24" y2="23" stroke="var(--border-strong)" stroke-width="1.5"/>
        <circle cx="6" cy="23" r="3" fill="var(--core)"/>
        <circle cx="24" cy="23" r="3" fill="var(--core)"/>
        <circle cx="15" cy="7" r="3.5" fill="var(--accent)"/>
      </svg>
      <span class="kicker">DotIQ · POC5 · Vans / VF</span>
    </div>
    <h1>Decisions to Take Today</h1>
    <p class="asof">Data as of week ending {latest_week}</p>
    <p class="dek">Five ranked, AI-explained decisions from the same deterministic detection engine built across POC1–4 — nothing here is decided by the AI; it only writes the plain-language version of what the rules already found.</p>
    <div class="summary-strip">
      <span class="big">{len(TOP5)} decisions today</span>
      <span class="breakdown">{summary_bits}</span>
    </div>
    <div class="mode-line">✦ AI explanations: {MODE_LINE} · model {EXPLAINED["model"]}</div>
  </header>

  {cards}

  {cut_section}

  <footer>
    This screen is where POC1–5 come together, unchanged from each stage:
    <ol class="poc-list">
      <li>POC1 — deterministic detection: one rule (Opportunity), one product/region.</li>
      <li>POC2 — same engine generalized to three rules (Opportunity, Product Problem, Demand Not Converting), zero cross-triggering.</li>
      <li>POC3 — scaled to 3 products × 3 regions, added ranking (top 5 by confidence) and a promo-confidence discount.</li>
      <li>POC4 — added the AI explanation layer on top, without changing what's detected or how confident it is.</li>
      <li>POC5 (this screen) — the presentation layer only: same data, same rules, same ranking, same explanations, arranged for someone to act on in the morning.</li>
    </ol>
    Synthetic data throughout. "Mark reviewed" is a demo-only, browser-local toggle — it doesn't sync anywhere or change the underlying detection.
  </footer>
</div>

<div id="tooltip"></div>
<script>
  const tip = document.getElementById('tooltip');
  document.querySelectorAll('.pt').forEach(function(c){{
    c.addEventListener('mouseenter', function(){{
      const series = c.getAttribute('data-series');
      const week = c.getAttribute('data-week');
      const value = c.getAttribute('data-value');
      const index = c.getAttribute('data-index');
      tip.innerHTML = week + '<br>' + series + ': ' + value + (index ? ' (index ' + index + ')' : '');
      tip.style.opacity = 1;
      c.setAttribute('r', 5);
    }});
    c.addEventListener('mousemove', function(e){{
      const card = c.closest('.decision');
      const rect = card.getBoundingClientRect();
      tip.style.left = (e.clientX - rect.left + card.offsetLeft) + 'px';
      tip.style.top = (e.clientY - rect.top + card.offsetTop) + 'px';
    }});
    c.addEventListener('mouseleave', function(){{ tip.style.opacity = 0; c.setAttribute('r', 3.2); }});
  }});
  document.querySelectorAll('.decision').forEach(function(card){{ card.style.position='relative'; }});

  // Demo-only "mark reviewed" — per-browser convenience, not synced anywhere.
  (function(){{
    let store = {{}};
    try {{ store = JSON.parse(localStorage.getItem('dotiq_poc5_reviewed') || '{{}}'); }} catch (e) {{ store = {{}}; }}
    document.querySelectorAll('[data-review-id]').forEach(function(box){{
      const id = box.getAttribute('data-review-id');
      const card = document.getElementById(id);
      if (store[id]) {{ box.checked = true; card.classList.add('reviewed'); }}
      box.addEventListener('change', function(){{
        if (box.checked) {{ card.classList.add('reviewed'); store[id] = true; }}
        else {{ card.classList.remove('reviewed'); delete store[id]; }}
        try {{ localStorage.setItem('dotiq_poc5_reviewed', JSON.stringify(store)); }} catch (e) {{}}
      }});
    }});
  }})();
</script>
"""

with open("poc5_screen.html", "w") as f:
    f.write(HTML)
print("Wrote poc5_screen.html")
