"""Scoring, pros/cons and historical base rates.

Everything here is transparent rule-based logic you can read and tune (see the
THRESHOLDS dict). It produces *signals*, not investment advice.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

USE_GMP = True  # set False by the app in sheet mode (no GMP data at all)

THRESHOLDS = {
    "gmp_pct_strong": 30, "gmp_pct_good": 15, "gmp_pct_weak": 5,
    "qib_strong": 20, "qib_good": 5, "qib_weak": 1,
    "total_hot": 50, "retail_hot": 20,
    "pe_cheap": 15, "pe_rich": 40,
    "roe_good": 15, "roe_weak": 8,
    "de_high": 1.0, "pat_margin_good": 10,
    "promoter_post_low": 50, "small_issue_cr": 50,
}


# --------------------------------------------------------------------------
def merge_live(gmp: pd.DataFrame, sub: pd.DataFrame) -> pd.DataFrame:
    if gmp is None or gmp.empty:
        return pd.DataFrame()
    if sub is None or sub.empty:
        return gmp.copy()
    key = lambda s: s.str.lower().str.replace(r"[^a-z0-9]", "", regex=True)  # noqa: E731
    g, s = gmp.copy(), sub.copy()
    g["_k"], s["_k"] = key(g["name"]), key(s["name"])
    g = g.drop_duplicates(subset=["_k"], keep="first")
    if "sub_total" in s:
        s = s.sort_values("sub_total", ascending=False, na_position="last")
    s = s.drop_duplicates(subset=["_k"], keep="first")
    s = s.drop(columns=[c for c in ("name", "category") if c in s.columns])
    m = g.merge(s, on="_k", how="left", suffixes=("", "_s"))
    if "sub_total_s" in m:
        m["sub_total"] = m["sub_total_s"].combine_first(m["sub_total"])
        m = m.drop(columns=["sub_total_s"])
    return m.drop(columns=["_k"]).reset_index(drop=True)


# --------------------------------------------------------------------------
def _bucket_gmp(p: float | None) -> str:
    if p is None or pd.isna(p):
        return "n/a"
    if p <= 0:
        return "≤0%"
    if p < 10:
        return "0–10%"
    if p < 25:
        return "10–25%"
    if p < 50:
        return "25–50%"
    return "50%+"


def _bucket_sub(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "n/a"
    if x < 2:
        return "<2x"
    if x < 10:
        return "2–10x"
    if x < 50:
        return "10–50x"
    if x < 150:
        return "50–150x"
    return "150x+"


GMP_ORDER = ["≤0%", "0–10%", "10–25%", "25–50%", "50%+"]
SUB_ORDER = ["<2x", "2–10x", "10–50x", "50–150x", "150x+"]


def base_rates(perf: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """How did past IPOs actually list, grouped by GMP and subscription buckets."""
    if perf is None or perf.empty:
        return {}
    p = perf.copy()
    p["gmp_bucket"] = p["gmp_pct"].map(_bucket_gmp)
    p["sub_bucket"] = p["sub_total"].map(_bucket_sub)

    def agg(g):
        return pd.Series({
            "IPOs": len(g),
            "Avg listing gain %": g["listing_gain_pct"].mean(),
            "Median listing gain %": g["listing_gain_pct"].median(),
            "% listed positive": (g["listing_gain_pct"] > 0).mean() * 100,
            "% listed ≥ GMP estimate": g["beat_gmp"].mean() * 100,
            "Avg gain now (LTP) %": g["ltp_gain_pct"].mean(),
        })

    out = {}
    for col, order in (("gmp_bucket", GMP_ORDER), ("sub_bucket", SUB_ORDER)):
        t = p.groupby(col, observed=True).apply(agg, include_groups=False)
        t = t.reindex([o for o in order if o in t.index])
        out[col] = t.round(1)
    out["by_segment"] = p.groupby("category").apply(agg, include_groups=False).round(1)
    return out


def gmp_reliability(perf: pd.DataFrame) -> dict[str, Any]:
    p = perf.dropna(subset=["gmp_pct", "listing_gain_pct"])
    if len(p) < 5:
        return {}
    err = p["listing_gain_pct"] - p["gmp_pct"]
    slope, intercept = np.polyfit(p["gmp_pct"], p["listing_gain_pct"], 1)
    corr = p["gmp_pct"].corr(p["listing_gain_pct"])
    return {
        "n": len(p),
        "corr": corr,
        "mae": err.abs().mean(),
        "median_err": err.median(),
        "slope": slope,
        "intercept": intercept,
        "pct_within_10": (err.abs() <= 10).mean() * 100,
        "direction_hit": ((p["gmp_pct"] > 0) == (p["listing_gain_pct"] > 0)).mean() * 100,
    }


# --------------------------------------------------------------------------
def allotment_odds(row: pd.Series) -> dict[str, Any]:
    """Rough retail odds of getting 1 lot and expected listing-day value per application."""
    r = row.get("sub_retail")
    lot, price, gmp = row.get("lot"), row.get("price"), row.get("gmp")
    out: dict[str, Any] = {"odds": None, "application_amt": None, "gain_per_lot": None, "expected_value": None}
    if lot and price:
        out["application_amt"] = lot * price  # per lot; SME issues may require 2 lots minimum – check the RHP
    if lot and gmp is not None and not pd.isna(gmp):
        out["gain_per_lot"] = lot * gmp
    if r is not None and not pd.isna(r) and r > 0:
        # SEBI rule: mainboard retail oversubscribed -> lottery for min lot, odds ≈ 1/x.
        out["odds"] = min(1.0, 1.0 / r)
        if out["gain_per_lot"] is not None:
            out["expected_value"] = out["odds"] * out["gain_per_lot"]
    return out


# --------------------------------------------------------------------------
def _lin(x, x0, x1, y0, y1):
    if x is None or pd.isna(x):
        return None
    if x <= x0:
        return y0
    if x >= x1:
        return y1
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def _cagr(series: pd.Series) -> float | None:
    s = series.dropna()
    if len(s) < 2 or s.iloc[-1] is None or s.iloc[-1] <= 0 or s.iloc[0] <= 0:
        return None
    n = len(s) - 1
    return ((s.iloc[0] / s.iloc[-1]) ** (1 / n) - 1) * 100  # chittorgarh lists newest first


def fundamentals_view(f: dict | None) -> dict[str, Any]:
    """Derive growth / quality metrics from the parsed chittorgarh page."""
    if not f:
        return {}
    v: dict[str, Any] = {}
    fin = f.get("financials")
    if fin is not None and not fin.empty:
        # keep annual columns (drop part-year e.g. '30 Jun 2026' when a Mar column exists)
        cols = list(fin.columns)
        annual = [c for c in cols if "Mar" in str(c)] or cols
        f2 = fin[annual]
        idx = {str(i).lower(): i for i in f2.index}
        rev_key = next((idx[k] for k in idx if "revenue" in k or "total income" in k), None)
        pat_key = next((idx[k] for k in idx if "profit after tax" in k), None)
        debt_key = next((idx[k] for k in idx if "borrowing" in k), None)
        nw_key = next((idx[k] for k in idx if "net worth" in k), None)
        if rev_key is not None:
            v["rev_cagr"] = _cagr(f2.loc[rev_key])
            v["revenue_latest"] = f2.loc[rev_key].iloc[0]
        if pat_key is not None:
            v["pat_cagr"] = _cagr(f2.loc[pat_key])
            v["pat_latest"] = f2.loc[pat_key].iloc[0]
            v["pat_declined"] = len(f2.loc[pat_key].dropna()) > 1 and f2.loc[pat_key].iloc[0] < f2.loc[pat_key].iloc[1]
            v["loss_making"] = f2.loc[pat_key].iloc[0] is not None and f2.loc[pat_key].iloc[0] < 0
        if debt_key is not None and nw_key is not None and f2.loc[nw_key].iloc[0]:
            v["de_calc"] = f2.loc[debt_key].iloc[0] / f2.loc[nw_key].iloc[0]
            v["debt_rising"] = len(f2.loc[debt_key].dropna()) > 1 and f2.loc[debt_key].iloc[0] > 1.3 * (f2.loc[debt_key].iloc[1] or 0)
    k = {kk.lower(): vv for kk, vv in (f.get("kpi") or {}).items()}
    v["roe"] = k.get("roe") or k.get("ronw")
    v["roce"] = k.get("roce")
    v["de"] = k.get("debt/equity", v.get("de_calc"))
    v["pat_margin"] = k.get("pat margin")
    val = {kk.lower(): vv for kk, vv in (f.get("valuation") or {}).items()}
    pe = next((vv for kk, vv in val.items() if "p/e" in kk), None)
    if pe:
        v["pe_post"] = pe.get("post") or pe.get("pre")
    mc = next((vv for kk, vv in val.items() if "market cap" in kk), None)
    if mc:
        v["mcap_cr"] = mc.get("post") or mc.get("pre")
    hold = {kk.lower(): vv for kk, vv in (f.get("holding") or {}).items()}
    ph = next((vv for kk, vv in hold.items() if "promoter" in kk), None)
    if ph:
        v["promoter_pre"], v["promoter_post"] = ph.get("pre"), ph.get("post")
    det = {kk.lower(): vv for kk, vv in (f.get("details") or {}).items()}
    fresh = next((vv for kk, vv in det.items() if kk.startswith("fresh issue")), None)
    ofs = next((vv for kk, vv in det.items() if "offer for sale" in kk), None)
    fr, of = _cr_in(fresh), _cr_in(ofs)
    if fr is not None or of is not None:
        tot = (fr or 0) + (of or 0)
        v["ofs_share"] = (of or 0) / tot * 100 if tot else None
    v["sale_type"] = det.get("sale type")
    return v


def _cr_in(s: str | None) -> float | None:
    import re

    if not s:
        return None
    m = re.search(r"₹\s*([\d,.]+)\s*Cr", s)
    return float(m.group(1).replace(",", "")) if m else None


# --------------------------------------------------------------------------
def evaluate(row: pd.Series, fund: dict | None = None, rates: dict | None = None,
             gmp_trend: pd.DataFrame | None = None) -> dict[str, Any]:
    T = THRESHOLDS
    pros: list[str] = []
    cons: list[str] = []
    notes: list[str] = []
    comp: dict[str, float] = {}

    gp = row.get("gmp_pct")
    gmp = row.get("gmp")
    status = row.get("status") or ""
    is_sme = row.get("category") == "SME"

    # ---- GMP -----------------------------------------------------------
    if not USE_GMP:
        pass
    elif gp is not None and not pd.isna(gp):
        comp["Grey market (GMP)"] = _lin(gp, 0, 50, 0, 35)
        if gp >= T["gmp_pct_strong"]:
            pros.append(f"Strong GMP of ₹{gmp:g} ({gp:.1f}% over issue price) signals high listing-day demand.")
        elif gp >= T["gmp_pct_good"]:
            pros.append(f"Healthy GMP of {gp:.1f}% over issue price.")
        elif gp <= 0:
            cons.append("GMP is zero or negative — grey market expects listing at or below issue price.")
        elif gp < T["gmp_pct_weak"]:
            cons.append(f"Thin GMP ({gp:.1f}%) — little listing-gain cushion after costs.")
    else:
        comp["Grey market (GMP)"] = 8
        notes.append("No active GMP yet (common for SME and early-stage upcoming IPOs).")
    lo, hi = row.get("gmp_low"), row.get("gmp_high")
    if hi and gmp is not None and hi > 0 and gmp < 0.6 * hi:
        cons.append(f"GMP has fallen from a high of ₹{hi:g} to ₹{gmp:g} — sentiment is cooling.")
    if gmp_trend is not None and len(gmp_trend) >= 3:
        d = gmp_trend["gmp"].iloc[-1] - gmp_trend["gmp"].iloc[0]
        if d > 0:
            pros.append(f"GMP trend is rising (+₹{d:g} over {len(gmp_trend)} readings).")
        elif d < 0:
            cons.append(f"GMP trend is falling (₹{d:g} over {len(gmp_trend)} readings).")

    # ---- Subscription --------------------------------------------------
    qib, tot, ret, nii = (row.get(k) for k in ("sub_qib", "sub_total", "sub_retail", "sub_nii"))
    has_sub = tot is not None and not pd.isna(tot)
    early = status in ("Open", "Upcoming")  # QIBs typically bid on the final day
    if qib is not None and not pd.isna(qib) and early and qib < 1:
        comp["Institutional demand (QIB)"] = 10
    elif qib is not None and not pd.isna(qib):
        comp["Institutional demand (QIB)"] = _lin(math.log10(max(qib, 0.01)), -1, math.log10(60), 0, 20)
        if qib >= T["qib_strong"]:
            pros.append(f"QIBs subscribed {qib:g}x — strong institutional conviction (the most informed money).")
        elif qib >= T["qib_good"]:
            pros.append(f"Decent QIB interest at {qib:g}x.")
        elif qib < T["qib_weak"] and status in ("Closed", "Closing Today", "Listed", "Listing Today"):
            cons.append(f"QIB portion undersubscribed ({qib:g}x) — institutions largely stayed away.")
        elif qib < T["qib_weak"]:
            notes.append(f"QIB at {qib:g}x so far; QIBs usually bid on the last day, so re-check at close.")
        if ret and qib is not None and ret > 5 * max(qib, 0.2) and ret > 5:
            cons.append(f"Retail ({ret:g}x) far ahead of QIB ({qib:g}x) — demand looks retail-driven rather than institution-backed.")
    else:
        comp["Institutional demand (QIB)"] = 10
        if status in ("Upcoming",):
            notes.append("Subscription not started yet.")
    if has_sub and early and tot < 1:
        comp["Overall demand"] = 5  # too early to judge
    elif has_sub:
        comp["Overall demand"] = _lin(math.log10(max(tot, 0.01)), -1, math.log10(150), 0, 10)
        if tot >= T["total_hot"]:
            pros.append(f"Heavily oversubscribed overall ({tot:g}x).")
            cons.append(f"At {tot:g}x, allotment chances are slim.")
        elif tot < 1 and status in ("Closed", "Closing Today", "Listed"):
            cons.append(f"Issue subscribed only {tot:g}x overall — weak demand.")
    else:
        comp["Overall demand"] = 5
    if nii and nii >= 30:
        pros.append(f"HNIs bid {nii:g}x — typically a sign of expected listing gains (note: HNI demand can be leverage-fuelled).")

    # ---- Fundamentals --------------------------------------------------
    fv = fundamentals_view(fund) if fund else {}
    f_score, f_n = 0.0, 0
    if fv:
        rc, pc = fv.get("rev_cagr"), fv.get("pat_cagr")
        if rc is not None:
            f_n += 1
            f_score += _lin(rc, 0, 30, 0, 1)
            (pros if rc >= 15 else cons if rc < 5 else notes).append(f"Revenue CAGR ≈ {rc:.1f}% over the reported years.")
        if pc is not None:
            f_n += 1
            f_score += _lin(pc, 0, 40, 0, 1)
            (pros if pc >= 20 else cons if pc < 5 else notes).append(f"Profit (PAT) CAGR ≈ {pc:.1f}%.")
        if fv.get("loss_making"):
            cons.append("Company is loss-making in the latest period.")
            f_score -= 0.5
        elif fv.get("pat_declined"):
            cons.append("Latest annual profit is lower than the previous year.")
        roe = fv.get("roe")
        if roe is not None:
            f_n += 1
            f_score += _lin(roe, 5, 25, 0, 1)
            if roe >= T["roe_good"]:
                pros.append(f"Good return on equity ({roe:.1f}%).")
            elif roe < T["roe_weak"]:
                cons.append(f"Low return on equity ({roe:.1f}%).")
        de = fv.get("de")
        if de is not None:
            f_n += 1
            f_score += _lin(-de, -2, 0, 0, 1)
            if de >= T["de_high"]:
                cons.append(f"High leverage — debt/equity {de:.2f}.")
            elif de < 0.3:
                pros.append(f"Low debt (D/E {de:.2f}).")
        if fv.get("debt_rising"):
            cons.append("Borrowings rose sharply in the latest year.")
        pm = fv.get("pat_margin")
        if pm is not None and pm >= T["pat_margin_good"]:
            pros.append(f"Healthy PAT margin ({pm:.1f}%).")
        ofs = fv.get("ofs_share")
        if ofs is not None:
            if ofs >= 60:
                cons.append(f"{ofs:.0f}% of the issue is Offer-for-Sale — money goes to selling shareholders, not the company.")
            elif ofs <= 10:
                pros.append("Issue is (almost) entirely fresh capital — proceeds go into the business.")
        pp = fv.get("promoter_post")
        if pp is not None and pp < T["promoter_post_low"]:
            cons.append(f"Promoter holding drops to {pp:.1f}% post-issue.")
        comp["Fundamentals"] = (f_score / f_n * 25) if f_n else 12.5
    else:
        comp["Fundamentals"] = 12.5
        notes.append("Fundamentals not loaded yet. Click 'Load fundamentals' below for revenue, profit, debt and valuation checks.")

    # ---- Valuation -----------------------------------------------------
    pe = fv.get("pe_post") if fv else None
    pe = pe or row.get("pe")
    if pe is not None and not pd.isna(pe) and pe > 0:
        comp["Valuation (P/E)"] = _lin(-pe, -60, -10, 0, 10)
        if pe <= T["pe_cheap"]:
            pros.append(f"Modest valuation (P/E ≈ {pe:.1f}).")
        elif pe >= T["pe_rich"]:
            cons.append(f"Rich valuation (P/E ≈ {pe:.1f}) — compare with listed peers before applying.")
    else:
        comp["Valuation (P/E)"] = 5

    # ---- Structural ----------------------------------------------------
    penalty = 0.0
    if is_sme:
        penalty += 5
        cons.append("SME IPO: higher risk, lower liquidity, large minimum ticket (≈₹1–2.5 L) and a 5% price band on listing day.")
    size = row.get("issue_size_cr")
    if size and size < T["small_issue_cr"] and not is_sme:
        cons.append(f"Small issue (₹{size:g} Cr) — can be volatile / operator-prone.")
    anc = row.get("anchor")
    anc = None if anc is None or (isinstance(anc, float) and pd.isna(anc)) else bool(anc)
    if anc is True:
        pros.append("Anchor investors participated before the issue opened.")
    elif anc is False and not is_sme:
        cons.append("No anchor book.")
    if size and size >= 5000:
        notes.append("Very large issue — big supply tends to cap listing pop; better for long-term holders.")

    # ---- Base rates ----------------------------------------------------
    if rates and "gmp_bucket" in rates and gp is not None and not pd.isna(gp):
        b = _bucket_gmp(gp)
        if b in rates["gmp_bucket"].index:
            br = rates["gmp_bucket"].loc[b]
            notes.append(
                f"History: of {int(br['IPOs'])} recent IPOs with GMP {b}, {br['% listed positive']:.0f}% listed positive, "
                f"avg listing gain {br['Avg listing gain %']:.1f}%, and {br['% listed ≥ GMP estimate']:.0f}% met/beat the GMP estimate."
            )

    raw = sum(v for v in comp.values() if v is not None)
    if not USE_GMP:  # rescale the remaining 65 points to 100
        raw = raw / 65 * 100
    raw -= penalty
    score = max(0.0, min(100.0, raw))
    confidence = sum([(gp is not None and not pd.isna(gp)) or not USE_GMP, qib is not None and not pd.isna(qib), bool(fv)])
    if score >= 70:
        verdict = "Strong signals"
    elif score >= 55:
        verdict = "Positive"
    elif score >= 40:
        verdict = "Mixed"
    else:
        verdict = "Weak"
    return {"score": round(score, 1), "verdict": verdict, "components": comp, "penalty": penalty,
            "pros": pros, "cons": cons, "notes": notes, "confidence": ["Low", "Low", "Medium", "High"][confidence],
            "fundamentals": fv}


def quick_scores(df: pd.DataFrame, rates: dict | None = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    d = df.copy()
    ev = d.apply(lambda r: evaluate(r, None, rates), axis=1)
    d["score"] = ev.map(lambda e: e["score"])
    d["verdict"] = ev.map(lambda e: e["verdict"])
    odds = d.apply(allotment_odds, axis=1)
    d["retail_odds"] = odds.map(lambda o: o["odds"])
    d["gain_per_lot"] = odds.map(lambda o: o["gain_per_lot"])
    d["min_invest"] = odds.map(lambda o: o["application_amt"])
    return d


# --------------------------------------------------------------------------
def ai_summary(api_key: str, name: str, payload: dict, model: str = "claude-sonnet-5") -> str:
    """Optional narrative using the Anthropic API (needs `pip install anthropic`)."""
    import json

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=900,
        messages=[{
            "role": "user",
            "content": (
                "You are an equity research assistant for Indian IPOs. Using ONLY the data below, write a concise "
                f"assessment of the {name} IPO: 3-5 key positives, 3-5 key risks, what to check in the RHP, and whether "
                "it looks better suited to listing-gain or long-term investors. Be balanced, flag missing data, and do "
                "not give a buy/sell instruction.\n\nDATA:\n" + json.dumps(payload, default=str, indent=1)[:12000]
            ),
        }],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


# ==========================================================================
# Market mood + final Apply / Avoid call
# ==========================================================================
def market_mood(perf: pd.DataFrame, nifty: pd.DataFrame | None = None) -> dict[str, Any]:
    """How hot is the IPO market right now? Based on the last 10 mainboard listings (+ NIFTY trend if available)."""
    out: dict[str, Any] = {"label": "Unknown", "level": 0, "bullets": []}
    if perf is None or perf.empty:
        return out
    p = perf.dropna(subset=["listing_gain_pct", "listing_date"]).sort_values("listing_date", ascending=False)
    mb = p[p["category"] == "Mainboard"]
    base = mb if len(mb) >= 6 else p
    last, prev = base.head(10), base.iloc[10:20]
    pos = (last["listing_gain_pct"] > 0).mean() * 100
    avg = last["listing_gain_pct"].mean()
    now = last["ltp_gain_pct"].mean() if "ltp_gain_pct" in last else None
    out.update({"pos": pos, "avg": avg, "now": now, "n": len(last)})
    if pos >= 75 and avg >= 15:
        lvl = 2
    elif pos >= 60 and avg >= 5:
        lvl = 1
    elif pos >= 40 and avg >= 0:
        lvl = 0
    else:
        lvl = -1
    seg = "mainboard " if base is mb else ""
    out["bullets"].append(f"Last {len(last)} {seg}listings: {pos:.0f}% listed above issue price, average listing gain {avg:+.1f}%.")
    if now is not None and not pd.isna(now):
        out["bullets"].append(f"Those same IPOs are {now:+.1f}% vs issue price today on average.")
    if len(prev) >= 5:
        pavg = prev["listing_gain_pct"].mean()
        trend = "improving" if avg > pavg + 3 else "weakening" if avg < pavg - 3 else "steady"
        out["trend"] = trend
        out["bullets"].append(f"Trend vs the 10 before: {trend} (was {pavg:+.1f}%).")
    if nifty is not None and len(nifty) > 25:
        n = nifty.sort_values("Date")
        r1m = (n["Close"].iloc[-1] / n["Close"].iloc[-22] - 1) * 100
        out["nifty_1m"] = r1m
        out["bullets"].append(f"NIFTY 50 over the last month: {r1m:+.1f}%.")
        if r1m <= -4:
            lvl -= 1
        elif r1m >= 3 and lvl < 2:
            lvl += 0  # supportive, but listings drive the call
    lvl = max(-1, min(2, lvl))
    out["level"] = lvl
    out["label"] = {2: "Hot", 1: "Healthy", 0: "Cooling", -1: "Cold"}[lvl]
    return out


CALLS = {
    "Apply": ("#0ca30c", "✅"),
    "Apply for long term": ("#0ca30c", "✅"),
    "Apply for listing gains": ("#1baf7a", "☑️"),
    "Wait – decide on last day": ("#fab219", "⏳"),
    "Avoid": ("#d03b3b", "⛔"),
    "Closed": ("#898781", "🔒"),
}


def recommend(row: pd.Series, ev: dict, cons: dict | None, mood: dict | None) -> dict[str, Any]:
    """Combine the rule-based signal, expert consensus and market mood into one call."""
    cons = cons or {"n": 0, "net": None, "label": "No expert views found", "long_term": 0, "listing": 0, "apply": 0, "avoid": 0, "neutral": 0}
    mood = mood or {"level": 0, "label": "Unknown"}
    status = row.get("status") or ""
    gp = row.get("gmp_pct")
    gp = None if gp is None or pd.isna(gp) else float(gp)
    qib = row.get("sub_qib")
    qib = None if qib is None or pd.isna(qib) else float(qib)
    is_sme = row.get("category") == "SME"
    fv = ev.get("fundamentals") or {}

    adj_exp = 0.0
    if cons["n"] and cons["net"] is not None:
        adj_exp = cons["net"] * (15 if cons["n"] >= 2 else 8)
    adj_mood = {2: 5, 1: 2, 0: -3, -1: -8}.get(mood.get("level", 0), 0)
    final = max(0.0, min(100.0, ev["score"] + adj_exp + adj_mood))

    weak_fund = bool(fv) and ((fv.get("roe") is not None and fv["roe"] < 8) or fv.get("loss_making") or
                              (fv.get("de") is not None and fv["de"] >= 1) or (fv.get("pe_post") or 0) >= 45)
    good_fund = bool(fv) and not weak_fund and ((fv.get("pat_cagr") or 0) >= 15 or (fv.get("roe") or 0) >= 15)
    exp_pos = cons["n"] >= 1 and (cons["net"] or 0) >= 0.5
    exp_neg = cons["label"] in ("Mostly Avoid", "Leaning Avoid")
    last_day_pending = status in ("Open", "Upcoming") and qib is None or (status == "Open" and qib is not None and qib < 1)

    if status in ("Closed", "Listed", "Listing Today"):
        call = "Closed"
    elif (status == "Open" and (qib is None or qib < 1) and not exp_neg and (gp is None or 0 < gp < 25) and not is_sme
          and final < 60):
        call = "Wait – decide on last day"
    elif cons["label"] == "Mostly Avoid" or final < 38 or (gp is not None and gp <= 0 and not exp_pos) \
            or (is_sme and (gp is None or gp < 5) and not exp_pos):
        call = "Avoid"
    elif final >= 60 and (gp is None or gp >= 10):
        call = "Apply for listing gains" if (weak_fund or cons["listing"] > cons["long_term"] or is_sme) else "Apply"
    elif exp_pos and good_fund and not is_sme:
        call = "Apply for long term"
    elif gp is not None and gp >= 15 and final >= 48 and not exp_neg:
        call = "Apply for listing gains"
    elif last_day_pending:
        call = "Wait – decide on last day"
    elif exp_pos and final >= 48:
        call = "Apply for long term" if not is_sme else "Apply for listing gains"
    else:
        call = "Avoid"

    why = [f"Signal score {ev['score']:.0f}/100 ({ev['verdict']}) from GMP, demand, fundamentals and valuation."]
    if gp is not None:
        why.append(f"Grey market implies {gp:+.1f}% listing gain.")
    if qib is not None:
        why.append(f"Institutions (QIB) have bid {qib:g}x.")
    if cons["n"]:
        why.append(f"Experts: {cons['label']} ({cons['apply']} apply · {cons['neutral']} neutral · {cons['avoid']} avoid).")
    else:
        why.append("No expert views found yet. Add ones you read, or check the news links.")
    if mood.get("label") != "Unknown":
        why.append(f"IPO market mood: {mood['label']}.")

    change = []
    if call.startswith("Wait") or call == "Avoid":
        if qib is None or qib < 5:
            change.append("Strong QIB bidding (10x+) on the last day would make this more attractive.")
        if gp is None or gp < 10:
            change.append("A GMP rising above ~15% would improve the listing-gain case.")
        if not cons["n"]:
            change.append("Positive brokerage reviews would strengthen the case.")
    elif call.startswith("Apply"):
        change.append("Re-check on the last day: a falling GMP or weak QIB bidding would weaken this call.")
        if not fv:
            change.append("Load fundamentals to confirm the business quality before applying.")

    evidence = sum([gp is not None, qib is not None, cons["n"] >= 2, bool(fv)])
    confidence = ["Low", "Low", "Medium", "High", "High"][evidence]
    color, icon = CALLS[call]
    return {"call": call, "icon": icon, "color": color, "final": round(final, 1), "confidence": confidence,
            "why": why, "change": change, "adj_expert": adj_exp, "adj_mood": adj_mood}
