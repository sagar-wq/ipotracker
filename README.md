# 📡 IPO Radar — local dashboard for Indian IPOs

A Streamlit app that runs on your own computer (`http://localhost:8501`) and brings together everything you need to decide which IPOs to apply for:

| View | What you get |
|---|---|
| **Dashboard** | Open / closing-today / upcoming counts, an *action board* of IPOs you can still apply to (signal score, GMP %, QIB / retail subscription, retail allotment odds, 1-lot cost, GMP gain per lot, close & listing dates), IPO calendar, GMP ranking, recent listings. |
| **Open & upcoming** | Full table (CSV export), subscription comparison across IPOs (QIB vs NII vs Retail), and the category-wise bifurcation (QIB · sNII · bNII · Retail · Total) for any one IPO. |
| **Recently listed** | Every IPO listed in the last *N* days (default 30): issue price, GMP before listing, listing gain, day-1 close, return today, whether it met the GMP estimate; chart of listing gain vs return today; daily price chart since listing (optionally indexed vs NIFTY 50). |
| **IPO deep dive** | Signal score with breakdown, **pros & cons**, context from history, subscription bars, GMP history, allotment odds and expected value per application. One click loads **fundamentals** from Chittorgarh: revenue / PAT / net worth / borrowing trend, ROE, D/E, P/E, market cap, promoter holding pre/post, fresh issue vs OFS, objects of the issue, reservation, lead managers, broker recommendations. Optional **AI analyst note** (Anthropic API key). |
| **Trends & base rates** | How reliable is GMP? Predicted vs actual listing gain, accuracy stats, and what happened historically for each GMP band and subscription band; Mainboard vs SME. Plus the GMP history this app records locally. |
| **Watchlist** | Save IPOs with notes; see their live status and score. |

## The call: Apply / Wait / Avoid

Every open or upcoming IPO gets one of: **✅ Apply · ✅ Apply for long term · ☑️ Apply for listing gains · ⏳ Wait, decide on last day · ⛔ Avoid**, with the reasons and "what would change this call" on the IPO details page. It combines three things:

1. **Signal score** (0–100) from GMP, QIB/HNI/retail demand, fundamentals and valuation (see below).
2. **Expert views**, worth up to ±15 points:
   - News headlines from Google News and Bing News that state a brokerage view ("Brokerages bullish…", "Avoid, say analysts…") are auto-tagged Apply / Neutral / Avoid. Question headlines ("Should you apply?") are shown but not counted.
   - Views you add yourself on the IPO details page (e.g. *SBI Securities: Apply*) always count, and replace a headline from the same brokerage.
   - Optional: with an Anthropic API key, **"Let AI read the articles"** extracts each brokerage's exact call and reason.
3. **IPO market mood**, from +5 to −8 points: Hot / Healthy / Cooling / Cold, from the last 10 mainboard listings (share listed positive, average gain, trend) plus the NIFTY's one-month move.

Rules of thumb built in: QIBs bid late, so low QIB numbers before the last day lead to **Wait** rather than Avoid. SME IPOs without a real grey-market premium get **Avoid**. Weak fundamentals or rich valuation with a strong GMP gives **Apply for listing gains** rather than Apply. The logic lives in `recommend()` in `core/analysis.py`, and you can edit it.

## Put it online

See **[DEPLOY.md](DEPLOY.md)** to host it free on Streamlit Community Cloud. The settings (entered as secrets, see `.streamlit/secrets.example.toml`) are:
- `ADMIN_PASSWORD` (+ `SECRET_KEY`, `GITHUB_TOKEN`, `GIST_ID`): **access-code login**. Visitors enter a 10-character code that you create, revoke, extend or reset in the **🔑 Admin panel**. Codes, per-user watchlists and admin-curated expert views are stored permanently in a free private GitHub Gist.
- `APP_PASSWORD`: shows a password screen first (private app with every feature).
- `DATA_SOURCE = "sheet"` + `SHEET_URL`: **permission-free public edition**. Data comes only from a Google Sheet you fill in with facts from public documents; see **[SHEET_GUIDE.md](SHEET_GUIDE.md)** and `templates/IPO_Radar_data_sheet.xlsx`.
- `PUBLIC_MODE = "true"`: information-only. Removes Apply/Avoid calls, scores and verdicts, adds a disclaimer, and keeps each visitor's watchlist private.

## Quick start

1. Install Python 3.10+ (python.org — on Windows tick “Add Python to PATH”).
2. Unzip this folder and double-click **`run_windows.bat`** (Windows) or run **`./run_mac_linux.sh`** (Mac/Linux).
   The first run creates a virtual environment and installs dependencies (a minute or two), then opens the browser.

Manual alternative:
```bash
pip install -r requirements.txt
streamlit run app.py
```

In the sidebar choose **Live** (default) or **Demo snapshot** (a frozen real snapshot from 25-Sep-2026, for offline use).

## Where the data comes from

| Data | Source |
|---|---|
| GMP, fire rating, price, lot, dates, anchor | InvestorGain live GMP report (331) |
| Subscription by category (QIB, sNII, bNII, NII, Retail) | InvestorGain live subscription report (333) |
| Listing price, day-1 close, current price, GMP accuracy | InvestorGain GMP performance tracker (377) |
| Day-wise GMP history | The IPO's InvestorGain page + your own local snapshots |
| Financials, KPIs, valuation, holding, objects, reservation | Chittorgarh IPO page |
| Daily prices after listing, NIFTY 50 | Yahoo Finance (`yfinance`) |

InvestorGain's pages call an undocumented JSON API (`webnodejs.investorgain.com/cloud/v2/report/data-read/...`), which the app reads directly; if that fails it falls back to reading the HTML tables. Results are cached for 10 minutes, and the last good fetch is kept in `data/ipo_radar.db`, so a temporary outage doesn't blank the app.

**Build your own GMP history:** every Live refresh stores a snapshot. To collect snapshots even when the app isn't open, schedule `python refresh.py` (Windows Task Scheduler, or cron: `*/30 9-19 * * 1-6 cd /path/to/ipo_radar && python refresh.py`).

## How the signal score works (0–100)

Transparent rules in `core/analysis.py` — tweak the `THRESHOLDS` dict to taste.

| Component | Max | Logic |
|---|---|---|
| Grey market (GMP %) | 35 | 0 % → 0 pts, 50 %+ → 35 pts |
| Institutional demand (QIB x) | 20 | log scale, ~60x → full |
| Overall demand (total x) | 10 | log scale, ~150x → full |
| Fundamentals | 25 | revenue & PAT CAGR, ROE, D/E (neutral 12.5 until loaded) |
| Valuation (P/E) | 10 | P/E 10 → full, 60 → 0 |
| SME penalty | −5 | liquidity / ticket-size / data-quality risk |

≥70 *Strong signals* · 55–70 *Positive* · 40–55 *Mixed* · <40 *Weak*. "Data confidence" tells you how many of GMP / QIB / fundamentals were available.

Pros/cons rules include: strong or fading GMP, GMP trend, QIB conviction vs retail-driven demand, heavy oversubscription (low allotment odds), HNI frenzy, revenue/PAT growth, losses, ROE, leverage and rising debt, PAT margin, OFS-heavy issues, promoter holding after the issue, rich/cheap P/E, SME risks, small issue size, anchor book, very large issues, plus the historical base rate for the IPO's GMP band.

**Retail allotment odds** ≈ 1 ÷ retail subscription (SEBI's lottery for the minimum lot when oversubscribed). **Expected value** = odds × GMP × lot size — a rough listing-day expectation.

## Things worth knowing

- GMP is unofficial and can swing a lot in the last 48 h; the *Trends & base rates* page shows how far off it has been.
- QIBs usually bid on the last day — a low QIB number on day 1–2 means little.
- SME IPOs: bigger minimum ticket, 5 % circuit on listing day, thin GMP data, higher failure rate after listing (compare "listing gain" vs "now" for SMEs on the Recently listed page).
- Always read the RHP (risk factors, litigation, related-party transactions, peer valuation) before applying.

## Troubleshooting

- **"Fetch issues" in the sidebar** — a site changed its API or layout, or blocked the request. The app keeps working from the last cached data. Run `python tests/test_parsers.py` to check the parsers, then adjust the field names in `core/sources.py` (`fetch_gmp`, `fetch_subscription`, `fetch_performance`).
- **No price chart for an SME stock** — Yahoo Finance doesn't cover every fresh SME listing.
- **Fundamentals not auto-detected** — find the IPO on chittorgarh.com and paste its URL into the box in Deep Dive.

## Project layout

```
app.py              Streamlit UI (all pages)
core/sources.py     fetchers + parsers (InvestorGain, Chittorgarh, Yahoo Finance)
core/analysis.py    merge, score, pros/cons, allotment odds, base rates, market mood, final call, AI note
core/experts.py     news-headline expert views, saved views, consensus, AI extraction
core/ui.py          cards, calendar strip, call panel and other visual blocks
core/sheet.py       Google Sheet / .xlsx data source for the permission-free public edition
core/access.py      access codes (hashed), expiry/revoke/reset, signed stay-logged-in links, per-user watchlists
core/persist.py     permanent JSON storage: private GitHub Gist, or local files
templates/          IPO_Radar_data_sheet.xlsx - the sheet template
core/charts.py      Plotly charts (colour-blind-safe palette)
core/store.py       SQLite snapshots, cache, watchlist
core/demo.py        offline demo snapshot
refresh.py          headless snapshot for schedulers
tests/              offline parser tests
```

> For information and education only — not investment advice. Consult a SEBI-registered adviser before investing.
