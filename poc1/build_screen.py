"""
Builds the POC1 "one screen" — a self-contained HTML page — from insight.json.
No hand-typed numbers: every figure on the page is read out of the file the
detection/correlation script produced.
"""
import json

with open("insight.json") as f:
    D = json.load(f)

weekly = D["evidence_weekly"]
dealer_weekly = D["evidence_dealer_weekly"]
dealers = D["recommendation"]["dealers"]
sig = D["signals"]

# ---------- indexed trend series (week1 = 100), so 3 different-scale metrics share one axis ----------
def indexed(key):
    base = weekly[0][key]
    return [round(w[key] / base * 100, 1) for w in weekly]

idx_search = indexed("searches")
idx_sales = indexed("units_sold")
idx_inv = indexed("vans_inventory_units")
week_labels = [w["week_start"] for w in weekly]

# ---------- SVG geometry for the trend chart ----------
W, H = 900, 340
PAD_L, PAD_R, PAD_T, PAD_B = 46, 46, 22, 34
plot_w = W - PAD_L - PAD_R
plot_h = H - PAD_T - PAD_B
n = len(weekly)
y_min, y_max = 55, 140  # index domain, fits all three series with headroom


def xy(i, val):
    x = PAD_L + (plot_w * i / (n - 1))
    y = PAD_T + plot_h * (1 - (val - y_min) / (y_max - y_min))
    return x, y


def path_d(series):
    pts = [xy(i, v) for i, v in enumerate(series)]
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), pts


search_d, search_pts = path_d(idx_search)
sales_d, sales_pts = path_d(idx_sales)
inv_d, inv_pts = path_d(idx_inv)

# baseline (index 100) gridline
base_y = xy(0, 100)[1]

# x-axis ticks: first, middle, last week
tick_idxs = [0, n // 2, n - 1]

circles_svg = []
for series_name, pts, raw_key, color_var in [
    ("Search", search_pts, "searches", "var(--chart-blue)"),
    ("Sales", sales_pts, "units_sold", "var(--chart-orange)"),
    ("Vans Inventory", inv_pts, "vans_inventory_units", "var(--chart-aqua)"),
]:
    for i, (x, y) in enumerate(pts):
        circles_svg.append(
            f'<circle class="pt" data-series="{series_name}" data-week="{week_labels[i]}" '
            f'data-value="{weekly[i][raw_key]}" data-index="{[idx_search,idx_sales,idx_inv][["Search","Sales","Vans Inventory"].index(series_name)][i]}" '
            f'cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{color_var}" />'
        )

# ---------- dealer bar chart ----------
DW, DH = 900, 230
d_pad_l, d_pad_r, d_pad_t, d_pad_b = 40, 40, 20, 44
d_plot_w = DW - d_pad_l - d_pad_r
d_plot_h = DH - d_pad_t - d_pad_b
d_max = max(d["current_units"] for d in dealers) * 1.25
n_dealers = len(dealers)
bar_gap = 46
bar_w = (d_plot_w - bar_gap * (n_dealers - 1)) / n_dealers

dealers_sorted = sorted(dealers, key=lambda d: d["current_units"])

bars_svg = []
for i, d in enumerate(dealers_sorted):
    bx = d_pad_l + i * (bar_w + bar_gap)
    bh = d_plot_h * (d["current_units"] / d_max)
    by = d_pad_t + d_plot_h - bh
    color = "var(--status-critical)" if d["flagged_low"] else "var(--muted-fill)"
    bars_svg.append(f'''
      <g>
        <rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="4" fill="{color}"/>
        <text x="{bx+bar_w/2:.1f}" y="{by-10:.1f}" text-anchor="middle" font-family="var(--font-mono)" font-size="15" font-weight="600" fill="var(--ink)">{d['current_units']}</text>
        {f'<text x="{bx+bar_w/2:.1f}" y="{by-26:.1f}" text-anchor="middle" font-family="var(--font-body)" font-size="10.5" font-weight="700" letter-spacing="0.06em" fill="var(--status-critical)">LOW STOCK</text>' if d['flagged_low'] else ''}
        <text x="{bx+bar_w/2:.1f}" y="{d_pad_t+d_plot_h+20:.1f}" text-anchor="middle" font-family="var(--font-body)" font-size="12" fill="var(--ink)" font-weight="600">{d['dealer']}</text>
        <text x="{bx+bar_w/2:.1f}" y="{d_pad_t+d_plot_h+36:.1f}" text-anchor="middle" font-family="var(--font-mono)" font-size="10.5" fill="var(--muted)">{d['pct_change_over_window']:+.0f}% over window</text>
      </g>''')

# ---------- evidence table rows ----------
evidence_rows = "\n".join(
    f'<tr><td>{w["week_start"]}</td><td>{w["searches"]:,}</td><td>{w["views"]:,}</td>'
    f'<td>{w["conversion_rate"]*100:.1f}%</td><td>{w["units_sold"]}</td>'
    f'<td>{w["vans_inventory_units"]:,}</td><td>{w["returns"]}</td><td>{w["review_sentiment"]:+.2f}</td></tr>'
    for w in weekly
)

dealer_table_rows = "\n".join(
    f'<tr><td>{d["dealer"]}</td><td>{d["current_units"]}</td><td>{d["pct_change_over_window"]:+.1f}%</td>'
    f'<td>{"Flagged — low stock" if d["flagged_low"] else "Healthy"}</td></tr>'
    for d in dealers
)

flagged = [d for d in dealers if d["flagged_low"]]
lead_dealer = flagged[0]["dealer"] if flagged else None
dealer_bar_aria = ", ".join(f'{d["dealer"]} at {d["current_units"]} units' for d in dealers_sorted)

HTML = f"""<title>Vans Knu Skool: West Coast Signal</title>
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
  .page{{max-width:940px;margin:0 auto;display:flex;flex-direction:column;gap:32px;}}

  header{{display:flex;flex-direction:column;gap:12px;}}
  .brandrow{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}}
  .kicker{{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;letter-spacing:0.09em;color:var(--muted);}}
  h1{{font-family:var(--font-display);font-weight:700;font-size:clamp(22px,4vw,29px);letter-spacing:-0.01em;margin:0;text-wrap:balance;}}
  .metarow{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}}
  .pill{{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-mono);font-size:11.5px;color:var(--muted);border:1px solid var(--border-strong);border-radius:999px;padding:4px 11px;}}
  .pill.hot{{color:var(--accent);border-color:var(--accent);}}
  .pill .dot{{width:6px;height:6px;border-radius:50%;background:currentColor;}}

  .narrative{{font-size:15px;line-height:1.65;color:var(--ink);max-width:74ch;}}

  .reco{{
    display:flex; gap:14px; align-items:flex-start;
    background:var(--accent-soft); border:1px solid var(--accent);
    border-radius:10px; padding:16px 18px;
  }}
  .reco .label{{font-family:var(--font-mono);font-size:10.5px;text-transform:uppercase;letter-spacing:0.08em;color:var(--accent);font-weight:600;}}
  .reco p{{margin:4px 0 0;font-size:14px;line-height:1.55;color:var(--ink);}}

  .card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px clamp(10px,3vw,26px) 18px;position:relative;}}
  .card h2{{font-family:var(--font-display);font-weight:700;font-size:16px;margin:0 0 4px;color:var(--ink);}}
  .card .sub{{font-size:12.5px;color:var(--muted);margin:0 0 10px;}}
  svg.chart{{display:block;width:100%;height:auto;overflow:visible;}}
  .legend{{display:flex;gap:18px;flex-wrap:wrap;margin-top:6px;}}
  .legend span{{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);}}
  .legend i{{width:10px;height:10px;border-radius:2px;display:inline-block;}}

  #tooltip{{
    position:absolute; pointer-events:none; background:var(--ink); color:var(--paper);
    font-family:var(--font-mono); font-size:11.5px; line-height:1.5; padding:8px 10px;
    border-radius:6px; opacity:0; transform:translate(-50%,-110%); transition:opacity .08s;
    white-space:nowrap; z-index:5;
  }}
  :root[data-theme="dark"] #tooltip, @media (prefers-color-scheme:dark){{ #tooltip{{}} }}

  details.why{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:4px 20px;}}
  details.why summary{{cursor:pointer;font-family:var(--font-display);font-weight:700;font-size:15px;padding:14px 0;color:var(--ink);list-style:none;display:flex;align-items:center;gap:8px;}}
  details.why summary::-webkit-details-marker{{display:none;}}
  details.why summary::before{{content:"+";font-family:var(--font-mono);color:var(--core);width:18px;}}
  details.why[open] summary::before{{content:"–";}}
  details.why .why-body{{padding:0 0 18px;}}
  .rule-box{{background:var(--paper);border:1px solid var(--border);border-radius:8px;padding:12px 14px;font-family:var(--font-mono);font-size:12px;line-height:1.7;color:var(--ink);margin-bottom:16px;}}
  .rule-box b{{color:var(--core);}}

  .table-wrap{{overflow-x:auto;border:1px solid var(--border);border-radius:8px;margin-bottom:16px;}}
  table{{border-collapse:collapse;width:100%;min-width:640px;font-size:12.5px;}}
  th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums;}}
  thead th{{font-family:var(--font-mono);font-size:10.5px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);font-weight:500;background:var(--paper);}}
  tbody tr:last-child td{{border-bottom:none;}}

  footer{{font-size:12px;color:var(--muted);border-top:1px solid var(--border);padding-top:16px;line-height:1.6;}}

  @media (max-width:640px){{ .legend{{gap:12px;}} }}
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
      <span class="kicker">DotIQ Insight · POC1</span>
    </div>
    <h1>{D['headline']}</h1>
    <div class="metarow">
      <span class="pill hot"><span class="dot"></span>{D['confidence']}% confidence</span>
      <span class="pill">{D['week_start']} → {D['week_end']} · 10 weeks</span>
      <span class="pill">Situation: {D['situation_type']}</span>
    </div>
    <p class="narrative">{D['narrative']}</p>
  </header>

  <div class="reco">
    <div>
      <div class="label">Recommended action</div>
      <p>{D['recommendation']['action']}</p>
    </div>
  </div>

  <div class="card">
    <h2>Signals — indexed to week 1 = 100</h2>
    <p class="sub">Search, sales, and Vans-side inventory over the 10-week window. Hover a point for the underlying weekly number.</p>
    <svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Line chart: search index rises to {idx_search[-1]:.0f}, sales index rises to {idx_sales[-1]:.0f}, and Vans inventory index falls to {idx_inv[-1]:.0f}, all indexed to 100 at week 1.">
      <line x1="{PAD_L}" y1="{base_y:.1f}" x2="{W-PAD_R}" y2="{base_y:.1f}" stroke="var(--border)" stroke-width="1" stroke-dasharray="3,3"/>
      <text x="{W-PAD_R+4}" y="{base_y+3:.1f}" font-family="var(--font-mono)" font-size="9.5" fill="var(--muted)">100</text>
      <path d="{search_d}" fill="none" stroke="var(--chart-blue)" stroke-width="2"/>
      <path d="{sales_d}" fill="none" stroke="var(--chart-orange)" stroke-width="2"/>
      <path d="{inv_d}" fill="none" stroke="var(--chart-aqua)" stroke-width="2"/>
      {"".join(circles_svg)}
      <text x="{search_pts[-1][0]:.1f}" y="{search_pts[-1][1]-10:.1f}" text-anchor="end" font-family="var(--font-mono)" font-size="11" font-weight="600" fill="var(--chart-blue)">Search {idx_search[-1]:.0f}</text>
      <text x="{sales_pts[-1][0]:.1f}" y="{sales_pts[-1][1]-10:.1f}" text-anchor="end" font-family="var(--font-mono)" font-size="11" font-weight="600" fill="var(--chart-orange)">Sales {idx_sales[-1]:.0f}</text>
      <text x="{inv_pts[-1][0]:.1f}" y="{inv_pts[-1][1]+16:.1f}" text-anchor="end" font-family="var(--font-mono)" font-size="11" font-weight="600" fill="var(--chart-aqua)">Vans Inv. {idx_inv[-1]:.0f}</text>
      <text x="{PAD_L}" y="{H-8}" font-family="var(--font-mono)" font-size="10" fill="var(--muted)">{week_labels[0]}</text>
      <text x="{W-PAD_R}" y="{H-8}" text-anchor="end" font-family="var(--font-mono)" font-size="10" fill="var(--muted)">{week_labels[-1]}</text>
    </svg>
    <div class="legend">
      <span><i style="background:var(--chart-blue)"></i>Search</span>
      <span><i style="background:var(--chart-orange)"></i>Sales</span>
      <span><i style="background:var(--chart-aqua)"></i>Vans Inventory</span>
    </div>
  </div>

  <div class="card">
    <h2>Dealer inventory — {D['week_end']}</h2>
    <p class="sub">Current on-hand units per dealer in {D['region']}. {lead_dealer or "No dealer"} is the one to call.</p>
    <svg class="chart" viewBox="0 0 {DW} {DH}" role="img" aria-label="Bar chart of current dealer inventory: {dealer_bar_aria}.">
      {"".join(bars_svg)}
    </svg>
  </div>

  <details class="why">
    <summary>Why? — underlying evidence</summary>
    <div class="why-body">
      <div class="rule-box">
        Rule: <b>Opportunity</b> = Search WoW↑ + Sales WoW↑ + Vans Inventory WoW↓, each ≥15% cumulative change over the window with ≥60% of weekly steps agreeing.<br/>
        Result: Search <b>{sig['search_cum_pct']:+.1f}%</b> ({sig['search_consistency']*100:.0f}% consistency) ·
        Sales <b>{sig['sales_cum_pct']:+.1f}%</b> ({sig['sales_consistency']*100:.0f}% consistency) ·
        Vans Inventory <b>{sig['vans_inventory_cum_pct']:+.1f}%</b> ({sig['inventory_consistency']*100:.0f}% consistency) →
        confidence <b>{D['confidence']}%</b>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Week</th><th>Searches</th><th>Views</th><th>Conv. rate</th><th>Units sold</th><th>Vans inventory</th><th>Returns</th><th>Sentiment</th></tr></thead>
          <tbody>{evidence_rows}</tbody>
        </table>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Dealer</th><th>Current units</th><th>Change over window</th><th>Status</th></tr></thead>
          <tbody>{dealer_table_rows}</tbody>
        </table>
      </div>
    </div>
  </details>

  <footer>
    POC1 — synthetic data, deterministic rules only, no LLM yet. Product: {D['product']} · Region: {D['region']} · Dealers tracked: {len(dealers)}.
  </footer>

</div>

<div id="tooltip"></div>
<script>
  const tip = document.getElementById('tooltip');
  document.querySelectorAll('.pt').forEach(function(c){{
    c.addEventListener('mouseenter', function(e){{
      const series = c.getAttribute('data-series');
      const week = c.getAttribute('data-week');
      const value = c.getAttribute('data-value');
      const index = parseFloat(c.getAttribute('data-index')).toFixed(0);
      tip.innerHTML = week + '<br>' + series + ': ' + Number(value).toLocaleString() + ' (index ' + index + ')';
      tip.style.opacity = 1;
      c.setAttribute('r', 5);
    }});
    c.addEventListener('mousemove', function(e){{
      const rect = c.closest('.card').getBoundingClientRect();
      tip.style.left = (e.clientX - rect.left + c.closest('.card').offsetLeft) + 'px';
      tip.style.top = (e.clientY - rect.top + c.closest('.card').offsetTop) + 'px';
    }});
    c.addEventListener('mouseleave', function(){{
      tip.style.opacity = 0;
      c.setAttribute('r', 3.4);
    }});
  }});
  document.querySelectorAll('.card').forEach(function(card){{ card.style.position='relative'; }});
</script>
"""

with open("poc1_screen.html", "w") as f:
    f.write(HTML)

print("Wrote poc1_screen.html")
