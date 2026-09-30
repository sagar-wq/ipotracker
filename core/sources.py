"""
Data fetchers for IPO Radar.

Sources
-------
1. InvestorGain (live GMP, live subscription by category, GMP performance tracker).
   Their web pages are client-rendered; the page JavaScript calls a plain JSON API:
       https://webnodejs.investorgain.com/cloud/v2/report/data-read/{report}/{page}/{month}/{year}/{fy}/0/{category}
   report 331 = live GMP, 333 = live subscription, 377 = GMP performance tracker.
   This endpoint is undocumented and may change. If it fails we fall back to
   reading the HTML tables on the public page with pandas.read_html.
2. Chittorgarh IPO detail page (financials, KPIs, valuation, reservation,
   objects of the issue, promoter holding, broker recommendations).
3. Yahoo Finance via yfinance (post-listing price history, .NS / .BO symbols).

All fetchers return pandas DataFrames / dicts with a stable, normalised schema so
the rest of the app never has to know where data came from.
"""
from __future__ import annotations

import html as _html
import re
import time
from datetime import date, datetime
from io import StringIO
from typing import Any

import pandas as pd
import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
IG_API = "https://webnodejs.investorgain.com/cloud/v2/report/data-read"
IG_SITE = "https://www.investorgain.com"
IG_PAGES = {
    331: IG_SITE + "/report/ipo-gmp-live/331/",
    333: IG_SITE + "/report/ipo-subscription-live/333/all/",
    377: IG_SITE + "/report/ipo-gmp-performance-tracker/377/all/",
}

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": UA,
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                "Referer": IG_SITE + "/",
                "Origin": IG_SITE,
            }
        )
        _session = s
    return _session


def _get(url: str, params: dict | None = None, tries: int = 3, timeout: int = 20) -> requests.Response:
    last: Exception | None = None
    for i in range(tries):
        try:
            r = session().get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed: {url} ({last})")


# --------------------------------------------------------------------------
# Small parsing helpers
# --------------------------------------------------------------------------
def strip_html(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = re.sub(r"<[^>]+>", " ", str(x))
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def to_num(x: Any) -> float | None:
    """'₹1,091.68 Cr' -> 1091.68 ; '18.08x' -> 18.08 ; '--' -> None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return None if pd.isna(x) else float(x)
    s = strip_html(x)
    m = re.search(r"-?\d[\d,]*\.?\d*", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def fiscal_year(d: date | None = None) -> str:
    d = d or date.today()
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def parse_date(s: Any, ref: date | None = None) -> pd.Timestamp | None:
    """Handles ISO dates, '25-Sep', '25-Sep-26', '28-09-2026'."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    t = strip_html(s)
    if not t or t in ("-", "--"):
        return None
    ref = ref or date.today()
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})$", t.split(" ")[0])
    if m:  # '25-Sep' – year missing, pick the nearest year to today
        best = None
        for y in (ref.year - 1, ref.year, ref.year + 1):
            try:
                cand = datetime.strptime(f"{m.group(1)}-{m.group(2)}-{y}", "%d-%b-%Y").date()
            except ValueError:
                continue
            if best is None or abs((cand - ref).days) < abs((best - ref).days):
                best = cand
        return pd.Timestamp(best) if best else None
    for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%b %d, %Y", "%a, %b %d, %Y"):
        try:
            return pd.Timestamp(datetime.strptime(t.split("T")[0] if fmt == "%Y-%m-%d" else t, fmt))
        except ValueError:
            continue
    try:
        return pd.Timestamp(t)
    except Exception:  # noqa: BLE001
        return None


def _pick(row: dict, *names: str) -> Any:
    """Return the first key whose normalised name matches any of `names`."""
    norm = {re.sub(r"[^a-z0-9~]", "", k.lower()): k for k in row}
    for n in names:
        k = norm.get(re.sub(r"[^a-z0-9~]", "", n.lower()))
        if k is not None:
            return row[k]
    return None


STATUS_CODES = {"U": "Upcoming", "O": "Open", "CT": "Closing Today", "C": "Closed", "LT": "Listing Today", "L": "Listed"}


def _status_from_name_cell(raw: str) -> str | None:
    """InvestorGain appends a badge (U / O / CT / C / LT) after the name."""
    t = strip_html(raw)
    m = re.search(r"(?:IPO|SME)\s*(CT|LT|U|O|C|L)\b", t)
    if m:
        return STATUS_CODES.get(m.group(1))
    return None


def _category_from_name_cell(raw: str) -> tuple[str, str | None]:
    t = strip_html(raw)
    if re.search(r"\bNSE\s*SME\b", t):
        return "SME", "NSE SME"
    if re.search(r"\bBSE\s*SME\b", t):
        return "SME", "BSE SME"
    if re.search(r"\bSME\b", t):
        return "SME", None
    return "Mainboard", None


def _name_from_cell(raw: str) -> tuple[str, str | None]:
    s = str(raw or "")
    m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', s, re.S | re.I)
    if m:
        url = m.group(1)
        if url.startswith("/"):
            url = IG_SITE + url
        return strip_html(m.group(2)), url
    t = strip_html(s)
    t = re.sub(r"\s+(BSE SME|NSE SME|SME|IPO)\b.*$", "", t)
    return t, None


def _clean_name(n: str) -> str:
    n = re.sub(r"\s+(SME|IPO)$", "", n.strip())
    return n


# --------------------------------------------------------------------------
# InvestorGain – generic report reader
# --------------------------------------------------------------------------
def ig_report_rows(report_id: int, category: str = "all", year: int | None = None, max_pages: int = 5) -> list[dict]:
    """Return raw row dicts from an InvestorGain report (JSON API, HTML fallback)."""
    today = date.today()
    yr = year or today.year
    fy = fiscal_year(today)
    rows: list[dict] = []
    try:
        for page in range(1, max_pages + 1):
            url = f"{IG_API}/{report_id}/{page}/{today.month}/{yr}/{fy}/0/{category}"
            data = _get(url, params={"search": "", "v": int(time.time() // 600)}).json()
            chunk = data.get("reportTableData") or data.get("data") or []
            if rows and chunk and chunk[0] == rows[0]:
                break  # API ignored the page number and sent page 1 again
            rows.extend(chunk)
            # most reports return everything on page 1; stop when a page is short/empty
            if len(chunk) < 50:
                break
        if rows:
            return rows
    except Exception:  # noqa: BLE001
        pass
    # ---- HTML fallback -------------------------------------------------
    url = IG_PAGES[report_id]
    if report_id == 377 and year:
        url += f"?year={year}"
    r = _get(url, params=None)
    tables = pd.read_html(StringIO(r.text))
    if not tables:
        raise RuntimeError(f"No table found on {url}")
    t = max(tables, key=len)
    t.columns = [re.sub(r"[▲▼]", "", str(c)).strip() for c in t.columns]
    first = t.columns[0]
    t = t[t[first].astype(str).str.strip().ne(first)]  # repeated header rows
    return t.to_dict("records")


# --------------------------------------------------------------------------
# Normalised tables
# --------------------------------------------------------------------------
def fetch_gmp() -> pd.DataFrame:
    """Current / upcoming / recently closed IPOs with latest GMP."""
    out = []
    for r in ig_report_rows(331):
        name_raw = _pick(r, "Name", "IPO", "~ipo_name") or ""
        name, url = _name_from_cell(name_raw)
        if _pick(r, "~urlrewrite_folder_name"):
            url = IG_SITE + str(_pick(r, "~urlrewrite_folder_name"))
        cat, exch = _category_from_name_cell(name_raw)
        if _pick(r, "~IPO_Category"):
            cat = "SME" if "SME" in str(_pick(r, "~IPO_Category")).upper() else "Mainboard"
        status = STATUS_CODES.get(str(_pick(r, "~ipo_status1") or "").strip()) or _status_from_name_cell(name_raw)
        gmp_raw = _pick(r, "GMP") or ""
        gmp_txt = strip_html(gmp_raw)
        gmp_val = None
        m = re.search(r"₹\s*(-?[\d.,]+)", gmp_txt)
        if m:
            gmp_val = to_num(m.group(1))
        price = to_num(_pick(r, "Price (₹)", "Price", "Price(₹)"))
        lo_hi = re.search(r"(-?[\d.]+)\s*↓\s*/\s*(-?[\d.]+)\s*↑", gmp_txt)
        out.append(
            {
                "name": _clean_name(name),
                "category": cat,
                "exchange": exch or ("BSE, NSE" if cat == "Mainboard" else None),
                "status": status,
                "gmp": gmp_val,
                "gmp_pct": (gmp_val / price * 100) if (gmp_val is not None and price) else None,
                "gmp_low": to_num(lo_hi.group(1)) if lo_hi else None,
                "gmp_high": to_num(lo_hi.group(2)) if lo_hi else None,
                "fire_rating": strip_html(_pick(r, "Rating") or "").count("🔥") or None,
                "sub_total": to_num(_pick(r, "Sub")),
                "price": price,
                "issue_size_cr": to_num(_pick(r, "IPO Size", "Size")),
                "lot": to_num(_pick(r, "Lot")),
                "open": parse_date(_pick(r, "~Srt_Open", "Open")),
                "close": parse_date(_pick(r, "~Srt_Close", "Close")),
                "allotment": parse_date(_pick(r, "~Srt_BoA_Dt", "BoA Dt")),
                "listing": parse_date(_pick(r, "~Str_Listing", "Listing")),
                "anchor": ("✅" in strip_html(_pick(r, "Anchor") or "")) or None,
                "updated": strip_html(_pick(r, "Updated-On", "Updated On") or ""),
                "ig_url": url,
            }
        )
    df = pd.DataFrame(out)
    if not df.empty:
        df = df[df["name"].astype(str).str.strip().ne("")]
        df = df.drop_duplicates(subset=["name"], keep="first").reset_index(drop=True)
        df = _infer_status(df)
    return df


def fetch_subscription() -> pd.DataFrame:
    """Live subscription bifurcation (QIB / sNII / bNII / NII / Retail)."""
    out = []
    for r in ig_report_rows(333):
        name_raw = _pick(r, "Name", "IPO") or ""
        name, url = _name_from_cell(name_raw)
        cat, exch = _category_from_name_cell(name_raw)
        total_raw = strip_html(_pick(r, "Total") or "")
        out.append(
            {
                "name": _clean_name(name),
                "category": cat,
                "sub_total": to_num(total_raw.split(" ")[0] if total_raw else None),
                "sub_as_of": " ".join(total_raw.split(" ")[1:]) or None,
                "sub_qib": to_num(_pick(r, "QIB")),
                "sub_snii": to_num(_pick(r, "SHNI", "sNII")),
                "sub_bnii": to_num(_pick(r, "BHNI", "bNII")),
                "sub_nii": to_num(_pick(r, "NII", "HNI")),
                "sub_retail": to_num(_pick(r, "RII", "Retail")),
                "sub_employee": to_num(_pick(r, "EMP", "Employee")),
                "pe": to_num(_pick(r, "P/E", "PE")),
                "close_date": parse_date(_pick(r, "Closing Date")),
            }
        )
    df = pd.DataFrame(out)
    if not df.empty:
        df = df[df["name"].astype(str).str.strip().ne("")]
        df = (df.sort_values("sub_total", ascending=False, na_position="last")
                .drop_duplicates(subset=["name"], keep="first").reset_index(drop=True))
    return df


def fetch_performance(year: int | None = None) -> pd.DataFrame:
    """Listed IPOs: GMP before listing vs actual listing & current price."""
    out = []
    for r in ig_report_rows(377, year=year, max_pages=5):
        name_raw = _pick(r, "IPO", "Name") or ""
        name, url = _name_from_cell(name_raw)
        is_sme = bool(re.search(r"\bSME\b", strip_html(name_raw)))
        sym_raw = strip_html(_pick(r, "Symbol") or "")
        nse_sym, bse_code = None, None
        for part in [p.strip() for p in sym_raw.split(",") if p.strip()]:
            if part.isdigit():
                bse_code = part
            else:
                nse_sym = part
        lp = strip_html(_pick(r, "Listing Price") or "")
        ldc = strip_html(_pick(r, "Listing Day Close") or "")
        ltp = strip_html(_pick(r, "Closing Price (LTP)", "LTP", "Current Price") or "")
        out.append(
            {
                "name": _clean_name(name),
                "category": "SME" if is_sme else "Mainboard",
                "nse_symbol": nse_sym,
                "bse_code": bse_code,
                "listing_date": parse_date(_pick(r, "Listing Dt", "Listing Date")),
                "issue_size_cr": to_num(_pick(r, "Size")),
                "sub_total": to_num(_pick(r, "Sub")),
                "gmp": to_num(_pick(r, "GMP")),
                "price": to_num(_pick(r, "Price")),
                "est_price": to_num(_pick(r, "Est Price")),
                "listing_price": to_num(lp),
                "listing_gain_pct": _pct_in_brackets(lp),
                "listing_day_close": to_num(ldc),
                "listing_close_gain_pct": _pct_in_brackets(ldc),
                "ltp": to_num(ltp) if not ltp.startswith("₹-") else None,
                "ltp_gain_pct": _pct_in_brackets(ltp),
                "ig_url": url,
            }
        )
    df = pd.DataFrame(out)
    if not df.empty:
        df = df.drop_duplicates(subset=["name", "listing_date"], keep="first").reset_index(drop=True)
        df["gmp_pct"] = df["gmp"] / df["price"] * 100
        df["gmp_error_pct"] = df["listing_gain_pct"] - df["gmp_pct"]
        df["beat_gmp"] = df["listing_price"] >= df["est_price"]
    return df


def _pct_in_brackets(s: str) -> float | None:
    m = re.search(r"\((-?[\d.]+)%\)", s or "")
    return float(m.group(1)) if m else None


def _infer_status(df: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp(date.today())

    def st(r):
        if isinstance(r.get("status"), str) and r["status"]:
            return r["status"]
        o, c, l_ = r.get("open"), r.get("close"), r.get("listing")
        if l_ is not None and pd.notna(l_) and l_ <= today:
            return "Listed"
        if c is not None and pd.notna(c) and c < today:
            return "Closed"
        if c is not None and pd.notna(c) and c == today:
            return "Closing Today"
        if o is not None and pd.notna(o) and o <= today:
            return "Open"
        return "Upcoming"

    df["status"] = df.apply(st, axis=1)
    return df


# --------------------------------------------------------------------------
# GMP day-wise history for one IPO (from its InvestorGain page)
# --------------------------------------------------------------------------
def fetch_gmp_history(ig_url: str) -> pd.DataFrame:
    r = _get(ig_url)
    tables = pd.read_html(StringIO(r.text))
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any("gmp date" in c for c in cols) or (any(c.strip() == "gmp" for c in cols) and any("time" in c for c in cols)):
            t.columns = [str(c) for c in t.columns]
            date_col = next(c for c in t.columns if "date" in c.lower() or "time" in c.lower())
            gmp_col = next(c for c in t.columns if c.strip().upper() == "GMP")
            out = pd.DataFrame(
                {
                    "when": t[date_col].astype(str).str.extract(r"^(\d{1,2}[- ][A-Za-z]{3,4}[ ,]*[\d:]*\s*[apm]*)")[0],
                    "gmp": t[gmp_col].map(to_num),
                }
            ).dropna(subset=["gmp"])
            out["ts"] = out["when"].map(_parse_hist_ts)
            return out.dropna(subset=["ts"]).sort_values("ts")
    return pd.DataFrame(columns=["when", "gmp", "ts"])


def _parse_hist_ts(s: str) -> pd.Timestamp | None:
    if not isinstance(s, str):
        return None
    s = s.replace("Sept", "Sep").strip().rstrip(",")
    y = date.today().year
    for fmt in ("%d-%b %H:%M", "%d %b, %I:%M %p", "%d %b %I:%M %p", "%d-%b"):
        try:
            d = datetime.strptime(s, fmt).replace(year=y)
            if d.date() > date.today():
                d = d.replace(year=y - 1)
            return pd.Timestamp(d)
        except ValueError:
            continue
    return None


def find_chittorgarh_url(ig_url: str | None) -> str | None:
    """InvestorGain detail pages link to the matching Chittorgarh page."""
    if not ig_url:
        return None
    try:
        txt = _get(ig_url).text
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"https?://www\.chittorgarh\.com/ipo/[a-z0-9\-]+/\d+/?", txt)
    return m.group(0) if m else None


# --------------------------------------------------------------------------
# Chittorgarh – fundamentals
# --------------------------------------------------------------------------
def fetch_fundamentals(url: str) -> dict:
    """Parse a chittorgarh.com/ipo/<slug>/<id>/ page into structured sections."""
    r = _get(url)
    text = r.text
    tables = pd.read_html(StringIO(text))
    res: dict[str, Any] = {"url": url, "financials": None, "kpi": {}, "valuation": {}, "holding": {},
                           "reservation": None, "objects": None, "details": {}, "reco": None,
                           "lead_managers": [], "about": None, "promoters": None}
    for t in tables:
        t.columns = [str(c).strip() for c in t.columns]
        first_col = t.iloc[:, 0].astype(str).str.strip()
        joined = " ".join(first_col.tolist()).lower()
        hdr = " ".join(t.columns).lower()
        if "profit after tax" in joined and ("total income" in joined or "revenue" in joined):
            f = t.set_index(t.columns[0])
            f = f[~f.index.astype(str).str.contains("Amount in", case=False)]
            res["financials"] = f.apply(lambda col: col.map(to_num))
        elif first_col.str.fullmatch(r"ROE|ROCE|RoNW|Debt/Equity|PAT Margin", case=False).any():
            for _, row in t.iterrows():
                res["kpi"][str(row.iloc[0]).strip()] = to_num(row.iloc[-1])
        elif "p/e" in joined and ("eps" in joined or "market cap" in joined):
            for _, row in t.iterrows():
                key = str(row.iloc[0]).strip()
                res["valuation"][key] = {"pre": to_num(row.iloc[1]), "post": to_num(row.iloc[-1]) if t.shape[1] > 2 else None}
        elif "promoter" in joined and "pre" in hdr:
            for _, row in t.iterrows():
                res["holding"][str(row.iloc[0]).strip()] = {"pre": to_num(row.iloc[1]), "post": to_num(row.iloc[-1])}
        elif "investor category" in hdr or ("qib" in joined and "retail" in joined and "%" in t.to_string()):
            res["reservation"] = t
        elif "issue objects" in hdr or "objects" in hdr:
            res["objects"] = t
        elif "review by" in hdr or "subscribe" in hdr:
            res["reco"] = t
        elif t.shape[1] == 2 and ("sale type" in joined or "face value" in joined or "fresh issue" in joined or "offer for sale" in joined or "total issue size" in joined):
            for _, row in t.iterrows():
                res["details"][str(row.iloc[0]).strip()] = strip_html(row.iloc[1])
    m = re.search(r"Company Promoters:\s*</?\w*>?\s*([^<]+)", text)
    if m:
        res["promoters"] = strip_html(m.group(1))
    res["lead_managers"] = list(dict.fromkeys(
        strip_html(x) for x in re.findall(r'ipo-lead-manager-review/\d+/all/\d+/"[^>]*>([^<]+)</a>', text)))[:6]
    m = re.search(r"<h2[^>]*>\s*About[^<]*</h2>(.*?)<h2", text, re.S | re.I)
    if m:
        res["about"] = strip_html(m.group(1))[:1500]
    return res


# --------------------------------------------------------------------------
# Market prices after listing
# --------------------------------------------------------------------------
def fetch_price_history(nse_symbol: str | None, bse_code: str | None, start: pd.Timestamp | None) -> pd.DataFrame:
    import yfinance as yf

    def ok(v):
        return isinstance(v, str) and v.strip() and v.lower() != "nan"

    nse_symbol = nse_symbol if ok(nse_symbol) else None
    bse_code = bse_code if ok(bse_code) else None
    tickers = []
    if nse_symbol:
        tickers.append(f"{nse_symbol}.NS")
    if bse_code:
        tickers.append(f"{bse_code}.BO")
    for tk in tickers:
        try:
            h = yf.Ticker(tk).history(start=(start - pd.Timedelta(days=1)).strftime("%Y-%m-%d") if start is not None else None,
                                      period=None if start is not None else "3mo", auto_adjust=False)
            if h is not None and not h.empty:
                h = h.reset_index()
                h["Date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None)
                h["ticker"] = tk
                return h[["Date", "Open", "High", "Low", "Close", "Volume", "ticker"]]
        except Exception:  # noqa: BLE001
            continue
    return pd.DataFrame()


def fetch_nifty(start: pd.Timestamp) -> pd.DataFrame:
    import yfinance as yf

    try:
        h = yf.Ticker("^NSEI").history(start=start.strftime("%Y-%m-%d"))
        h = h.reset_index()
        h["Date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None)
        return h[["Date", "Close"]]
    except Exception:  # noqa: BLE001
        return pd.DataFrame()
