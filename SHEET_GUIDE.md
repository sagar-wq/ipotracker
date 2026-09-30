# The permission-free public edition: your Google Sheet

In this edition, **you** are the data source. You type facts about each IPO into a free Google Sheet, taken from public documents and news. The public website reads only that sheet. Nothing is scraped, no one's database is copied, no GMP numbers are shown, and there are no buy/avoid calls. Every page carries a disclaimer.

Your private copy on your PC is not affected. It keeps live GMP, scraping and the Apply/Avoid calls for your own use.

---

## One-time setup (about 20 minutes)

### 1. Put the template in Google Sheets
1. Open **drive.google.com** → **New → File upload** → choose `templates/IPO_Radar_data_sheet.xlsx`.
2. Double-click it → **Open with Google Sheets** → **File → Save as Google Sheets**.
3. Rename it, e.g. "IPO Radar data".

### 2. Share it (read-only)
**Share** → under *General access* choose **Anyone with the link** → role **Viewer** → **Copy link**.
(Only you can edit. The app, and anyone with the link, can only view. That's fine, since the same facts appear on the site anyway.)

### 3. Point the website at it
In **share.streamlit.io** → your app → **⋮ → Settings → Secrets**, paste:
```toml
DATA_SOURCE = "sheet"
SHEET_URL   = "https://docs.google.com/spreadsheets/d/....../edit?usp=sharing"
PUBLIC_MODE = "true"
```
Save. The app restarts and reads your sheet. (First-time hosting steps are in **DEPLOY.md**.)

To try it on your PC first, open Command Prompt in the `ipo_radar` folder and run:
```
set DATA_SOURCE=sheet
set SHEET_URL=<your sheet link>
set PUBLIC_MODE=true
.venv\Scripts\streamlit run app.py
```

---

## The four tabs

| Tab | One row per… | What goes in |
|---|---|---|
| **IPOs** | IPO | Name, Mainboard/SME, exchange, price band, lot size, issue size, fresh issue / OFS (₹ Cr), open / close / allotment / listing dates, anchor amount, P/E, promoter holding before and after, RHP link, source note |
| **Subscription** | IPO per bidding day | Date, Day 1/2/3, QIB x, NII x (bNII / sNII optional), Retail x, Total x, source link |
| **Listing** | Listed IPO | Listing date, listing price, day-1 close, optional latest price and date, source link |
| **Financials** | IPO per financial year | FY26 / FY25 / FY24: revenue, profit after tax, net worth, total borrowing (₹ Cr), RHP page |

Hover over any column header in the sheet to see a note about what to enter. Grey rows starting with "Example" are ignored; delete them when you like.

**Formatting rules:** numbers only (no ₹, commas or "x"). Percentages as plain numbers (71.2 means 71.2%). Dates as dates. Use exactly the same IPO name in every tab.

---

## Where to find each fact (all public)

| Fact | Where |
|---|---|
| Price band, lot size, dates, issue size, fresh / OFS | The company's price-band announcement (newspaper ad, press release) and the **RHP**. The RHP is on the SEBI website (Filings → Public Issues), the NSE/BSE "Public issues" pages, or the lead manager's site. |
| P/E at upper band | The price-band ad, or the RHP's "Basis for Offer Price" section |
| Promoter holding pre / post | The RHP ("Capital Structure") or the price-band ad |
| Anchor amount | News on the day before opening ("X raises ₹Y crore from anchor investors") |
| Revenue / profit / net worth / debt | The RHP's "Summary of Financial Information" table, entered once per IPO |
| Subscription by category | Evening news reports on each bidding day (Economic Times, Business Standard, Moneycontrol, Mint…), or the exchange's bid-details notice. **Read and type the numbers**; don't paste whole tables. |
| Listing price, day-1 close | Listing-day news reports |

Put the link you used in the **Source** column. It's good practice, and it's what makes this edition permission-free.

---

## Your routine

| When | What | Time |
|---|---|---|
| A new IPO's price band is announced | Add a row in **IPOs** and 2–3 rows in **Financials** | ~10 min per IPO |
| Each evening of the bidding days | Add a row in **Subscription** for each open IPO | ~1–2 min per IPO |
| Listing day | Add a row in **Listing** | ~1 min |
| Quiet weeks | Nothing | 0 |

Changes appear on the site within about 10 minutes, or immediately after a visitor clicks **Refresh now**. You can edit from your phone with the Google Sheets app.

The **"What history says"** page learns from your Listing tab: the more listed IPOs you add, the more meaningful it gets. You can back-fill past IPOs from news archives whenever you have time.

---

## House rules that keep it permission-free
1. Type individual facts yourself and note the source. **Never paste another site's table.**
2. **No GMP numbers** in the sheet. The site links to GMP pages instead.
3. **No buy / avoid opinions** on the public site. Keep `PUBLIC_MODE = "true"`.
4. Keep the disclaimer (it's built in).
5. Don't upload or re-host RHP PDFs. Link to them.

This keeps the risk low, not zero, and it isn't legal advice. If the site grows large or starts earning money, have a one-time chat with a lawyer.
