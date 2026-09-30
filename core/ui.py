"""Simple visual building blocks (HTML cards, calendar strip, meters) for the Streamlit UI.
Neutral translucent backgrounds so everything reads in both light and dark themes.
Status colours always come with an icon + text label."""
from __future__ import annotations

import html
import math

import pandas as pd

GOOD, WARN, BAD, INFO = "#0ca30c", "#fab219", "#d03b3b", "#2a78d6"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"

VERDICT_STYLE = {
    "Strong signals": (GOOD, "▲", "Strong"),
    "Positive": (GOOD, "▲", "Positive"),
    "Mixed": (WARN, "●", "Mixed"),
    "Weak": (BAD, "▼", "Weak"),
}

CSS = """
<style>
.block-container{padding-top:1.2rem}
div[data-testid="stMetricValue"]{font-size:1.5rem}
.ir-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px;margin:6px 0 18px}
.ir-card{border:1px solid rgba(127,127,127,.25);border-radius:14px;padding:14px 16px;background:rgba(127,127,127,.05)}
.ir-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.ir-name{font-weight:700;font-size:1.05rem;line-height:1.25}
.ir-sub{font-size:.8rem;opacity:.7;margin-top:2px}
.ir-chip{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:3px 10px;font-size:.8rem;font-weight:600;white-space:nowrap}
.ir-pill{display:inline-block;border-radius:6px;padding:1px 7px;font-size:.72rem;font-weight:600;background:rgba(127,127,127,.15);margin-right:4px}
.ir-urgent{background:rgba(208,59,59,.14);color:inherit}
.ir-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:12px 0 10px}
.ir-stat .v{font-size:1.25rem;font-weight:700;line-height:1.1}
.ir-stat .l{font-size:.72rem;opacity:.7;margin-top:2px}
.ir-bars{margin-top:4px}
.ir-bar{display:grid;grid-template-columns:86px 1fr 52px;align-items:center;gap:6px;font-size:.76rem;margin:3px 0}
.ir-track{height:8px;border-radius:4px;background:rgba(127,127,127,.15);overflow:hidden}
.ir-fill{height:100%;border-radius:4px}
.ir-foot{display:flex;justify-content:space-between;font-size:.76rem;opacity:.75;margin-top:10px;border-top:1px solid rgba(127,127,127,.2);padding-top:8px}
.ir-week{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:6px 0 18px}
.ir-day{border:1px solid rgba(127,127,127,.25);border-radius:12px;padding:8px;min-height:120px;background:rgba(127,127,127,.04)}
.ir-day.today{border:2px solid #2a78d6}
.ir-dh{font-weight:700;font-size:.85rem;margin-bottom:6px}
.ir-dh span{opacity:.6;font-weight:500}
.ir-ev{font-size:.72rem;border-radius:6px;padding:3px 6px;margin:3px 0;line-height:1.2}
.ir-ev b{display:block;font-size:.66rem;text-transform:uppercase;letter-spacing:.03em;opacity:.8}
.ir-meter{height:14px;border-radius:7px;background:linear-gradient(90deg,rgba(208,59,59,.25) 0 40%,rgba(250,178,25,.25) 40% 55%,rgba(12,163,12,.25) 55% 100%);position:relative;margin:8px 0 4px}
.ir-needle{position:absolute;top:-5px;width:4px;height:24px;border-radius:2px;background:currentColor}
.ir-scale{display:flex;justify-content:space-between;font-size:.7rem;opacity:.65}
.ir-lights{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.ir-list{border-radius:12px;padding:10px 14px 4px;margin-bottom:10px}
.ir-list h4{margin:0 0 6px;font-size:1rem}
.ir-list li{margin-bottom:6px;font-size:.92rem}
.ir-big{font-size:2.6rem;font-weight:800;line-height:1}
.ir-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:4px 0 16px}
.ir-kpi{border-radius:12px;padding:12px 14px;background:rgba(127,127,127,.07)}
.ir-kpi .v{font-size:1.6rem;font-weight:800}
.ir-kpi .l{font-size:.78rem;opacity:.75}
@media (max-width:900px){.ir-week{grid-template-columns:repeat(2,1fr)}}
</style>
"""


def e(x) -> str:
    return html.escape(str(x))


def nn(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x)) and not pd.isna(x)


def chip(color: str, icon: str, text: str, strong: bool = True) -> str:
    return (f'<span class="ir-chip" style="background:{color}22;border:1px solid {color}66">'
            f'<span style="color:{color}">{icon}</span>{"<b>" if strong else ""}{e(text)}{"</b>" if strong else ""}</span>')


def verdict_chip(verdict: str, score: float | None = None) -> str:
    c, i, t = VERDICT_STYLE.get(verdict, (INFO, "●", verdict))
    return chip(c, i, f"{t}" + (f" · {score:.0f}" if score is not None else ""))


def call_chip(r) -> str:
    call = r.get("call")
    if not isinstance(call, str) or not call:
        v = r.get("verdict")
        return verdict_chip(v, r.get("score")) if isinstance(v, str) and v else ""
    c = r.get("call_color") or INFO
    return (f'<span class="ir-chip" style="background:{c}26;border:1px solid {c}88;font-size:.95rem;padding:5px 12px">'
            f'{r.get("call_icon", "")} <b>{e(call)}</b></span>')


def expert_chip(r) -> str:
    lbl, n = r.get("expert_label"), r.get("expert_n")
    if not isinstance(lbl, str) or not n or (isinstance(n, float) and math.isnan(n)):
        return ""
    col = GOOD if "Apply" in lbl else BAD if "Avoid" in lbl else WARN
    return f'<span class="ir-chip" style="background:{col}18">🧑‍💼 Experts: {e(lbl)} ({int(n)})</span>'


def call_panel(rec: dict, cons: dict) -> str:
    c = rec["color"]
    why = "".join(f"<li>{e(x)}</li>" for x in rec["why"])
    chg = "".join(f"<li>{e(x)}</li>" for x in rec["change"])
    return f"""
<div class="ir-card" style="border:2px solid {c};background:{c}12">
  <div style="font-size:.8rem;opacity:.7;text-transform:uppercase;letter-spacing:.05em">IPO Radar's call</div>
  <div style="font-size:2rem;font-weight:800;color:{c};line-height:1.2">{rec['icon']} {e(rec['call'])}</div>
  <div class="ir-sub">Combined score {rec['final']:.0f}/100 · confidence {e(rec['confidence'])} ·
     signal {rec['final'] - rec['adj_expert'] - rec['adj_mood']:.0f} {rec['adj_expert']:+.0f} experts {rec['adj_mood']:+.0f} market mood</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:8px">
    <div><b>Why</b><ul style="margin:.3rem 0 0 1rem;font-size:.9rem">{why}</ul></div>
    <div><b>What would change this</b><ul style="margin:.3rem 0 0 1rem;font-size:.9rem">{chg or '<li>—</li>'}</ul></div>
  </div>
</div>"""


def consensus_bar(cons: dict) -> str:
    n = cons["n"]
    if not n:
        return '<div class="ir-sub">No expert views counted yet.</div>'
    segs = [(cons["apply"], GOOD, "Apply"), (cons["neutral"], WARN, "Neutral"), (cons["avoid"], BAD, "Avoid")]
    bar = "".join(f'<div style="width:{k / n * 100:.1f}%;background:{c}" title="{lbl}: {k}"></div>' for k, c, lbl in segs if k)
    legend = " · ".join(f'<span style="color:{c}">■</span> {lbl} {k}' for k, c, lbl in segs)
    return (f'<div style="display:flex;height:16px;border-radius:8px;overflow:hidden;gap:2px;margin:6px 0">{bar}</div>'
            f'<div class="ir-sub" style="font-size:.85rem"><b>{e(cons["label"])}</b> from {n} source{"s" if n != 1 else ""} · {legend}</div>')


RATING_COLOR = {"Apply": GOOD, "Apply (long term)": GOOD, "Apply (listing gains)": AQUA, "Neutral": WARN, "Avoid": BAD}


def headline_list(news: pd.DataFrame) -> str:
    rows = []
    for _, r in news.iterrows():
        rt = r.get("rating")
        tag = (f'<span class="ir-chip" style="background:{RATING_COLOR.get(rt, INFO)}22;font-size:.72rem">{e(rt)}</span>'
               if isinstance(rt, str) else '<span class="ir-chip" style="background:rgba(127,127,127,.12);font-size:.72rem">info</span>')
        when = pd.Timestamp(r["ts"]).strftime("%d %b") if nn(r.get("ts")) else ""
        rows.append(f'<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px solid rgba(127,127,127,.15)">'
                    f'{tag}<div><a href="{e(r["link"])}" target="_blank" style="text-decoration:none">{e(r["title"])}</a>'
                    f'<div class="ir-sub">{e(r.get("source") or "")} {when}</div></div></div>')
    return "".join(rows)


def mood_banner(mood: dict) -> str:
    if mood.get("label", "Unknown") == "Unknown":
        return ""
    c = {"Hot": GOOD, "Healthy": GOOD, "Cooling": WARN, "Cold": BAD}[mood["label"]]
    icon = {"Hot": "🔥", "Healthy": "▲", "Cooling": "●", "Cold": "▼"}[mood["label"]]
    li = " · ".join(e(b) for b in mood["bullets"])
    return (f'<div class="ir-card" style="border-left:5px solid {c};padding:10px 14px;margin-bottom:14px">'
            f'<b>IPO market mood: <span style="color:{c}">{icon} {mood["label"]}</span></b>'
            f'<div class="ir-sub" style="font-size:.85rem;margin-top:3px">{li}</div></div>')


def days_left(row) -> str:
    today = pd.Timestamp.today().normalize()
    st = row.get("status")
    c, o = row.get("close"), row.get("open")
    if st == "Closing Today":
        return '<span class="ir-chip ir-urgent">⏰ Closes today</span>'
    if st == "Open" and nn(c):
        d = (pd.Timestamp(c) - today).days
        return f'<span class="ir-chip" style="background:rgba(42,120,214,.12)">⏳ {d} day{"s" if d != 1 else ""} left</span>'
    if st == "Upcoming" and nn(o):
        d = (pd.Timestamp(o) - today).days
        return f'<span class="ir-chip" style="background:rgba(127,127,127,.12)">🗓 Opens {pd.Timestamp(o):%d %b}' + (f" (in {d}d)" if d > 0 else "") + "</span>"
    return f'<span class="ir-chip" style="background:rgba(127,127,127,.12)">{e(st or "")}</span>'


def _bar(label: str, val, color: str, vmax_log: float = math.log10(200)) -> str:
    if not nn(val):
        return f'<div class="ir-bar"><span>{label}</span><div class="ir-track"></div><span style="opacity:.5">—</span></div>'
    w = 0 if val <= 0 else max(3, min(100, (math.log10(max(val, 0.01)) + 2) / (vmax_log + 2) * 100))
    return (f'<div class="ir-bar"><span>{label}</span><div class="ir-track"><div class="ir-fill" style="width:{w:.0f}%;background:{color}"></div></div>'
            f'<span style="text-align:right;font-weight:600">{val:,.2f}x</span></div>')


def fmt_inr(x) -> str:
    if not nn(x):
        return "—"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


def ipo_card(r) -> str:
    gp, g = r.get("gmp_pct"), r.get("gmp")
    gain_txt = f"{gp:+.1f}%" if nn(gp) else "—"
    gcol = GOOD if nn(gp) and gp >= 15 else (BAD if nn(gp) and gp <= 0 else "inherit")
    gpl = r.get("gain_per_lot")
    odds = r.get("retail_odds")
    tot = r.get("sub_total")
    seg = r.get("category") or ""
    lst = pd.Timestamp(r["listing"]).strftime("%d %b") if nn(r.get("listing")) else "—"
    if r.get("_sheet") is True:
        lo, hi = r.get("price_low"), r.get("price")
        band = f"₹{lo:g}–{hi:g}" if nn(lo) and nn(hi) else (f"₹{hi:g}" if nn(hi) else "—")
        first_stat = f'<div class="ir-stat"><div class="v">{band}</div><div class="l">Price band</div></div>'
    else:
        first_stat = f'<div class="ir-stat"><div class="v" style="color:{gcol}">{gain_txt}</div><div class="l">Expected listing gain (GMP)</div></div>'

    return f"""
<div class="ir-card">
  <div class="ir-top">
    <div><div class="ir-name">{e(r.get('name'))}</div>
      <div class="ir-sub"><span class="ir-pill">{e(seg)}</span>₹{r.get('price') if nn(r.get('price')) else '—'} / share · lot {int(r['lot']) if nn(r.get('lot')) else '—'}</div></div>
    {f'<span class="ir-sub" style="white-space:nowrap">score {r.get("final") or 0:.0f}</span>' if isinstance(r.get("call"), str) and r.get("call") else ""}
  </div>
  <div style="margin-top:8px">{call_chip(r)}</div>
  <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">{days_left(r)}{expert_chip(r)}</div>
  <div class="ir-stats">
    {first_stat}
    <div class="ir-stat"><div class="v">{f'{tot:,.1f}x' if nn(tot) else '—'}</div><div class="l">Times subscribed</div></div>
    <div class="ir-stat"><div class="v">{f'{odds*100:.0f}%' if nn(odds) else '—'}</div><div class="l">Your allotment chance</div></div>
  </div>
  <div class="ir-bars">
    {_bar('Institutions', r.get('sub_qib'), BLUE)}
    {_bar('HNIs', r.get('sub_nii'), ORANGE)}
    {_bar('Retail (you)', r.get('sub_retail'), AQUA)}
  </div>
  <div class="ir-foot"><span>Invest {fmt_inr(r.get('min_invest'))}{'' if r.get('_sheet') is True else ' · gain/lot ' + (fmt_inr(gpl) if nn(gpl) else '—')}</span><span>Lists {lst}</span></div>
</div>"""


def card_grid(df: pd.DataFrame) -> str:
    return '<div class="ir-grid">' + "".join(ipo_card(r) for _, r in df.iterrows()) + "</div>"


EVENT_STYLE = {"Opens": (BLUE, "Opens"), "Closes": (BAD, "Last day"), "Allotment": (YELLOW, "Allotment"), "Lists": (GOOD, "Listing")}


def week_strip(df: pd.DataFrame, days: int = 7) -> str:
    today = pd.Timestamp.today().normalize()
    cols = []
    for i in range(days):
        d = today + pd.Timedelta(days=i)
        evs = []
        for col, key in (("close", "Closes"), ("open", "Opens"), ("listing", "Lists"), ("allotment", "Allotment")):
            if col not in df:
                continue
            hit = df[pd.to_datetime(df[col], errors="coerce").dt.normalize() == d]
            hit = hit.sort_values("category")  # Mainboard before SME
            for _, r in hit.iterrows():
                c, lbl = EVENT_STYLE[key]
                tag = " (SME)" if r.get("category") == "SME" else ""
                evs.append(f'<div class="ir-ev" style="background:{c}1f;border-left:3px solid {c}"><b>{lbl}</b>{e(r["name"])}{tag}</div>')
        body = "".join(evs[:7]) + (f'<div class="ir-ev" style="opacity:.6">+{len(evs)-7} more</div>' if len(evs) > 7 else "")
        if not evs:
            body = '<div style="font-size:.75rem;opacity:.45">No events</div>'
        wd = "Today" if i == 0 else d.strftime("%a")
        cols.append(f'<div class="ir-day{" today" if i == 0 else ""}"><div class="ir-dh">{wd} <span>{d:%d %b}</span></div>{body}</div>')
    return '<div class="ir-week">' + "".join(cols) + "</div>"


def kpis(items: list[tuple[str, str, str | None]]) -> str:
    out = []
    for label, value, color in items:
        out.append(f'<div class="ir-kpi"><div class="v" style="color:{color or "inherit"}">{e(value)}</div><div class="l">{e(label)}</div></div>')
    return '<div class="ir-kpis">' + "".join(out) + "</div>"


def meter(score: float, verdict: str) -> str:
    c, i, t = VERDICT_STYLE.get(verdict, (INFO, "●", verdict))
    return f"""
<div style="display:flex;align-items:flex-end;gap:14px"><div class="ir-big" style="color:{c}">{score:.0f}</div>
<div style="padding-bottom:4px">{verdict_chip(verdict)}<div class="ir-sub">out of 100 · rule-based signal</div></div></div>
<div class="ir-meter"><div class="ir-needle" style="left:calc({max(0,min(100,score))}% - 2px)"></div></div>
<div class="ir-scale"><span>0 Weak</span><span>40 Mixed</span><span>55 Positive</span><span>100</span></div>"""


def lights(components: dict, missing: set | None = None) -> str:
    maxes = {"Grey market (GMP)": 35, "Institutional demand (QIB)": 20, "Overall demand": 10, "Fundamentals": 25, "Valuation (P/E)": 10}
    names = {"Grey market (GMP)": "Grey market", "Institutional demand (QIB)": "Institutions", "Overall demand": "Overall demand",
             "Fundamentals": "Fundamentals", "Valuation (P/E)": "Valuation"}
    out = []
    for k, v in components.items():
        if missing and k in missing:
            out.append(chip("#898781", "○", f"{names.get(k, k)}: no data yet"))
            continue
        f = (v or 0) / maxes.get(k, 1)
        c, i, t = (GOOD, "▲", "Good") if f >= 0.6 else (WARN, "●", "OK") if f >= 0.35 else (BAD, "▼", "Weak")
        out.append(chip(c, i, f"{names.get(k, k)}: {t}"))
    return '<div class="ir-lights">' + "".join(out) + "</div>"


def bullet_box(title: str, items: list[str], color: str, empty: str) -> str:
    li = "".join(f"<li>{e(x)}</li>" for x in items) or f"<li style='opacity:.6'>{e(empty)}</li>"
    return f'<div class="ir-list" style="background:{color}14;border:1px solid {color}55"><h4>{title}</h4><ul>{li}</ul></div>'


def result_card(r, rank_note: str = "") -> str:
    lg, nw = r.get("listing_gain_pct"), r.get("ltp_gain_pct")
    if not nn(nw):
        nw = lg if nn(lg) else 0.0
    if not nn(lg):
        lg = 0.0
    col = GOOD if nn(nw) and nw >= 0 else BAD
    icon = "▲" if nn(nw) and nw >= 0 else "▼"
    return (f'<div class="ir-card" style="padding:10px 14px"><div class="ir-top"><div><div class="ir-name" style="font-size:.95rem">{e(r["name"])}</div>'
            f'<div class="ir-sub"><span class="ir-pill">{e(r.get("category"))}</span>Listed {pd.Timestamp(r["listing_date"]):%d %b} · issue ₹{r.get("price"):g}</div></div>'
            f'<div style="text-align:right"><div style="font-size:1.3rem;font-weight:800;color:{col}">{icon} {nw:+.1f}%</div>'
            f'<div class="ir-sub">today · listed {lg:+.1f}%</div></div></div></div>')
