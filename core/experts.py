"""Expert / analyst opinions for an IPO.

Three layers, combined into one consensus:
1. News headlines (Google News + Bing News RSS) classified as Apply / Neutral / Avoid by
   keyword rules. Question-style headlines ("Should you subscribe?") that don't state a view
   are shown but not counted.
2. Views you add yourself (e.g. "SBI Securities – Subscribe") – stored locally, always counted.
3. Optional: Claude reads the articles and extracts each brokerage's exact call (needs API key).
"""
from __future__ import annotations

import html as _html
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, quote_plus, urlparse

import pandas as pd

from . import sources as S
from . import persist

RATINGS = ["Apply", "Apply (long term)", "Apply (listing gains)", "Neutral", "Avoid"]
POSITIVE = {"Apply", "Apply (long term)", "Apply (listing gains)"}

BROKERS = [
    "SBI Securities", "Bajaj Broking", "Anand Rathi", "Motilal Oswal", "ICICI Securities", "ICICI Direct", "HDFC Securities",
    "Kotak Securities", "Axis Securities", "Angel One", "Choice Broking", "Marwadi", "Arihant Capital", "Geojit",
    "Nirmal Bang", "Ventura", "Canara Bank Securities", "Reliance Securities", "StoxBox", "SMC Global", "Mehta Equities",
    "Swastika Investmart", "Hensex", "BP Equities", "Master Capital", "Religare", "Sharekhan", "Nuvama", "Emkay",
    "Asit C Mehta", "Ashika", "LKP Securities", "Prabhudas Lilladher", "Elara", "Jainam", "Deven Choksey", "Aditya Birla Money",
    "Dilip Davda", "Canmoney", "Bonanza", "Master Trust", "Capital Market", "Chittorgarh", "Anand Rathi Share",
]

_AVOID = r"\b(avoid|skip|stay away|give (it )?a miss|do not subscribe|don'?t subscribe|not subscribe|negative rating|sell rating)\b"
_NEUTRAL = r"\b(neutral|may apply|wait and watch|cautious|high[- ]risk investors only|risk takers only|mixed (views|review|bag))\b"
_LONG = r"\b(long[- ]term|long haul)\b"
_LISTING = r"\b(listing gains?|listing pop)\b"
_POS = (r"\b(subscribe|apply|buy|bullish|positive (view|outlook|rating|review)|recommend(s|ed)?|thumbs up|"
        r"go for it|worth (a|the) bet|good bet)\b")
_VIEW_MARKERS = r"\b(say|says|recommend|recommends|rating|rate|brokerages?|analysts?|experts?|advise|suggest|verdict|review)\b"


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


_NOISE = [
    r"should (you|i|one) (apply|subscribe|avoid|invest|bid)[^?.:]*[?.:]?", r"(apply|subscribe|invest) or (not|avoid|skip)\??",
    r"good or bad\??", r"is it worth[^?]*\??", r"before (you|investors) (subscribe|apply|invest)", r"how to (apply|subscribe|check)",
    r"things to know", r"what (brokerages|analysts|experts) say", r"here'?s what[^.:]*", r"(check|know) [^.:]*(gmp|price|review|details)[^.:]*",
    r"subscription status", r"allotment status", r"day \d+",
]


def classify(title: str) -> str | None:
    """Return a rating from a headline, or None when it doesn't state a view."""
    t = title.lower()
    for pat in _NOISE:
        t = re.sub(pat, " ", t)
    if re.search(_AVOID, t):
        return "Avoid"
    if re.search(_NEUTRAL, t):
        return "Neutral"
    if re.search(_POS, t) or re.search(r"\bthumbs up\b", t):
        if re.search(_LONG, t):
            return "Apply (long term)"
        if re.search(_LISTING, t):
            return "Apply (listing gains)"
        return "Apply"
    return None


def find_broker(title: str) -> str | None:
    for b in BROKERS:
        if b.lower() in title.lower():
            return b
    return None


# --------------------------------------------------------------------------
def _rss(url: str) -> list[dict]:
    try:
        r = S._get(url, tries=2, timeout=12)
        root = ET.fromstring(r.content)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for it in root.iter("item"):
        title = _clean(it.findtext("title") or "")
        link = it.findtext("link") or ""
        if "bing.com" in link and "url=" in link:
            link = parse_qs(urlparse(link).query).get("url", [link])[0]
        src = it.findtext("source") or it.findtext("{http://www.bing.com/news/search}Source") or ""
        if not src and " - " in title:
            title, src = title.rsplit(" - ", 1)
        pub = it.findtext("pubDate")
        try:
            ts = parsedate_to_datetime(pub).replace(tzinfo=None) if pub else None
        except Exception:  # noqa: BLE001
            ts = None
        out.append({"title": title.strip(), "link": link, "source": _clean(src), "ts": ts,
                    "summary": _clean(it.findtext("description") or "")[:300]})
    return out


def fetch_news(name: str, days: int = 45) -> pd.DataFrame:
    """Headlines about this IPO's review / recommendation from Google News and Bing News."""
    q = f'"{name}" IPO (subscribe OR avoid OR review OR brokerages OR recommend)'
    urls = [
        f"https://news.google.com/rss/search?q={quote_plus(q)}+when:{days}d&hl=en-IN&gl=IN&ceid=IN:en",
        f"https://www.bing.com/news/search?q={quote_plus(name + ' IPO review subscribe')}&format=rss&setlang=en-IN",
    ]
    items: list[dict] = []
    for u in urls:
        items += _rss(u)
    if not items:
        return pd.DataFrame(columns=["title", "link", "source", "ts", "rating", "broker"])
    df = pd.DataFrame(items)
    key = name.lower().split()[0]
    df = df[df["title"].str.lower().str.contains(re.escape(key))]
    df["_k"] = df["title"].str.lower().str.replace(r"[^a-z0-9]", "", regex=True).str[:70]
    df = df.drop_duplicates("_k").drop(columns="_k")
    df["rating"] = df["title"].map(classify)
    df["broker"] = df["title"].map(find_broker)
    return df.sort_values("ts", ascending=False, na_position="last").head(25).reset_index(drop=True)


def fetch_news_many(names: list[str]) -> dict[str, pd.DataFrame]:
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda n: (n, fetch_news(n)), names))
    return dict(res)


# --------------------------------------------------------------------------
# Manually added / AI-extracted views (stored locally)
# --------------------------------------------------------------------------
COLS = ["ipo", "source", "rating", "note", "origin", "ts"]


def _all() -> list[dict]:
    return persist.load("expert_views", []) or []


def add_view(ipo: str, source: str, rating: str, note: str = "", origin: str = "manual") -> None:
    rows = [r for r in _all() if not (r.get("ipo") == ipo and r.get("source") == source.strip())]
    rows.append({"ipo": ipo, "source": source.strip(), "rating": rating, "note": note, "origin": origin,
                 "ts": pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M")})
    persist.save("expert_views", rows)


def remove_view(ipo: str, source: str) -> None:
    persist.save("expert_views", [r for r in _all() if not (r.get("ipo") == ipo and r.get("source") == source)])


def views(ipo: str | None = None) -> pd.DataFrame:
    rows = [r for r in _all() if ipo is None or r.get("ipo") == ipo]
    df = pd.DataFrame(rows, columns=COLS)
    return df.sort_values("ts", ascending=False).reset_index(drop=True) if not df.empty else df


# --------------------------------------------------------------------------
def consensus(news: pd.DataFrame | None, stored: pd.DataFrame | None) -> dict:
    """Count one vote per named source (stored views override headlines from the same broker)."""
    votes: dict[str, str] = {}
    covered = set()
    if stored is not None and not stored.empty and "origin" in stored:
        covered = {str(o).lower() for o in stored["origin"].dropna()}
    if news is not None and not news.empty:
        for _, r in news.dropna(subset=["rating"]).iterrows():
            # skip an article whose brokerage calls were already saved individually
            if r.get("source") and any(str(r["source"]).lower() in o for o in covered):
                continue
            key = r["broker"] or r["source"] or r["title"][:40]
            votes.setdefault(f"news::{key}", r["rating"])
    if stored is not None and not stored.empty:
        for _, r in stored.iterrows():
            # an explicit entry for a broker replaces the headline vote for it
            votes = {k: v for k, v in votes.items() if not k.endswith(f"::{r['source']}")}
            votes[f"view::{r['source']}"] = r["rating"]
    n = len(votes)
    pos = sum(v in POSITIVE for v in votes.values())
    neu = sum(v == "Neutral" for v in votes.values())
    avo = sum(v == "Avoid" for v in votes.values())
    net = (pos - avo) / n if n else None
    if n == 0:
        label = "No expert views found"
    elif net >= 0.6 and pos >= 2:
        label = "Mostly Apply"
    elif net >= 0.25:
        label = "Leaning Apply"
    elif net <= -0.4:
        label = "Mostly Avoid"
    elif net < 0:
        label = "Leaning Avoid"
    else:
        label = "Mixed"
    return {"n": n, "apply": pos, "neutral": neu, "avoid": avo, "net": net, "label": label,
            "long_term": sum(v == "Apply (long term)" for v in votes.values()),
            "listing": sum(v == "Apply (listing gains)" for v in votes.values())}


# --------------------------------------------------------------------------
def ai_extract(api_key: str, ipo: str, news: pd.DataFrame, model: str = "claude-sonnet-5") -> list[dict]:
    """Ask Claude to read the headlines (and article text where reachable) and list each brokerage's call."""
    import anthropic

    texts = []
    for _, r in news.head(6).iterrows():
        body = ""
        try:
            if r["link"] and "news.google.com" not in r["link"]:
                body = _clean(S._get(r["link"], tries=1, timeout=10).text)[:5000]
        except Exception:  # noqa: BLE001
            pass
        texts.append({"title": r["title"], "source": r["source"], "summary": r.get("summary", ""), "text": body})
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model, max_tokens=1200,
        messages=[{"role": "user", "content": (
            f"From the news items below about the {ipo} IPO, extract every brokerage / analyst recommendation that is "
            "explicitly stated. Return ONLY a JSON array of objects: "
            '{"source": broker or analyst name, "rating": one of ["Apply","Apply (long term)","Apply (listing gains)","Neutral","Avoid"], '
            '"reason": short reason (max 20 words)}. Do not guess; skip items without an explicit call.\n\n'
            + json.dumps(texts)[:40000])}],
    )
    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\[.*\]", txt, re.S)
    try:
        arr = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        arr = []
    return [a for a in arr if isinstance(a, dict) and a.get("rating") in RATINGS and a.get("source")]
