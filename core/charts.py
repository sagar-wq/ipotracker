"""Plotly chart builders. Colors follow a validated, colour-blind-safe palette:
categorical slots in fixed order, a blue<->red diverging pair for gains/losses,
and reserved status colours (always shown with an icon + label)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEGMENT = {"Mainboard": SERIES[0], "SME": SERIES[1]}
SUBCAT = {"QIB": SERIES[0], "sNII (₹2–10L)": SERIES[1], "bNII (>₹10L)": SERIES[2], "Retail": SERIES[3],
          "NII (total)": SERIES[1], "Total": "#52514e"}
POS, NEG, NEUTRAL = "#2a78d6", "#e34948", "#c3c2b7"
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
MUTED, GRID = "#898781", "rgba(137,135,129,0.25)"


def _base(fig: go.Figure, title: str | None = None, h: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xref="paper", y=0.985, yref="container", yanchor="top", font=dict(size=15)) if title else None,
        height=h, margin=dict(l=8, r=8, t=48 if title else 16, b=64 if legend else 8),
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=12),
        hovermode="closest", showlegend=legend,
        legend=dict(orientation="h", yref="container", yanchor="bottom", y=0.005, xanchor="left", x=0, title=None),
        bargap=0.25, bargroupgap=0.08,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor="rgba(137,135,129,0.6)", tickfont=dict(color=MUTED))
    return fig


def signed_colors(vals) -> list[str]:
    return [NEUTRAL if (v is None or pd.isna(v)) else (POS if v >= 0 else NEG) for v in vals]


# ---------------------------------------------------------------------------
def subscription_bars(row: pd.Series, title: str = "Subscription by investor category (times)") -> go.Figure | None:
    cats = [("QIB", "sub_qib"), ("sNII (₹2–10L)", "sub_snii"), ("bNII (>₹10L)", "sub_bnii"), ("Retail", "sub_retail"), ("Total", "sub_total")]
    pts = [(lbl, row.get(k)) for lbl, k in cats if row.get(k) is not None and not pd.isna(row.get(k))]
    if not pts:
        return None
    fig = go.Figure(go.Bar(
        x=[p[0] for p in pts], y=[p[1] for p in pts], marker_color=[SUBCAT[p[0]] for p in pts],
        text=[f"{p[1]:,.2f}x" for p in pts], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y:,.2f}x<extra></extra>", marker=dict(cornerradius=4),
    ))
    fig.add_hline(y=1, line_dash="dot", line_color=MUTED)  # 1x = fully subscribed
    return _base(fig, title + " · dotted line = 1x", h=340, legend=False)


def subscription_compare(df: pd.DataFrame) -> go.Figure | None:
    d = df.dropna(subset=["sub_total"]).copy()
    if d.empty:
        return None
    d = d.sort_values("sub_total", ascending=True).tail(15)
    fig = go.Figure()
    for lbl, k in (("QIB", "sub_qib"), ("NII (total)", "sub_nii"), ("Retail", "sub_retail")):
        fig.add_bar(y=d["name"], x=d[k], name=lbl, orientation="h", marker_color=SUBCAT[lbl],
                    marker=dict(cornerradius=3), hovertemplate=f"{lbl}: %{{x:,.2f}}x<extra>%{{y}}</extra>")
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="log", title="times subscribed (log scale)", gridcolor=GRID, showgrid=True)
    return _base(fig, "Who is bidding? QIB vs NII vs Retail", h=max(360, 34 * len(d) + 80))


def gmp_ranked(df: pd.DataFrame) -> go.Figure | None:
    d = df.dropna(subset=["gmp_pct"]).sort_values("gmp_pct")
    if d.empty:
        return None
    fig = go.Figure(go.Bar(
        y=d["name"], x=d["gmp_pct"], orientation="h", marker_color=signed_colors(d["gmp_pct"]),
        marker=dict(cornerradius=3), customdata=d[["gmp", "price", "status"]].values,
        text=[f"{v:.1f}%" for v in d["gmp_pct"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>GMP ₹%{customdata[0]} on ₹%{customdata[1]}<br>%{x:.1f}% · %{customdata[2]}<extra></extra>",
    ))
    fig.update_xaxes(title="GMP as % of issue price", showgrid=True, gridcolor=GRID)
    return _base(fig, "Grey-market premium (implied listing gain)", h=max(320, 28 * len(d) + 80), legend=False)


def gmp_trend(hist: pd.DataFrame, price: float | None, title="GMP trend") -> go.Figure | None:
    if hist is None or hist.empty:
        return None
    fig = go.Figure(go.Scatter(
        x=hist["ts"], y=hist["gmp"], mode="lines+markers", line=dict(color=SERIES[0], width=2, shape="hv"),
        marker=dict(size=8, color=SERIES[0], line=dict(color="white", width=2)), name="GMP",
        hovertemplate="%{x|%d %b %H:%M}<br>GMP ₹%{y}" + (f" ({{customdata:.1f}}%)" if price else "") + "<extra></extra>",
        customdata=(hist["gmp"] / price * 100) if price else None,
    ))
    fig.update_yaxes(title="GMP (₹ per share)")
    fig.update_layout(hovermode="x unified")
    return _base(fig, title, h=320, legend=False)


def timeline(df: pd.DataFrame) -> go.Figure | None:
    d = df.dropna(subset=["open", "close"]).copy()
    if d.empty:
        return None
    d = d.sort_values(["open", "close", "name"])
    fig = go.Figure()
    for seg, g in d.groupby("category"):
        fig.add_bar(
            y=g["name"], x=(g["close"] - g["open"]).dt.days.clip(lower=0) * 86400000 + 86400000, base=g["open"],
            orientation="h", name=f"{seg} bidding window", marker_color=SEGMENT.get(seg, SERIES[2]),
            marker=dict(cornerradius=3),
            customdata=g[["status", "allotment", "listing"]].astype(str).values,
            hovertemplate="<b>%{y}</b><br>Bidding %{base|%d %b} → close<br>Status: %{customdata[0]}<br>Allotment %{customdata[1]}<br>Listing %{customdata[2]}<extra></extra>",
        )
    lst = d.dropna(subset=["listing"])
    fig.add_scatter(y=lst["name"], x=lst["listing"], mode="markers", name="Listing date",
                    marker=dict(symbol="diamond", size=10, color=SERIES[6], line=dict(color="white", width=2)),
                    hovertemplate="<b>%{y}</b><br>Lists %{x|%a %d %b}<extra></extra>")
    today = pd.Timestamp.today().normalize()
    fig.add_vline(x=today, line_dash="dot", line_color=MUTED)
    fig.add_annotation(x=today, y=1.02, yref="paper", text="today", showarrow=False, font=dict(color=MUTED))
    fig.update_xaxes(type="date", tickformat="%d %b", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(categoryorder="array", categoryarray=d["name"].tolist(), autorange="reversed")
    return _base(fig, "IPO calendar — bidding windows and listing dates", h=max(360, 26 * len(d) + 100))


# ---------------------------------------------------------------------------
def gmp_vs_actual(perf: pd.DataFrame, fit: dict | None = None) -> go.Figure | None:
    d = perf.dropna(subset=["gmp_pct", "listing_gain_pct"])
    if d.empty:
        return None
    fig = go.Figure()
    for seg, g in d.groupby("category"):
        fig.add_scatter(
            x=g["gmp_pct"], y=g["listing_gain_pct"], mode="markers", name=seg,
            marker=dict(size=10, color=SEGMENT.get(seg), line=dict(color="white", width=2), opacity=0.9),
            customdata=g[["name", "sub_total"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>GMP implied %{x:.1f}%<br>Actual listing %{y:.1f}%<br>Sub %{customdata[1]}x<extra></extra>",
        )
    lo = min(d["gmp_pct"].min(), d["listing_gain_pct"].min(), 0)
    hi = max(d["gmp_pct"].max(), d["listing_gain_pct"].max())
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Perfect GMP prediction",
                    line=dict(color=MUTED, dash="dot", width=2), hoverinfo="skip")
    fig.update_xaxes(title="GMP-implied gain % (before listing)", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title="Actual listing-price gain %")
    return _base(fig, "How accurate was GMP? Predicted vs actual listing gain", h=440)


def listing_bars(perf: pd.DataFrame) -> go.Figure | None:
    d = perf.dropna(subset=["listing_gain_pct"]).sort_values("listing_gain_pct")
    if d.empty:
        return None
    fig = go.Figure()
    fig.add_bar(y=d["name"], x=d["listing_gain_pct"], name="At listing (open price)", orientation="h",
                marker_color=SERIES[0], marker=dict(cornerradius=3),
                hovertemplate="<b>%{y}</b><br>Listing gain %{x:.1f}%<extra></extra>")
    fig.add_bar(y=d["name"], x=d["ltp_gain_pct"], name="Now (latest price)", orientation="h",
                marker_color=SERIES[1], marker=dict(cornerradius=3),
                hovertemplate="<b>%{y}</b><br>Gain vs issue now %{x:.1f}%<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.05)
    fig.update_xaxes(title="% vs issue price", showgrid=True, gridcolor=GRID, side="top")
    fig.update_yaxes(tickfont=dict(size=11))
    return _base(fig, "Listing-day gain vs return today (both vs issue price), sorted by listing gain",
                 h=max(400, 24 * len(d) + 120))


def price_since_listing(h: pd.DataFrame, issue_price: float | None, name: str, nifty: pd.DataFrame | None = None,
                        indexed: bool = False) -> go.Figure | None:
    if h is None or h.empty:
        return None
    fig = go.Figure()
    if indexed and issue_price:
        y = h["Close"] / issue_price * 100
        fig.add_scatter(x=h["Date"], y=y, name=name, line=dict(color=SERIES[0], width=2),
                        hovertemplate="%{x|%d %b}<br>%{y:.1f} (issue price = 100)<extra></extra>")
        if nifty is not None and not nifty.empty:
            n = nifty[nifty["Date"] >= h["Date"].min()]
            if not n.empty:
                base = n["Close"].iloc[0]
                fig.add_scatter(x=n["Date"], y=n["Close"] / base * 100, name="NIFTY 50", line=dict(color=SERIES[1], width=2),
                                hovertemplate="%{x|%d %b}<br>NIFTY %{y:.1f}<extra></extra>")
        fig.add_hline(y=100, line_dash="dot", line_color=MUTED, annotation_text="Issue price / start = 100",
                      annotation_font_color=MUTED)
        fig.update_yaxes(title="Indexed (issue price = 100)")
    else:
        fig.add_scatter(x=h["Date"], y=h["Close"], name="Close", line=dict(color=SERIES[0], width=2),
                        hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.2f}<extra></extra>")
        if issue_price:
            fig.add_hline(y=issue_price, line_dash="dot", line_color=NEG,
                          annotation_text=f"Issue price ₹{issue_price:g}", annotation_font_color=NEG)
        fig.update_yaxes(title="₹ per share")
    fig.update_layout(hovermode="x unified")
    return _base(fig, f"{name}: price since listing", h=380)


def base_rate_bars(t: pd.DataFrame, title: str) -> go.Figure | None:
    if t is None or t.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=t.index, y=t["Avg listing gain %"], name="Avg listing gain %", marker_color=SERIES[0],
                marker=dict(cornerradius=3), customdata=t[["IPOs", "% listed positive"]].values,
                hovertemplate="%{x}<br>Avg listing gain %{y:.1f}%<br>%{customdata[1]:.0f}% listed positive · n=%{customdata[0]:.0f}<extra></extra>")
    fig.add_bar(x=t.index, y=t["Avg gain now (LTP) %"], name="Avg gain today %", marker_color=SERIES[1],
                marker=dict(cornerradius=3), hovertemplate="%{x}<br>Avg gain today %{y:.1f}%<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="% vs issue price")
    return _base(fig, title, h=340)


def score_breakdown(components: dict, penalty: float) -> go.Figure:
    maxes = {"Grey market (GMP)": 35, "Institutional demand (QIB)": 20, "Overall demand": 10, "Fundamentals": 25, "Valuation (P/E)": 10}
    names = list(components)
    got = [components[n] or 0 for n in names]
    fig = go.Figure()
    fig.add_bar(y=names, x=got, orientation="h", name="Points scored", marker_color=SERIES[0], marker=dict(cornerradius=3),
                hovertemplate="%{y}: %{x:.1f}<extra></extra>", text=[f"{g:.1f} / {maxes.get(n, '?')}" for g, n in zip(got, names)],
                textposition="outside", cliponaxis=False)
    fig.add_bar(y=names, x=[maxes.get(n, 0) - g for n, g in zip(names, got)], orientation="h", name="Points available",
                marker_color="rgba(137,135,129,0.18)", hoverinfo="skip")
    fig.update_layout(barmode="stack")
    fig.update_yaxes(autorange="reversed")
    t = "Score breakdown" + (f" (−{penalty:g} SME risk penalty)" if penalty else "")
    return _base(fig, t, h=260)


def financials_bars(fin: pd.DataFrame) -> go.Figure | None:
    if fin is None or fin.empty:
        return None
    idx = {str(i).lower(): i for i in fin.index}
    rows = []
    for label, keys in (("Revenue / Total income", ("revenue", "total income")), ("Profit after tax", ("profit after tax",)),
                        ("Net worth", ("net worth",)), ("Total borrowing", ("borrowing",))):
        k = next((idx[x] for x in idx if any(kk in x for kk in keys)), None)
        if k is not None:
            rows.append((label, fin.loc[k]))
    if not rows:
        return None
    periods = list(fin.columns)[::-1]
    fig = go.Figure()
    for i, (label, s) in enumerate(rows):
        fig.add_bar(x=periods, y=[s[p] for p in periods], name=label, marker_color=SERIES[i], marker=dict(cornerradius=3),
                    hovertemplate=f"{label}<br>%{{x}}: ₹%{{y:,.2f}} Cr<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="₹ Crore")
    return _base(fig, "Financials (restated)", h=360)


# ---------------------------------------------------------------------------
# Simple-view charts: one message each, plain-language labels
# ---------------------------------------------------------------------------
def who_is_bidding(row: pd.Series, title: str = "Who is bidding?") -> go.Figure | None:
    cats = [("Institutions (QIB)", "sub_qib", SERIES[0]), ("HNIs (NII)", "sub_nii", SERIES[1]),
            ("Retail — you", "sub_retail", SERIES[2]), ("Overall", "sub_total", "#52514e")]
    pts = [(l, row.get(k), c) for l, k, c in cats if row.get(k) is not None and not pd.isna(row.get(k))]
    if not pts:
        return None
    fig = go.Figure(go.Bar(
        y=[p[0] for p in pts], x=[p[1] for p in pts], orientation="h", marker_color=[p[2] for p in pts],
        marker=dict(cornerradius=4), text=[f"{p[1]:,.1f}x" for p in pts], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f} times<extra></extra>",
    ))
    fig.add_vline(x=1, line_dash="dot", line_color=MUTED)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=13))
    fig.update_xaxes(title="times subscribed (dotted line = fully subscribed)", showgrid=True, gridcolor=GRID,
                     range=[0, max(p[1] for p in pts) * 1.25 + 0.5])
    return _base(fig, title, h=260, legend=False)


def expected_gain(df: pd.DataFrame, top: int = 12) -> go.Figure | None:
    d = df.dropna(subset=["gmp_pct"])
    d = d[d["gmp_pct"] != 0]
    if d.empty:
        return None
    d = d.sort_values("gmp_pct", ascending=False).head(top).iloc[::-1]
    fig = go.Figure(go.Bar(
        y=d["name"], x=d["gmp_pct"], orientation="h", marker_color=signed_colors(d["gmp_pct"]),
        marker=dict(cornerradius=4), text=[f"{v:+.0f}%" for v in d["gmp_pct"]], textposition="outside", cliponaxis=False,
        customdata=d[["gmp", "price"]].values,
        hovertemplate="<b>%{y}</b><br>GMP ₹%{customdata[0]} on ₹%{customdata[1]} → %{x:.1f}%<extra></extra>",
    ))
    lo, hi = min(0, d["gmp_pct"].min()), max(0, d["gmp_pct"].max())
    pad = (hi - lo) * 0.18 + 2
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=True, range=[lo - (pad if lo < 0 else 0), hi + pad])
    fig.update_yaxes(tickfont=dict(size=13))
    return _base(fig, "Expected listing gain (from GMP)", h=max(260, 34 * len(d) + 70), legend=False)


def winners_losers(perf: pd.DataFrame, n: int = 6) -> go.Figure | None:
    d = perf.dropna(subset=["ltp_gain_pct"]).sort_values("ltp_gain_pct")
    if d.empty:
        return None
    d = pd.concat([d.head(n), d.tail(n)]).drop_duplicates(subset=["name"])
    fig = go.Figure(go.Bar(
        y=d["name"], x=d["ltp_gain_pct"], orientation="h", marker_color=signed_colors(d["ltp_gain_pct"]),
        marker=dict(cornerradius=4), text=[f"{v:+.0f}%" for v in d["ltp_gain_pct"]], textposition="outside", cliponaxis=False,
        customdata=d[["listing_gain_pct", "price"]].values,
        hovertemplate="<b>%{y}</b><br>Today vs issue price %{x:+.1f}%<br>At listing %{customdata[0]:+.1f}%<extra></extra>",
    ))
    lo, hi = min(0, d["ltp_gain_pct"].min()), max(0, d["ltp_gain_pct"].max())
    pad = (hi - lo) * 0.2 + 2
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=True, zerolinewidth=2,
                     range=[lo - (pad if lo < 0 else 0), hi + pad])
    fig.update_yaxes(tickfont=dict(size=13))
    return _base(fig, f"Best & worst since listing", h=max(300, 32 * len(d) + 70), legend=False)


def hit_rate(t: pd.DataFrame, label: str) -> go.Figure | None:
    if t is None or t.empty:
        return None
    fig = go.Figure(go.Bar(
        x=t.index, y=t["% listed positive"], marker_color=SERIES[0], marker=dict(cornerradius=4),
        text=[f"{p:.0f}%<br><span style='font-size:11px'>avg {g:+.0f}%</span>" for p, g in zip(t["% listed positive"], t["Avg listing gain %"])],
        textposition="outside", cliponaxis=False, customdata=t[["IPOs"]].values,
        hovertemplate=f"{label} %{{x}}<br>%{{y:.0f}}% listed above issue price<br>%{{customdata[0]:.0f}} IPOs<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 118], showticklabels=False, showgrid=False)
    fig.update_xaxes(title=label, tickfont=dict(size=13))
    return _base(fig, f"Chance of listing above issue price, by {label[0].lower() + label[1:] if not label.startswith('GMP') else label}", h=320, legend=False)


def revenue_profit(fin: pd.DataFrame) -> go.Figure | None:
    if fin is None or fin.empty:
        return None
    idx = {str(i).lower(): i for i in fin.index}
    rev = next((idx[x] for x in idx if "revenue" in x or "total income" in x), None)
    pat = next((idx[x] for x in idx if "profit after tax" in x), None)
    if rev is None and pat is None:
        return None
    periods = list(fin.columns)[::-1]
    fig = go.Figure()
    if rev is not None:
        fig.add_bar(x=periods, y=[fin.loc[rev, p] for p in periods], name="Revenue", marker_color=SERIES[0], marker=dict(cornerradius=4),
                    hovertemplate="Revenue %{x}: ₹%{y:,.0f} Cr<extra></extra>")
    if pat is not None:
        fig.add_bar(x=periods, y=[fin.loc[pat, p] for p in periods], name="Profit", marker_color=SERIES[2], marker=dict(cornerradius=4),
                    hovertemplate="Profit %{x}: ₹%{y:,.0f} Cr<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="₹ Crore")
    return _base(fig, "Is the business growing? Revenue and profit", h=320)


def subscription_buildup(h: pd.DataFrame) -> go.Figure | None:
    """Day-by-day subscription for one IPO (sheet edition)."""
    if h is None or h.empty:
        return None
    d = h.copy()
    d["x"] = d["day"].fillna("").astype(str)
    d.loc[d["x"].isin(["", "nan", "None"]), "x"] = d["as_of"].dt.strftime("%d %b")
    fig = go.Figure()
    for lbl, k, c in (("Institutions (QIB)", "sub_qib", SERIES[0]), ("HNIs (NII)", "sub_nii", SERIES[1]),
                      ("Retail", "sub_retail", SERIES[2]), ("Overall", "sub_total", "#52514e")):
        if d[k].notna().any():
            fig.add_scatter(x=d["x"], y=d[k], name=lbl, mode="lines+markers", line=dict(color=c, width=2),
                            marker=dict(size=8, line=dict(color="white", width=2)),
                            hovertemplate=f"{lbl} %{{x}}: %{{y:,.2f}}x<extra></extra>")
    fig.add_hline(y=1, line_dash="dot", line_color=MUTED)
    fig.update_yaxes(title="times subscribed")
    fig.update_layout(hovermode="x unified")
    return _base(fig, "Subscription day by day", h=320)
