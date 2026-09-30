"""Sheet data source: facts you enter yourself in a Google Sheet (or a local .xlsx).

This is the permission-free data path for the public site. No website is scraped;
the only request made is downloading *your own* sheet (shared "anyone with the link").
The sheet is converted into the same tables the rest of the app already uses.
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

TABS = ("IPOs", "Subscription", "Listing", "Financials")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _col(df: pd.DataFrame, *names: str):
    m = {_norm(c): c for c in df.columns}
    for n in names:
        if _norm(n) in m:
            return df[m[_norm(n)]]
    return pd.Series([None] * len(df), index=df.index, dtype="object")


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[^0-9.\-]", "", regex=True).replace("", None), errors="coerce")


def _date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def export_url(url: str) -> str:
    """Turn any Google Sheets link (share link or 'publish to web' link) into an .xlsx download URL."""
    m = re.search(r"/spreadsheets/d/e/([\w-]+)", url)
    if m:  # published-to-web link
        return f"https://docs.google.com/spreadsheets/d/e/{m.group(1)}/pub?output=xlsx"
    m = re.search(r"/spreadsheets/d/([\w-]+)", url)
    if m:
        return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx"
    raise ValueError("That doesn't look like a Google Sheets link.")


def load_tabs(source: str) -> dict[str, pd.DataFrame]:
    """source = Google Sheets link or a local .xlsx path."""
    if source.startswith("http"):
        r = requests.get(export_url(source), timeout=30)
        r.raise_for_status()
        if b"<html" in r.content[:500].lower():
            raise RuntimeError("Google returned a web page instead of the sheet. Check sharing is 'Anyone with the link → Viewer'.")
        raw = pd.read_excel(BytesIO(r.content), sheet_name=None)
    else:
        raw = pd.read_excel(Path(source), sheet_name=None)
    tabs = {}
    for t in TABS:
        df = next((v for k, v in raw.items() if _norm(k) == _norm(t)), pd.DataFrame())
        if not df.empty:
            name = _col(df, "IPO name").astype(str).str.strip()
            keep = name.ne("") & name.ne("nan") & ~name.str.lower().str.startswith("example")
            df = df[keep].copy()
            df["IPO name"] = name[keep]
        tabs[t] = df
    return tabs


def to_frames(tabs: dict[str, pd.DataFrame]) -> dict:
    """Convert sheet tabs into (ipos, subscription, performance, subscription history, fundamentals)."""
    ipo = tabs.get("IPOs", pd.DataFrame())
    if not ipo.empty:
        ipo = ipo.drop_duplicates(subset=["IPO name"], keep="last").reset_index(drop=True)
    if ipo.empty:
        empty = pd.DataFrame()
        return {"gmp": empty, "sub": empty, "perf": empty, "sub_hist": empty, "fund": {}}

    seg = _col(ipo, "Segment").astype(str).str.upper()
    g = pd.DataFrame({
        "name": _col(ipo, "IPO name").astype(str).str.strip(),
        "category": ["SME" if "SME" in s else "Mainboard" for s in seg],
        "exchange": _col(ipo, "Exchange"),
        "status": None,
        "gmp": None, "gmp_pct": None, "gmp_low": None, "gmp_high": None, "fire_rating": None,
        "sub_total": None,
        "price_low": _num(_col(ipo, "Price band low (₹)", "Price band low")),
        "price": _num(_col(ipo, "Price band high (₹)", "Price band high", "Issue price")),
        "issue_size_cr": _num(_col(ipo, "Issue size (₹ Cr)", "Issue size")),
        "lot": _num(_col(ipo, "Lot size (shares)", "Lot size")),
        "open": _date(_col(ipo, "Open date")),
        "close": _date(_col(ipo, "Close date")),
        "allotment": _date(_col(ipo, "Allotment date")),
        "listing": _date(_col(ipo, "Listing date")),
        "anchor": _num(_col(ipo, "Anchor raised (₹ Cr)", "Anchor raised")).fillna(0) > 0,
        "updated": None,
        "ig_url": None,
        "rhp_link": _col(ipo, "RHP link"),
        "source_note": _col(ipo, "Source / notes", "Source"),
        "_sheet": True,
    })
    for c in ("gmp", "gmp_pct", "gmp_low", "gmp_high", "fire_rating", "sub_total"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    from .sources import _infer_status  # status from dates only

    g = _infer_status(g.assign(status=None)).reset_index(drop=True)

    # ---- subscription: latest reading per IPO + full history
    sub = tabs.get("Subscription", pd.DataFrame())
    sub_hist = pd.DataFrame()
    s_latest = pd.DataFrame()
    if not sub.empty:
        sub_hist = pd.DataFrame({
            "name": _col(sub, "IPO name").astype(str).str.strip(),
            "as_of": _date(_col(sub, "As of (date)", "As of")),
            "day": _col(sub, "Day"),
            "sub_qib": _num(_col(sub, "QIB (x)", "QIB")),
            "sub_nii": _num(_col(sub, "NII (x)", "NII")),
            "sub_bnii": _num(_col(sub, "bNII (x)", "bNII")),
            "sub_snii": _num(_col(sub, "sNII (x)", "sNII")),
            "sub_retail": _num(_col(sub, "Retail (x)", "Retail")),
            "sub_employee": _num(_col(sub, "Employee (x)", "Employee")),
            "sub_total": _num(_col(sub, "Total (x)", "Total")),
            "source": _col(sub, "Source link", "Source"),
        })
        sub_hist["_d"] = sub_hist["day"].astype(str).str.extract(r"(\d+)")[0].astype(float)
        s_latest = (sub_hist.sort_values(["name", "as_of", "_d", "sub_total"], na_position="first")
                    .drop_duplicates("name", keep="last").drop(columns=["_d", "day"]))
        s_latest = s_latest.rename(columns={"as_of": "sub_as_of"})
        s_latest = s_latest.merge(g[["name", "category", "close"]].rename(columns={"close": "close_date"}), on="name", how="left")
    pe = pd.DataFrame({"name": g["name"], "pe": _num(_col(ipo, "P/E at upper band", "P/E")).values[: len(g)]})
    if not s_latest.empty:
        s_latest = s_latest.merge(pe, on="name", how="left")
    else:
        s_latest = pe.assign(category=g["category"].values)

    # ---- listing performance
    lst = tabs.get("Listing", pd.DataFrame())
    perf = pd.DataFrame()
    if not lst.empty:
        perf = pd.DataFrame({
            "name": _col(lst, "IPO name").astype(str).str.strip(),
            "listing_date": _date(_col(lst, "Listing date")),
            "listing_price": _num(_col(lst, "Listing price (₹)", "Listing price")),
            "listing_day_close": _num(_col(lst, "Day-1 close (₹)", "Day-1 close")),
            "ltp": _num(_col(lst, "Latest price (₹)", "Latest price")),
            "source": _col(lst, "Source link", "Source"),
        })
        base = g[["name", "category", "price", "issue_size_cr"]]
        perf = perf.merge(base, on="name", how="left")
        if not s_latest.empty and "sub_total" in s_latest:
            perf = perf.merge(s_latest[["name", "sub_total"]], on="name", how="left")
        else:
            perf["sub_total"] = None
        perf["category"] = perf["category"].fillna("Mainboard")
        perf["ltp"] = perf["ltp"].fillna(perf["listing_day_close"])
        pct = lambda a: (a / perf["price"] - 1) * 100  # noqa: E731
        perf["listing_gain_pct"] = pct(perf["listing_price"])
        perf["listing_close_gain_pct"] = pct(perf["listing_day_close"])
        perf["ltp_gain_pct"] = pct(perf["ltp"])
        for c in ("gmp", "gmp_pct", "est_price", "gmp_error_pct", "nse_symbol", "bse_code", "ig_url"):
            perf[c] = None
        perf["gmp_pct"] = pd.to_numeric(perf["gmp_pct"])
        perf["gmp_error_pct"] = pd.to_numeric(perf["gmp_error_pct"])
        perf["beat_gmp"] = pd.Series([pd.NA] * len(perf), dtype="boolean")
        perf = perf.dropna(subset=["listing_date"])

    # ---- fundamentals per IPO, shaped like sources.fetch_fundamentals()
    fund: dict[str, dict] = {}
    fin = tabs.get("Financials", pd.DataFrame())
    fin_rows = pd.DataFrame()
    if not fin.empty:
        fin_rows = pd.DataFrame({
            "name": _col(fin, "IPO name").astype(str).str.strip(),
            "period": _col(fin, "Period").astype(str).str.strip(),
            "rev": _num(_col(fin, "Revenue (₹ Cr)", "Revenue")),
            "pat": _num(_col(fin, "Profit after tax (₹ Cr)", "Profit after tax", "PAT")),
            "nw": _num(_col(fin, "Net worth (₹ Cr)", "Net worth")),
            "debt": _num(_col(fin, "Total borrowing (₹ Cr)", "Total borrowing", "Debt")),
        })
    ipo_i = ipo.reset_index(drop=True)
    for i, r in g.reset_index(drop=True).iterrows():
        get = lambda *n: _col(ipo_i.iloc[[i]], *n).iloc[0] if i < len(ipo_i) else None  # noqa: E731
        f: dict = {"url": r.get("rhp_link") if isinstance(r.get("rhp_link"), str) else None, "financials": None, "kpi": {},
                   "valuation": {}, "holding": {}, "reservation": None, "objects": None, "details": {}, "reco": None,
                   "lead_managers": [], "about": None, "promoters": None, "from_sheet": True}
        rows = fin_rows[fin_rows["name"] == r["name"]] if not fin_rows.empty else fin_rows
        if not rows.empty:
            rows = rows.sort_values("period", ascending=False)  # FY26, FY25, FY24 → newest first
            f["financials"] = pd.DataFrame(
                [rows["rev"].values, rows["pat"].values, rows["nw"].values, rows["debt"].values],
                index=["Total Income", "Profit After Tax", "NET Worth", "Total Borrowing"], columns=rows["period"].values)
            lt = rows.iloc[0]
            if pd.notna(lt["nw"]) and lt["nw"]:
                if pd.notna(lt["pat"]):
                    f["kpi"]["ROE"] = lt["pat"] / lt["nw"] * 100
                if pd.notna(lt["debt"]):
                    f["kpi"]["Debt/Equity"] = lt["debt"] / lt["nw"]
            if pd.notna(lt["rev"]) and lt["rev"] and pd.notna(lt["pat"]):
                f["kpi"]["PAT Margin"] = lt["pat"] / lt["rev"] * 100
        pe_v = pd.to_numeric(get("P/E at upper band", "P/E"), errors="coerce")
        if pd.notna(pe_v):
            f["valuation"]["P/E (x)"] = {"pre": None, "post": float(pe_v)}
        pre = pd.to_numeric(get("Promoter holding pre-IPO (%)"), errors="coerce")
        post = pd.to_numeric(get("Promoter holding post-IPO (%)"), errors="coerce")
        if pd.notna(pre) or pd.notna(post):
            f["holding"]["Promoter and Promoter Group"] = {"pre": None if pd.isna(pre) else float(pre),
                                                           "post": None if pd.isna(post) else float(post)}
        fr = pd.to_numeric(get("Fresh issue (₹ Cr)"), errors="coerce")
        of = pd.to_numeric(get("Offer for sale (₹ Cr)"), errors="coerce")
        if pd.notna(fr):
            f["details"]["Fresh Issue"] = f"₹{fr:g} Cr"
        if pd.notna(of):
            f["details"]["Offer for Sale"] = f"₹{of:g} Cr"
        if pd.notna(fr) or pd.notna(of):
            f["details"]["Sale Type"] = ("Fresh capital only" if not (pd.notna(of) and of > 0) else
                                         "Offer for sale only" if not (pd.notna(fr) and fr > 0) else "Fresh capital + offer for sale")
        has = f["financials"] is not None or f["valuation"] or f["holding"] or f["details"]
        if has:
            fund[r["name"]] = f

    return {"gmp": g, "sub": s_latest,
            "perf": perf, "sub_hist": sub_hist, "fund": fund}
