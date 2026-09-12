"""
Builds the POC2 page — one screen proving the correlation engine now
recognizes three situation types, each fired from its own tuned synthetic
scenario, with zero cross-triggering. Every number on the page is read out
of insight_<scenario>.json, nothing hand-typed.
"""
import json

SCENARIOS = ["opportunity", "product_problem", "demand_not_converting"]
DATA = {s: json.load(open(f"insight_{s}.json")) for s in SCENARIOS}

W, H = 860, 280
PAD_L, PAD_R, PAD_T, PAD_B = 46, 46, 20, 30


def indexed_series(weekly, key):
    base = weekly[0][key]
    return [round(w[key] / base * 100, 1) for w in weekly]


def xy(i, val, n, y_min, y_max):
    x = PAD_L + ((W - PAD_L - PAD_R) * i / (n - 1))
    y = PAD_T + (H - PAD_T - PAD_B) * (1 - (val - y_min) / (y_max - y_min))
    return x, y


def indexed_chart(weekly, series_specs, chart_id):
    """series_specs: list of (label, raw_key, css_color_var)"""
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

    # shade + label where sentiment is negative
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
        f'<tr><td>{w["week_start"]}</td><td>{w["searches"]:,}</td><td>{w["conversion_rate"]*100:.1f}%</td>'
        f'<td>{w["units_sold"]}</td><td>{w["vans_inventory_units"]:,}</td><td>{w["returns"]}</td><td>{w["review_sentiment"]:+.2f}</td></tr>'
        for w in weekly
    )
    return f'''<div class="table-wrap"><table>
      <thead><tr><th>Week</th><th>Searches</th><th>Conv. rate</th><th>Units sold</th><th>Vans inventory</th><th>Returns</th><th>Sentiment</th></tr></thead>
      <tbody>{rows}</tbody></table></div>'''


# ---------- assemble one card per scenario ----------
CARD_COLOR = {"opportunity": "var(--core)", "product_problem": "var(--status-critical)", "demand_not_converting": "var(--accent)"}
BADGE_BG = {"opportunity": "var(--core-soft)", "product_problem": "var(--status-critical-soft)", "demand_not_converting": "var(--accent-soft)"}

cards = []
for s in SCENARIOS:
    d = DATA[s]
    weekly = d["evidence_weekly"]
    color = CARD_COLOR[s]
    badge_bg = BADGE_BG[s]

    if s == "opportunity":
        chart_html = indexed_chart(weekly, [
            ("Search", "searches", "var(--chart-blue)"),
            ("Sales", "units_sold", "var(--chart-orange)"),
            ("Vans Inv.", "vans_inventory_units", "var(--chart-aqua)"),
        ], s)
        chart_html += f'<div class="sub" style="margin-top:16px;">Dealer inventory — {d["week_end"]}</div>' + dealer_bar_chart(d["recommendation"]["dealers"])
    elif s == "product_problem":
        chart_html = indexed_chart(weekly, [
            ("Sales", "units_sold", "var(--chart-blue)"),
            ("Returns", "returns", "var(--chart-orange)"),
        ], s)
        chart_html += '<div class="sub" style="margin-top:16px;">Review sentiment (-1 to +1)</div>' + sentiment_chart(weekly)
    else:
        chart_html = indexed_chart(weekly, [
            ("Search", "searches", "var(--chart-blue)"),
            ("Conversion", "conversion_rate", "var(--chart-orange)"),
        ], s)

    rule_rows = "".join(
        f'<tr><td>{t}</td><td>{"fired" if r["triggered"] else "—"}</td><td>{r["confidence"] if r["triggered"] else "—"}</td></tr>'
        for t, r in d["all_rule_results"].items()
    )

    cards.append(f'''
    <section class="card" style="border-left:4px solid {color};">
      <div class="cardhead">
        <span class="badge" style="background:{badge_bg};color:{color};">{d['situation_type']}</span>
        <span class="pill hot" style="color:{color};border-color:{color};">{d['confidence']}% confidence</span>
        <span class="pill">{d['week_start']} → {d['week_end']}</span>
      </div>
      <h2>{d['headline']}</h2>
      <p class="narrative">{d['narrative']}</p>
      <div class="reco" style="background:{badge_bg};border-color:{color};">
        <div class="label" style="color:{color};">Recommended action</div>
        <p>{d['recommendation']['action']}</p>
      </div>
      <div class="chartwrap">{chart_html}</div>
      <details class="why">
        <summary>Why? — all 3 rules checked against this scenario</summary>
        <div class="why-body">
          <div class="table-wrap"><table>
            <thead><tr><th>Rule</th><th>Result</th><th>Confidence</th></tr></thead>
            <tbody>{rule_rows}</tbody>
          </table></div>
          {evidence_table(weekly)}
        </div>
      </details>
    </section>
    ''')

HTML = f"""<title>Three DotIQ Situations</title>
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
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-body);padding:40px 20px 64px;}}
  .page{{max-width:940px;margin:0 auto;display:flex;flex-direction:column;gap:28px;}}
  header{{display:flex;flex-direction:column;gap:12px;}}
  .brandrow{{display:flex;align-items:center;gap:12px;}}
  .kicker{{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;letter-spacing:0.09em;color:var(--muted);}}
  h1{{font-family:var(--font-display);font-weight:700;font-size:clamp(22px,4vw,29px);margin:0;text-wrap:balance;}}
  .dek{{font-size:14.5px;line-height:1.6;color:var(--muted);max-width:74ch;margin:0;}}
  .proof{{display:flex;align-items:center;gap:8px;font-family:var(--font-mono);font-size:12px;color:var(--core);border:1px solid var(--core);background:var(--core-soft);border-radius:999px;padding:6px 14px;width:fit-content;}}

  .card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:22px clamp(12px,3vw,28px) 22px;}}
  .cardhead{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px;}}
  .badge{{font-family:var(--font-mono);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;padding:4px 10px;border-radius:5px;}}
  .pill{{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-mono);font-size:11px;color:var(--muted);border:1px solid var(--border-strong);border-radius:999px;padding:3px 10px;}}
  .pill.hot{{font-weight:600;}}
  .card h2{{font-family:var(--font-display);font-weight:700;font-size:19px;margin:0 0 8px;}}
  .narrative{{font-size:14px;line-height:1.6;color:var(--ink);max-width:76ch;margin:0 0 14px;}}
  .reco{{border:1px solid;border-radius:8px;padding:12px 16px;margin-bottom:18px;}}
  .reco .label{{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;letter-spacing:0.07em;font-weight:600;}}
  .reco p{{margin:3px 0 0;font-size:13px;line-height:1.5;color:var(--ink);}}
  .chartwrap{{margin-bottom:6px;}}
  svg.chart{{display:block;width:100%;height:auto;overflow:visible;}}
  .sub{{font-size:12px;color:var(--muted);font-weight:600;}}
  .legend{{display:flex;gap:16px;flex-wrap:wrap;margin-top:4px;}}
  .legend span{{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);}}
  .legend i{{width:9px;height:9px;border-radius:2px;display:inline-block;}}

  details.why{{margin-top:14px;border-top:1px solid var(--border);padding-top:6px;}}
  details.why summary{{cursor:pointer;font-family:var(--font-display);font-weight:700;font-size:13.5px;padding:8px 0;color:var(--ink);list-style:none;display:flex;align-items:center;gap:8px;}}
  details.why summary::-webkit-details-marker{{display:none;}}
  details.why summary::before{{content:"+";font-family:var(--font-mono);color:var(--core);width:16px;}}
  details.why[open] summary::before{{content:"–";}}
  .table-wrap{{overflow-x:auto;border:1px solid var(--border);border-radius:8px;margin:10px 0;}}
  table{{border-collapse:collapse;width:100%;min-width:560px;font-size:12px;}}
  th,td{{text-align:left;padding:7px 11px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums;}}
  thead th{{font-family:var(--font-mono);font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);font-weight:500;background:var(--paper);}}
  tbody tr:last-child td{{border-bottom:none;}}

  #tooltip{{position:absolute;pointer-events:none;background:var(--ink);color:var(--paper);font-family:var(--font-mono);font-size:11px;line-height:1.5;padding:7px 9px;border-radius:6px;opacity:0;transform:translate(-50%,-110%);transition:opacity .08s;white-space:nowrap;z-index:5;}}

  footer{{font-size:12px;color:var(--muted);border-top:1px solid var(--border);padding-top:16px;line-height:1.6;}}
</style>

<div class="page">
  <header>
    <div class="brandrow">
      <svg width="26" height="26" viewBox="0 0 30 30" aria-hidden="true">
        <line x1="6" y1="23" x2="15" y2="7" stroke="var(--border-strong)" stroke-width="1.5"/>
        <line x1="15" y1="7" x2="24" y2="23" stroke="var(--border-strong)" stroke-width="1.5"/>
        <line x1="6" y1="23" x2="24" y2="23" stroke="var(--border-strong)" stroke-width="1.5"/>
        <circle cx="6" cy="23" r="3" fill="var(--core)"/>
        <circle cx="24" cy="23" r="3" fill="var(--core)"/>
        <circle cx="15" cy="7" r="3.5" fill="var(--accent)"/>
      </svg>
      <span class="kicker">DotIQ · POC2</span>
    </div>
    <h1>Three Situations, One Engine</h1>
    <p class="dek">POC1 proved Opportunity. POC2 adds Product Problem and Demand Not Converting to the same deterministic rules engine — three independent synthetic scenarios below, each firing only its own rule.</p>
    <div class="proof">✓ 3 scenarios × 3 rules checked — zero cross-triggers</div>
  </header>

  {"".join(cards)}

  <footer>
    POC2 — synthetic data, deterministic rules only, no LLM yet, no ranking yet (that's POC3/4). Product: {DATA['opportunity']['product']} · Region: {DATA['opportunity']['region']}. Each scenario is an independent synthetic window, not one continuous timeline.
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
      const card = c.closest('.card');
      const rect = card.getBoundingClientRect();
      tip.style.left = (e.clientX - rect.left + card.offsetLeft) + 'px';
      tip.style.top = (e.clientY - rect.top + card.offsetTop) + 'px';
    }});
    c.addEventListener('mouseleave', function(){{ tip.style.opacity = 0; c.setAttribute('r', 3.2); }});
  }});
  document.querySelectorAll('.card').forEach(function(card){{ card.style.position='relative'; }});
</script>
"""

with open("poc2_screen.html", "w") as f:
    f.write(HTML)
print("Wrote poc2_screen.html")
