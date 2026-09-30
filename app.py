"""IPO Radar – a local dashboard for Indian IPOs (Mainboard + SME).

Run:  streamlit run app.py
"""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st

from core import analysis as A
from core import charts as C
from core import demo, sources as S, store
from core import ui
from core import experts as X
from core import sheet as SH
from core import access as AC
from core import persist

st.set_page_config(page_title="IPO Radar", page_icon="📡", layout="wide")


def setting(key: str, default=None):
    """Read a setting from Streamlit secrets (hosting) or environment variables (local)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:  # noqa: BLE001  (no secrets file locally)
        pass
    return os.environ.get(key, default)


APP_PASSWORD = str(setting("APP_PASSWORD", "") or "")
PUBLIC_MODE = str(setting("PUBLIC_MODE", "false")).lower() in ("1", "true", "yes")
SHEET = str(setting("DATA_SOURCE", "")).lower() == "sheet"
SHEET_URL = str(setting("SHEET_URL", "") or "")
A.USE_GMP = not SHEET  # the sheet edition never shows GMP

ADMIN_PASSWORD = str(setting("ADMIN_PASSWORD", "") or "")
CODES_ON = bool(ADMIN_PASSWORD)  # access-code login is switched on by setting an admin password
persist.configure(str(setting("GITHUB_TOKEN", "") or ""), str(setting("GIST_ID", "") or ""))
AC.configure(str(setting("SECRET_KEY", "") or ADMIN_PASSWORD or "local"))


def hmac_eq(a: str, b: str) -> bool:
    import hmac as _h
    return _h.compare_digest(a.encode(), b.encode())


def _logout(msg: str | None = None):
    for k in ("user", "is_admin", "user_hash"):
        st.session_state.pop(k, None)
    if "k" in st.query_params:
        del st.query_params["k"]
    if msg:
        st.session_state.login_msg = msg


def login_page():
    st.markdown("""<style>
      [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {display:none}
      .block-container {max-width: 480px; padding-top: 8vh}
      .lp-title {font-size: 2.2rem; font-weight: 800; margin-bottom: 0}
      .lp-sub {opacity: .7; margin-bottom: 1.2rem}
    </style>""", unsafe_allow_html=True)
    st.markdown('<div class="lp-title">📡 IPO Radar</div><div class="lp-sub">Indian IPOs: GMP, subscription, fundamentals and expert views in one place.</div>',
                unsafe_allow_html=True)
    if st.session_state.get("login_msg"):
        st.warning(st.session_state.pop("login_msg"))
    locked = st.session_state.get("lock_until", 0) > pd.Timestamp.now().timestamp()
    with st.form("login", border=True):
        code = st.text_input("Access code", placeholder="e.g. ABCDE-12345", max_chars=12,
                             help="The 10-character code you received from the admin. Dashes and capital letters don't matter.")
        ok = st.form_submit_button("Enter", type="primary", width="stretch", disabled=locked)
    if locked:
        st.error("Too many wrong attempts. Please wait a minute and try again.")
    elif ok:
        rec, why = AC.verify(code)
        if rec:
            AC.record_login(rec["id"])
            st.session_state.user = {"id": rec["id"], "label": rec["label"]}
            st.session_state.user_hash = rec["hash"]
            st.session_state.fails = 0
            st.query_params["k"] = AC.token_for(rec["id"])
            st.rerun()
        else:
            st.session_state.fails = st.session_state.get("fails", 0) + 1
            if st.session_state.fails >= 8:
                st.session_state.lock_until = pd.Timestamp.now().timestamp() + 60
                st.session_state.fails = 0
            st.error(why)
    with st.expander("Admin"):
        with st.form("admin_login", border=False):
            pw = st.text_input("Admin password", type="password")
            if st.form_submit_button("Log in as admin"):
                if pw and hmac_eq(pw, ADMIN_PASSWORD):
                    st.session_state.is_admin = True
                    st.session_state.user = {"id": "admin", "label": "Admin"}
                    st.rerun()
                else:
                    st.error("Wrong admin password.")
    st.caption("Information only, not investment advice. Access is by invitation.")


if CODES_ON:
    if not st.session_state.get("user"):
        rec = AC.from_token(st.query_params.get("k"))
        if rec:  # returning visitor with a saved link
            st.session_state.user = {"id": rec["id"], "label": rec["label"]}
            st.session_state.user_hash = rec["hash"]
    if st.session_state.get("user") and not st.session_state.get("is_admin"):
        rec = AC.get(st.session_state.user["id"])  # re-checked on every page load
        if not rec or AC.status(rec) != "Active" or rec["hash"] != st.session_state.get("user_hash"):
            _logout("Your access code is no longer active. Please contact the admin.")
    if not st.session_state.get("user"):
        login_page()
        st.stop()
elif APP_PASSWORD and not st.session_state.get("authed"):
    st.title("📡 IPO Radar")
    pw = st.text_input("Password", type="password")
    if pw:
        if pw == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

IS_ADMIN = bool(st.session_state.get("is_admin"))
USER = st.session_state.get("user") or {"id": "local", "label": "You"}
CAN_EDIT = IS_ADMIN or not CODES_ON  # only the admin curates expert views when codes are on

if PUBLIC_MODE:  # never share one visitor's saved data with another
    st.session_state.setdefault("my_views", pd.DataFrame(columns=["ipo", "source", "rating", "note", "origin", "ts"]))
    st.session_state.setdefault("my_watch", pd.DataFrame(columns=["name", "note", "added"]))


def views_all():
    return st.session_state.my_views if PUBLIC_MODE else X.views()


def view_add(ipo, source, rating, note="", origin="manual"):
    if PUBLIC_MODE:
        v = st.session_state.my_views
        v = v[~((v["ipo"] == ipo) & (v["source"] == source))]
        st.session_state.my_views = pd.concat([v, pd.DataFrame([{"ipo": ipo, "source": source, "rating": rating, "note": note,
                                                                   "origin": origin, "ts": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}])],
                                              ignore_index=True)
    else:
        X.add_view(ipo, source, rating, note, origin)


def view_remove(ipo, source):
    if PUBLIC_MODE:
        v = st.session_state.my_views
        st.session_state.my_views = v[~((v["ipo"] == ipo) & (v["source"] == source))]
    else:
        X.remove_view(ipo, source)


def watch_all():
    if CODES_ON:
        return pd.DataFrame(AC.watchlist(USER["id"]), columns=["name", "note", "added"])
    return st.session_state.my_watch if PUBLIC_MODE else store.watchlist()


def watch_add(name, note=""):
    if CODES_ON:
        items = [w for w in AC.watchlist(USER["id"]) if w["name"] != name]
        items.append({"name": name, "note": note, "added": pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M")})
        AC.watch_set(USER["id"], items)
    elif PUBLIC_MODE:
        w = st.session_state.my_watch
        st.session_state.my_watch = pd.concat([w[w["name"] != name], pd.DataFrame([{"name": name, "note": note,
                                              "added": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}])], ignore_index=True)
    else:
        store.watch_add(name, note)


def watch_remove(name):
    if CODES_ON:
        AC.watch_set(USER["id"], [w for w in AC.watchlist(USER["id"]) if w["name"] != name])
    elif PUBLIC_MODE:
        w = st.session_state.my_watch
        st.session_state.my_watch = w[w["name"] != name]
    else:
        store.watch_remove(name)


STATUS_ORDER = ["Closing Today", "Open", "Upcoming", "Closed", "Listing Today", "Listed"]
VERDICT_ICON = {"Strong signals": "🟢", "Positive": "🟢", "Mixed": "🟡", "Weak": "🔴"}

st.markdown(ui.CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def load_live(_bust: int = 0):
    errors, info = [], {}
    frames = {}
    for key, fn in (("gmp", S.fetch_gmp), ("sub", S.fetch_subscription), ("perf", S.fetch_performance)):
        try:
            df = fn()
            if key == "perf" and date.today().month == 1:
                df = pd.concat([df, S.fetch_performance(date.today().year - 1)], ignore_index=True)
            if df is None or df.empty:
                raise RuntimeError("empty response")
            frames[key] = df
            store.cache_put(key, df)
            info[key] = "live"
        except Exception as e:  # noqa: BLE001
            cached, ts = store.cache_get(key)
            if cached is not None:
                frames[key] = cached
                info[key] = f"cached {ts}"
            errors.append(f"{key}: {e}")
    return frames, errors, info


@st.cache_data(ttl=600, show_spinner=False)
def sheet_frames(source: str, _bust: int = 0):
    return SH.to_frames(SH.load_tabs(source))


def get_data(mode: str, bust: int):
    if mode == "Sheet":
        if not SHEET_URL:
            st.error("DATA_SOURCE is 'sheet' but SHEET_URL is empty. Add your Google Sheet link (or a local .xlsx path) to the settings.")
            st.stop()
        try:
            fr = sheet_frames(SHEET_URL, bust)
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't read your data sheet: {e}")
            st.stop()
        return fr, [], {"source": "your data sheet (facts entered from public sources)"}
    if mode == "Demo snapshot":
        return {"gmp": demo.gmp(), "sub": demo.subscription(), "perf": demo.performance()}, [], {"all": f"demo {demo.SNAPSHOT}"}
    frames, errors, info = load_live(bust)
    if not all(k in frames for k in ("gmp", "sub", "perf")):
        d = {"gmp": demo.gmp(), "sub": demo.subscription(), "perf": demo.performance()}
        for k in d:
            if k not in frames:
                frames[k] = d[k]
                info[k] = f"demo {demo.SNAPSHOT}"
    return frames, errors, info


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📡 IPO Radar")
    if CODES_ON:
        c1, c2 = st.columns([3, 2])
        c1.caption(f"👤 {USER['label']}" + (" (admin)" if IS_ADMIN else ""))
        if c2.button("Log out", width="stretch"):
            _logout()
            st.rerun()
    page = st.radio("View", ["🏠 Home", "📋 All open & upcoming", "📈 Recent listings", "🔍 IPO details",
                             "📚 What history says", "⭐ Watchlist"] + (["🔑 Admin panel"] if IS_ADMIN else []),
                    label_visibility="collapsed")
    page = page.split(" ", 1)[1]
    detailed = st.toggle("Show detailed tables & charts", value=False,
                         help="Off = simple visual view. On = adds full data tables and analyst-style charts.")
    st.divider()
    if SHEET:
        mode = "Sheet"
    else:
        mode = st.radio("Data source", ["Live", "Demo snapshot"], horizontal=True,
                        help="Live pulls InvestorGain / Chittorgarh / Yahoo Finance. Demo is a frozen real snapshot for offline use.")
    if "bust" not in st.session_state:
        st.session_state.bust = 0
    if st.button("🔄 Refresh now", width="stretch"):
        st.session_state.bust += 1
        st.cache_data.clear()
    seg_choice = st.segmented_control("Show", ["Mainboard", "SME", "Both"], default="Both",
                                      help="Mainboard = large companies on NSE/BSE. SME = small companies (higher risk, bigger minimum investment).")
    seg_filter = ["Mainboard", "SME"] if seg_choice in (None, "Both") else [seg_choice]
    days_back = st.slider("'Recently listed' window (days)", 7, 90, 30)
    use_news = False
    api_key = ""
    if not SHEET:
        use_news = st.toggle("Read expert views from news", value=True,
                             help="Scans news headlines (Google News / Bing News) for brokerage 'subscribe / avoid' calls on mainboard IPOs.")
    if not PUBLIC_MODE and CAN_EDIT:
        with st.expander("AI summary (optional)"):
            api_key = st.text_input("Anthropic API key", type="password", value=str(setting("ANTHROPIC_API_KEY", "") or ""))
            st.caption("Used only for the 'AI analyst note' in IPO details. Stored in memory for this session.")

with st.spinner("Fetching IPO data…"):
    frames, errors, info = get_data(mode, st.session_state.bust)

gmp_df, sub_df, perf_df = frames["gmp"], frames["sub"], frames["perf"]
sub_hist_all = frames.get("sub_hist", pd.DataFrame())
sheet_fund = frames.get("fund", {})
live = A.merge_live(gmp_df, sub_df)
if not live.empty:
    live = live.drop_duplicates(subset=["name"], keep="first").reset_index(drop=True)
rates = A.base_rates(perf_df)
live = A.quick_scores(live, rates)
if mode == "Live" and info.get("gmp") == "live":
    store.save_snapshot(live)


@st.cache_data(ttl=3600, show_spinner=False)
def nifty_hist(_bust: int = 0):
    return S.fetch_nifty(pd.Timestamp.today() - pd.Timedelta(days=120))


@st.cache_data(ttl=3600, show_spinner=False)
def news_for(names: tuple, _bust: int = 0):
    return X.fetch_news_many(list(names))


nifty = nifty_hist(st.session_state.bust) if mode == "Live" else None
mood = A.market_mood(perf_df, nifty)
active = live[live["status"].isin(["Open", "Closing Today", "Upcoming"])] if not live.empty else live
if mode == "Demo snapshot":
    news_map = {n: demo.expert_news(n) for n in active["name"]}
    stored_all = pd.concat([demo.expert_views(n) for n in active["name"]] + [views_all()], ignore_index=True)
else:
    names = tuple(sorted(active[active["category"] == "Mainboard"]["name"])) if use_news and not active.empty else ()
    with st.spinner("Reading expert views…"):
        news_map = news_for(names, st.session_state.bust) if names else {}
    stored_all = views_all()


def expert_state(name):
    nw = news_map.get(name)
    sv = stored_all[stored_all["ipo"] == name] if not stored_all.empty else stored_all
    return nw, sv, X.consensus(nw, sv)


if not live.empty:
    recs = []
    for _, r in live.iterrows():
        _, _, cons = expert_state(r["name"])
        rec = A.recommend(r, A.evaluate(r, None, rates), cons, mood)
        recs.append({"call": rec["call"], "call_icon": rec["icon"], "call_color": rec["color"], "final": rec["final"],
                     "expert_label": cons["label"] if cons["n"] else None, "expert_n": cons["n"]})
    live = pd.concat([live.reset_index(drop=True), pd.DataFrame(recs)], axis=1)
    if PUBLIC_MODE:  # information only: no buy/avoid calls or verdicts
        live["call"] = None
        live["verdict"] = None
        live["expert_label"] = None

live_f = live[live["category"].isin(seg_filter)] if not live.empty else live
perf_f = perf_df[perf_df["category"].isin(seg_filter)] if not perf_df.empty else perf_df
cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=days_back)
recent = perf_f[perf_f["listing_date"] >= cutoff].sort_values("listing_date", ascending=False) if not perf_f.empty else perf_f

with st.sidebar:
    st.divider()
    src = ", ".join(f"{k}: {v}" for k, v in info.items())
    st.caption(f"Data: {src}")
    if errors and mode == "Live":
        with st.expander("⚠️ Fetch issues"):
            st.write("\n".join(f"- {e}" for e in errors))
            st.caption("Falling back to last cached or demo data. Sites occasionally change their layout/API; see README → Troubleshooting.")
    st.caption("Information only, not advice. Read the RHP and consult a SEBI-registered adviser before investing."
               + ("" if SHEET else " GMP is unofficial grey-market data."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmt_dt(x):
    return "" if x is None or pd.isna(x) else pd.Timestamp(x).strftime("%d %b")


def table_cfg():
    cc = st.column_config
    return {
        "name": cc.TextColumn("IPO", width="medium"),
        "category": cc.TextColumn("Segment"),
        "status": cc.TextColumn("Status"),
        "verdict_lbl": cc.TextColumn("Signal"),
        "score": cc.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
        "gmp": cc.NumberColumn("GMP ₹", format="%.2f"),
        "gmp_pct": cc.NumberColumn("GMP %", format="%.1f%%"),
        "price": cc.NumberColumn("Price ₹", format="%.0f"),
        "issue_size_cr": cc.NumberColumn("Size ₹Cr", format="%.1f"),
        "lot": cc.NumberColumn("Lot", format="%d"),
        "min_invest": cc.NumberColumn("1-lot ₹", format="₹%.0f"),
        "gain_per_lot": cc.NumberColumn("GMP gain/lot ₹", format="₹%.0f"),
        "sub_total": cc.NumberColumn("Sub total x", format="%.2f"),
        "sub_qib": cc.NumberColumn("QIB x", format="%.2f"),
        "sub_nii": cc.NumberColumn("NII x", format="%.2f"),
        "sub_retail": cc.NumberColumn("Retail x", format="%.2f"),
        "retail_odds": cc.NumberColumn("Retail allot. odds", format="percent"),
        "open": cc.DateColumn("Opens", format="DD MMM"),
        "close": cc.DateColumn("Closes", format="DD MMM"),
        "allotment": cc.DateColumn("Allotment", format="DD MMM"),
        "listing": cc.DateColumn("Listing", format="DD MMM"),
        "pe": cc.NumberColumn("P/E", format="%.1f"),
        "listing_date": cc.DateColumn("Listed", format="DD MMM YY"),
        "listing_gain_pct": cc.NumberColumn("Listing gain %", format="%.1f%%"),
        "listing_close_gain_pct": cc.NumberColumn("Day-1 close %", format="%.1f%%"),
        "ltp": cc.NumberColumn("Now ₹", format="%.2f"),
        "ltp_gain_pct": cc.NumberColumn("Now vs issue %", format="%.1f%%"),
        "gmp_error_pct": cc.NumberColumn("Actual − GMP (pp)", format="%+.1f"),
        "beat_gmp": cc.CheckboxColumn("Met GMP est."),
        "anchor": cc.CheckboxColumn("Anchor"),
    }


def with_verdict(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["verdict_lbl"] = d["verdict"].map(lambda v: f"{VERDICT_ICON.get(v, '')} {v}")
    return d


def sort_status(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["_o"] = d["status"].map({s: i for i, s in enumerate(STATUS_ORDER)}).fillna(9)
    return d.sort_values(["_o", "score"], ascending=[True, False]).drop(columns="_o")


def html(x: str):
    st.markdown(x, unsafe_allow_html=True)


def show_chart(fig, key=None, quiet=False):
    if fig is None:
        if not quiet:
            st.info("Not enough data for this chart yet.")
    else:
        st.plotly_chart(fig, width="stretch", theme="streamlit", key=key)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
if PUBLIC_MODE:
    html('<div class="ir-card" style="border-left:5px solid #fab219;padding:8px 14px;margin-bottom:10px;font-size:.85rem">'
         '<b>For information and education only. This is not investment advice.</b> IPO Radar is not registered with SEBI and does not '
         'recommend buying or avoiding any security. '
         + ('Facts are compiled manually from public sources (company offer documents / RHPs, stock-exchange announcements and news reports) '
            'and linked on each IPO. No third-party database is copied, and grey-market premium (GMP) is not shown. Figures may contain errors '
            'or be out of date: always verify with the RHP and consult a SEBI-registered adviser.</div>' if SHEET else
            'GMP is unofficial grey-market data. Data is compiled from public sources (InvestorGain, Chittorgarh, Yahoo Finance, news sites); '
            'always verify with the RHP and consult a SEBI-registered adviser.</div>'))

CALL_RANK = {"Apply": 0, "Apply for long term": 1, "Apply for listing gains": 2, "Wait – decide on last day": 3, "Avoid": 4, "Closed": 5}


def apply_now(df):
    d = df[df["status"].isin(["Closing Today", "Open"])]
    return sort_status(d)


def by_call(df):
    d = df.copy()
    d["_r"] = d["call"].map(CALL_RANK).fillna(9) if "call" in d else 9
    return d.sort_values(["_r", "final"], ascending=[True, False]).drop(columns="_r")


if page == "Home":
    st.title("IPO Radar")
    st.caption(f"Updated {pd.Timestamp.now():%d %b %Y, %H:%M}. Signals, not advice: always read the RHP.")
    n = lambda s: int((live_f["status"] == s).sum()) if not live_f.empty else 0  # noqa: E731
    up = int((recent["listing_gain_pct"] > 0).sum()) if not recent.empty else 0
    html(ui.kpis([
        ("Open to apply now", str(n("Open") + n("Closing Today")), None),
        ("Last day today", str(n("Closing Today")), ui.BAD if n("Closing Today") else None),
        ("Coming soon", str(n("Upcoming")), None),
        (f"Listed in last {days_back} days: went up", f"{up} of {len(recent)}", ui.GOOD if len(recent) and up / len(recent) >= .5 else ui.BAD),
        ("Avg listing gain (same period)", f"{recent['listing_gain_pct'].mean():+.1f}%" if not recent.empty else "—", None),
    ]))

    html(ui.mood_banner(mood))
    st.subheader("🗓 This week")
    html(ui.week_strip(live_f))

    st.subheader("🟢 Open now" if PUBLIC_MODE else "🟢 Open now: our top picks")
    now = apply_now(live_f)
    if now.empty:
        st.info("No IPOs open right now.")
    else:
        top = (sort_status(now) if PUBLIC_MODE else by_call(now)).head(6)
        html(ui.card_grid(top))
        if len(now) > 6:
            st.caption(f"{len(now) - 6} more IPOs are open. See **📋 All open & upcoming**.")

    a, b = st.columns(2)
    with a:
        if SHEET:
            show_chart(C.subscription_compare(live_f[live_f["status"].isin(["Open", "Closing Today", "Closed"])]), "eg")
        else:
            show_chart(C.expected_gain(live_f[live_f["status"].isin(["Open", "Closing Today", "Upcoming"])]), "eg")
    with b:
        show_chart(C.winners_losers(recent, 5), "wl")

    soon = sort_status(live_f[live_f["status"] == "Upcoming"])
    if not soon.empty:
        st.subheader("🔜 Coming soon")
        html(ui.card_grid(by_call(soon).head(3)))
        if len(soon) > 3:
            st.caption(f"{len(soon) - 3} more upcoming IPOs are on the **📋 All open & upcoming** page.")

    if detailed:
        st.subheader("Full table")
        act = sort_status(with_verdict(live_f[live_f["status"].isin(["Open", "Closing Today", "Upcoming"])]))
        cols = ["name", "category", "status", "verdict_lbl", "score", "gmp_pct", "sub_total", "sub_qib", "sub_retail",
                "retail_odds", "price", "min_invest", "gain_per_lot", "close", "listing"]
        st.dataframe(act[cols], column_config=table_cfg(), hide_index=True, width="stretch")
        show_chart(C.timeline(live_f[live_f["status"].isin(["Open", "Closing Today", "Upcoming", "Closed"])]), "tl")

    with st.expander("How to read the cards"):
        if not PUBLIC_MODE:
            st.markdown("""- **The call** (✅ Apply · ☑️ Apply for listing gains · ✅ Apply for long term · ⏳ Wait, decide on last day · ⛔ Avoid) combines the signal score, **expert views** (brokerage calls found in the news plus any you add) and the **IPO market mood**. Open "IPO details" to see the reasons.
- **Signal** (0–100) combines grey-market premium, demand, fundamentals and valuation.""")
        if not SHEET:
            st.markdown("- **Expected listing gain** is the grey-market premium (GMP) as % of the issue price. It's unofficial and often wrong by several %.")
        st.markdown("""
- **Times subscribed**: 10x means bids for 10 times the shares on offer.
- **Bars**: *Institutions* (QIB) are mutual funds and FIIs, the most informed money, and usually bid on the last day. *HNIs* are wealthy individuals. *Retail* is investments up to ₹2 L.
- **Your allotment chance** ≈ 1 ÷ retail subscription (lottery for one lot).
""")

elif page == "All open & upcoming":
    st.title("All open & upcoming IPOs")
    stat = st.segmented_control("Status", ["Closing Today", "Open", "Upcoming", "Closed"], selection_mode="multi",
                                default=["Closing Today", "Open", "Upcoming"])
    sort_by = st.segmented_control("Sort by", ["Our call", "Deadline", "Expected gain"], default="Our call")
    d = live_f[live_f["status"].isin(stat or [])]
    if d.empty:
        st.info("Nothing matches.")
    else:
        if sort_by == "Our call":
            d = by_call(d)
        elif sort_by == "Expected gain":
            d = d.sort_values("gmp_pct", ascending=False, na_position="last")
        else:
            d = sort_status(d)
        html(ui.card_grid(d))
        st.subheader("Who is bidding? Pick an IPO")
        pick = st.selectbox("IPO", d["name"].tolist(), label_visibility="collapsed")
        row = d[d["name"] == pick].iloc[0]
        show_chart(C.who_is_bidding(row, f"{pick}: who is bidding?"), "wib")
        if detailed:
            dd = with_verdict(d)
            cols = ["name", "category", "status", "call", "final", "expert_label", "verdict_lbl", "score", "gmp", "gmp_pct", "price", "issue_size_cr", "lot",
                    "min_invest", "gain_per_lot", "sub_total", "sub_qib", "sub_nii", "sub_retail", "retail_odds", "pe",
                    "anchor", "open", "close", "allotment", "listing"]
            st.dataframe(dd[cols], column_config=table_cfg(), hide_index=True, width="stretch")
            show_chart(C.subscription_bars(row, f"{pick}: subscription by category (incl. small / big HNI)"), "sb")
            show_chart(C.subscription_compare(d), "sc")
        st.download_button("⬇ Download as CSV (opens in Excel)", d.to_csv(index=False), "ipos.csv")

elif page == "Recent listings":
    st.title(f"How recent IPOs did (last {days_back} days)")
    if recent.empty:
        st.info("No listings in this window.")
    else:
        up = int((recent["listing_gain_pct"] > 0).sum())
        below = int((recent["ltp_gain_pct"] < 0).sum())
        html(ui.kpis([
            ("IPOs listed", str(len(recent)), None),
            ("Listed above issue price", f"{up} ({up / len(recent) * 100:.0f}%)", ui.GOOD),
            ("Average listing-day gain", f"{recent['listing_gain_pct'].mean():+.1f}%", None),
            ("Average return today", f"{recent['ltp_gain_pct'].mean():+.1f}%", None),
            ("Trading below issue price now", str(below), ui.BAD if below else None),
        ]))
        show_chart(C.winners_losers(recent, 8), "wl2")
        if not SHEET:
            st.subheader("Price chart since listing")
            pick = st.selectbox("IPO", recent["name"].tolist())
            row = recent[recent["name"] == pick].iloc[0]
            indexed = st.toggle("Compare with NIFTY 50", value=False)
            if mode == "Demo snapshot":
                st.info("Price charts need Live mode (Yahoo Finance).")
            else:
                with st.spinner("Loading prices…"):
                    h = S.fetch_price_history(row["nse_symbol"], row["bse_code"], row["listing_date"])
                    nifty = S.fetch_nifty(row["listing_date"] - pd.Timedelta(days=3)) if indexed else None
                if h.empty:
                    st.warning("No price history found on Yahoo Finance for this symbol (common for fresh SME listings).")
                else:
                    show_chart(C.price_since_listing(h, row["price"], pick, nifty, indexed), "psl")
        if detailed:
            st.subheader("Full table")
            st.dataframe(recent[["name", "category", "listing_date", "issue_size_cr", "sub_total", "price", "gmp_pct",
                                 "listing_gain_pct", "listing_close_gain_pct", "ltp", "ltp_gain_pct", "gmp_error_pct", "beat_gmp"]],
                         column_config=table_cfg(), hide_index=True, width="stretch")
            show_chart(C.listing_bars(recent), "lb")

elif page == "IPO details":
    names = sort_status(live_f)["name"].tolist() + [n for n in perf_f["name"].tolist() if n not in set(live_f["name"])]
    if not names:
        st.stop()
    pick = st.selectbox("Choose an IPO", names)
    is_live = pick in set(live_f["name"])
    row = live_f[live_f["name"] == pick].iloc[0] if is_live else perf_f[perf_f["name"] == pick].iloc[0]

    hist = pd.DataFrame()
    if SHEET:
        pass  # no GMP in the sheet edition
    elif mode == "Demo snapshot":
        hist = demo.gmp_history(pick)
    elif row.get("ig_url"):
        try:
            hist = S.fetch_gmp_history(row["ig_url"])
        except Exception:  # noqa: BLE001
            hist = pd.DataFrame()
    if hist.empty and not SHEET:
        h2 = store.history(pick)
        if not h2.empty:
            hist = h2[["ts", "gmp"]].dropna()

    fkey = f"fund::{pick}"
    fund = sheet_fund.get(pick) if SHEET else st.session_state.get(fkey)
    ev = A.evaluate(row, fund, rates, hist if not hist.empty else None)
    odds = A.allotment_odds(row)
    nw, sv, cons = expert_state(pick)
    if nw is None and mode == "Live" and use_news and is_live:
        with st.spinner("Reading expert views…"):
            nw = news_for((pick,), st.session_state.bust).get(pick)
        cons = X.consensus(nw, sv)
    rec = A.recommend(row, ev, cons, mood)

    st.title(pick)
    html(f'<div class="ir-sub" style="font-size:.9rem"><span class="ir-pill">{ui.e(row.get("category"))}</span>'
         + " · ".join(f"{lbl} <b>{fmt_dt(row.get(k))}</b>" for lbl, k in (("Opens", "open"), ("Closes", "close"), ("Allotment", "allotment"), ("Listing", "listing")) if row.get(k) is not None and pd.notna(row.get(k)))
         + "</div>")
    if is_live and not PUBLIC_MODE:
        html(ui.call_panel(rec, cons))
    st.write("")
    a, b = st.columns([1, 1.3])
    with a:
      if not PUBLIC_MODE:
        html(ui.meter(ev["score"], ev["verdict"]))
        missing = set()
        if not fund:
            missing.add("Fundamentals")
        if pd.isna(row.get("gmp_pct")) if "gmp_pct" in row else True:
            missing.add("Grey market (GMP)")
        if pd.isna(row.get("sub_qib")) if "sub_qib" in row else True:
            missing.add("Institutional demand (QIB)")
        early = row.get("status") in ("Open", "Upcoming")
        if (pd.isna(row.get("sub_total")) if "sub_total" in row else True) or (early and row.get("sub_total", 0) < 1):
            missing.add("Overall demand")
        if early and pd.notna(row.get("sub_qib")) and row.get("sub_qib") < 1:
            missing.add("Institutional demand (QIB)")
        html(ui.lights(ev["components"], missing))
        st.caption(f"Data confidence: {ev['confidence']}" + ("" if fund else " (load fundamentals below for a fuller picture)"))
      else:
        anc = row.get("anchor")
        html(ui.kpis([
            ("Issue size", f"₹{row['issue_size_cr']:,.0f} Cr" if pd.notna(row.get("issue_size_cr")) else "—", None),
            ("Anchor investors", "Yes" if anc is True or anc == 1 else "No" if anc is False or anc == 0 else "—", None),
            ("Listing on", str(row.get("exchange") or "—") if isinstance(row.get("exchange"), str) else "—", None),
        ]))
    with b:
        gp = row.get("gmp_pct")
        if SHEET:
            lo, hi = row.get("price_low"), row.get("price")
            html(ui.kpis([
                ("Price band", f"₹{lo:g}–{hi:g}" if pd.notna(lo) and pd.notna(hi) else (f"₹{hi:g}" if pd.notna(hi) else "—"), None),
                ("Lot size", f"{row['lot']:,.0f} shares" if pd.notna(row.get("lot")) else "—", None),
                ("Minimum investment", ui.fmt_inr(odds["application_amt"]), None),
                ("Your allotment chance", f"{odds['odds'] * 100:.0f}%" if odds["odds"] is not None else "—", None),
                ("Times subscribed", f"{row['sub_total']:,.1f}x" if pd.notna(row.get("sub_total")) else "—", None),
                ("Institutions (QIB)", f"{row['sub_qib']:,.1f}x" if pd.notna(row.get("sub_qib")) else "—", None),
            ]))
        else:
          html(ui.kpis([
            ("Price per share", f"₹{row['price']:g}" if pd.notna(row.get("price")) else "—", None),
            ("Expected listing gain", f"{gp:+.1f}%" if pd.notna(gp) else "—", ui.GOOD if pd.notna(gp) and gp >= 15 else ui.BAD if pd.notna(gp) and gp <= 0 else None),
            ("Minimum investment", ui.fmt_inr(odds["application_amt"]), None),
            ("Your allotment chance", f"{odds['odds'] * 100:.0f}%" if odds["odds"] is not None else "—", None),
            ("Expected gain per application", ui.fmt_inr(odds["expected_value"]) if odds["expected_value"] is not None else "—", None),
            ("Times subscribed", f"{row['sub_total']:,.1f}x" if pd.notna(row.get("sub_total")) else "—", None),
        ]))

    a, b = st.columns(2)
    with a:
        html(ui.bullet_box("✅ Positives observed" if PUBLIC_MODE else "✅ Reasons to consider", ev["pros"], ui.GOOD, "Nothing stands out from the available data."))
    with b:
        html(ui.bullet_box("⚠️ Concerns observed" if PUBLIC_MODE else "⚠️ Risks / red flags", ev["cons"], ui.BAD, "No red flags from the available data."))
    if ev["notes"]:
        html(ui.bullet_box("ℹ️ Good to know", ev["notes"], ui.INFO, ""))

    a, b = st.columns(2)
    with a:
        show_chart(C.who_is_bidding(row) if is_live else None, "wib2", quiet=True)
    with b:
        if SHEET:
            sh = sub_hist_all[sub_hist_all["name"] == pick] if not sub_hist_all.empty else sub_hist_all
            show_chart(C.subscription_buildup(sh), "sbu", quiet=True)
            html(f'<a href="https://www.investorgain.com/report/ipo-gmp-live/331/" target="_blank">Check grey-market premium (GMP) on InvestorGain ↗</a>'
                 '<div class="ir-sub">GMP is unofficial and not shown here.</div>')
        elif hist.empty:
            st.caption("GMP history appears here in Live mode, and builds up from the app's own snapshots.")
        else:
            show_chart(C.gmp_trend(hist, row.get("price"), "Is the grey-market premium rising or falling?"), "gt")

    if SHEET:
        st.subheader("📰 News & reviews")
        q = pick.replace(" ", "+") + "+IPO+review"
        html(f'<a href="https://news.google.com/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en" target="_blank">Search news and brokerage reviews for {ui.e(pick)} ↗</a>'
             '<div class="ir-sub">Opens Google News. Read the analysts\' reasoning in full at the source.</div>')
    if not SHEET:
        st.subheader("🧑‍💼 What experts say")
        if not PUBLIC_MODE:
            html(ui.consensus_bar(cons))
        else:
            st.caption("Headlines from news sites. Read the full article for each brokerage's reasoning.")
        a, b = st.columns([1.3, 1])
        with a:
            st.markdown("**From the news**")
            if nw is not None and not nw.empty:
                html(ui.headline_list(nw))
                st.caption("Headlines are auto-tagged from their wording; 'info' ones state no view and aren't counted. Open the article to confirm.")
            else:
                st.caption("No review headlines found (common for SME IPOs, or before the issue opens)." if mode == "Live" or not use_news
                           else "News scan works in Live mode.")
            if api_key and nw is not None and not nw.empty:
                if st.button("🤖 Let AI read the articles and extract each brokerage's call"):
                    with st.spinner("Reading articles…"):
                        try:
                            found = X.ai_extract(api_key, pick, nw)
                            for f in found:
                                view_add(pick, f["source"], f["rating"], f.get("reason", ""), origin="ai")
                            st.success(f"Added {len(found)} brokerage call(s).")
                            st.rerun()
                        except Exception as ex:  # noqa: BLE001
                            st.error(f"AI extraction failed: {ex}")
        with b:
            st.markdown("**Brokerage / analyst calls**")
            if sv is not None and not sv.empty:
                for _, v in sv.iterrows():
                    col = ui.RATING_COLOR.get(v["rating"], ui.INFO)
                    html(f'<div style="padding:6px 0;border-bottom:1px solid rgba(127,127,127,.15)">'
                         f'<span class="ir-chip" style="background:{col}22">{ui.e(v["rating"])}</span> <b>{ui.e(v["source"])}</b>'
                         f'<div class="ir-sub">{ui.e(v.get("note") or "")} · {ui.e(v.get("origin") or "")}</div></div>')
            else:
                st.caption("None saved yet." + (" Add calls you read (e.g. from your broker's research note)." if CAN_EDIT else ""))
            if not PUBLIC_MODE and CAN_EDIT:
                with st.form(f"add_view::{pick}", clear_on_submit=True):
                    c1, c2 = st.columns([1.2, 1])
                    src = c1.text_input("Brokerage / analyst", placeholder="e.g. SBI Securities")
                    rt = c2.selectbox("Their call", X.RATINGS)
                    nt = st.text_input("Reason (optional)")
                    if st.form_submit_button("➕ Add expert view") and src.strip():
                        view_add(pick, src, rt, nt)
                        st.rerun()
            mine = sv[sv["origin"].isin(["manual", "ai"])] if sv is not None and not sv.empty else sv
            if CAN_EDIT and mine is not None and not mine.empty:
                rm = st.selectbox("Remove a saved view", [""] + mine["source"].tolist(), key=f"rmv::{pick}")
                if rm and st.button("Remove", key=f"rmb::{pick}"):
                    view_remove(pick, rm)
                    st.rerun()
    html(ui.mood_banner(mood))

    st.subheader("📑 Company fundamentals")
    if not fund and SHEET:
        st.caption("No financials entered for this IPO yet (Financials tab of the data sheet).")
    elif not fund:
        c1, c2 = st.columns([3, 1])
        cu = c1.text_input("Chittorgarh page URL (optional, auto-detected)", key=f"cu::{pick}",
                           placeholder="https://www.chittorgarh.com/ipo/<name>-ipo/<id>/", label_visibility="collapsed")
        if c2.button("Load fundamentals", disabled=mode == "Demo snapshot", width="stretch", type="primary"):
            with st.spinner("Fetching…"):
                url = cu.strip() or S.find_chittorgarh_url(row.get("ig_url"))
                if not url:
                    st.error("Couldn't find the Chittorgarh page automatically. Search the IPO on chittorgarh.com and paste its URL in the box.")
                else:
                    try:
                        st.session_state[fkey] = S.fetch_fundamentals(url)
                        st.rerun()
                    except Exception as ex:  # noqa: BLE001
                        st.error(f"Could not read {url}: {ex}")
        st.caption("Loads revenue, profit, debt, valuation and promoter holding, and updates the score." +
                   (" Needs Live mode." if mode == "Demo snapshot" else ""))
    else:
        fv = ev["fundamentals"]

        def tone(v, good, bad, higher_better=True):
            if v is None or pd.isna(v):
                return None
            if higher_better:
                return ui.GOOD if v >= good else ui.BAD if v < bad else None
            return ui.GOOD if v <= good else ui.BAD if v > bad else None

        fmt = lambda v, s="": f"{v:.1f}{s}" if v is not None and not pd.isna(v) else "—"  # noqa: E731
        html(ui.kpis([
            ("Revenue growth / yr", fmt(fv.get("rev_cagr"), "%"), tone(fv.get("rev_cagr"), 15, 5)),
            ("Profit growth / yr", fmt(fv.get("pat_cagr"), "%"), tone(fv.get("pat_cagr"), 20, 5)),
            ("Return on equity", fmt(fv.get("roe"), "%"), tone(fv.get("roe"), 15, 8)),
            ("Debt to equity", fmt(fv.get("de")), tone(fv.get("de"), 0.3, 1.0, False)),
            ("P/E (valuation)", fmt(fv.get("pe_post"), "x"), tone(fv.get("pe_post"), 15, 40, False)),
            ("Promoters keep", fmt(fv.get("promoter_post"), "%"), tone(fv.get("promoter_post"), 60, 50)),
        ]))
        st.caption("Green = healthy, red = concern, no colour = in between.")
        a, b = st.columns([1.2, 1])
        with a:
            show_chart(C.revenue_profit(fund.get("financials")), "rp", quiet=bool(SHEET))
            if SHEET and fund.get("financials") is None:
                st.caption("No financials entered yet for this IPO.")
        with b:
            if fund.get("objects") is not None:
                st.markdown("**What the money will be used for**")
                st.dataframe(fund["objects"], hide_index=True, width="stretch")
            extra = []
            if fv.get("sale_type"):
                extra.append(f"**Issue type:** {fv['sale_type']}")
            if fv.get("ofs_share") is not None:
                extra.append(f"**Goes to selling shareholders (OFS):** {fv['ofs_share']:.0f}%")
            if fund.get("promoters"):
                extra.append(f"**Promoters:** {fund['promoters']}")
            if extra:
                st.markdown("  \n".join(extra))
        if detailed:
            show_chart(C.financials_bars(fund.get("financials")), "fin")
            if fund.get("reservation") is not None:
                st.dataframe(fund["reservation"], hide_index=True, width="stretch")
            if fund.get("reco") is not None:
                st.markdown("**Broker / member recommendations (Chittorgarh)**")
                st.dataframe(fund["reco"], hide_index=True, width="stretch")
        if fund.get("about"):
            with st.expander("About the company"):
                st.write(fund["about"])
        if fund.get("url"):
            st.caption(f"Source: {fund['url']}")

    if detailed:
        show_chart(C.score_breakdown(ev["components"], ev["penalty"]), "sbd")
        show_chart(C.subscription_bars(row) if is_live else None, "sbr", quiet=True)

    if not PUBLIC_MODE:
      with st.expander("🤖 AI analyst note (optional)"):
          if not api_key:
              st.caption("Add an Anthropic API key in the sidebar to generate a written summary from the data above.")
          elif st.button("Generate AI note"):
              payload = {"ipo": {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in row.to_dict().items()},
                         "rule_based": {k: ev[k] for k in ("score", "verdict", "pros", "cons", "notes")},
                         "radar_call": {k: rec[k] for k in ("call", "final", "confidence", "why")},
                         "expert_consensus": cons,
                         "expert_views": sv.to_dict("records") if sv is not None else [],
                         "news_headlines": nw[["title", "source", "rating"]].to_dict("records") if nw is not None and not nw.empty else [],
                         "market_mood": {k: mood.get(k) for k in ("label", "bullets")},
                         "fundamentals": ev["fundamentals"],
                         "financials": fund["financials"].to_dict() if fund and fund.get("financials") is not None else None}
              with st.spinner("Thinking…"):
                  try:
                      st.markdown(A.ai_summary(api_key, pick, payload))
                  except Exception as ex:  # noqa: BLE001
                      st.error(f"AI call failed: {ex}")

    rhp = row.get("rhp_link") if isinstance(row.get("rhp_link"), str) and row.get("rhp_link", "").startswith("http") else None
    links = [f"[Offer document (RHP)]({rhp})" if rhp else None,
             f"[InvestorGain]({row['ig_url']})" if row.get("ig_url") else None,
             f"[Chittorgarh]({fund['url']})" if fund and not fund.get("from_sheet") and fund.get("url") else None,
             "[NSE issue info](https://www.nseindia.com/market-data/all-upcoming-issues-ipo)"]
    st.markdown("**Verify at source:** " + " · ".join(x for x in links if x))
    wc1, wc2 = st.columns([3, 1])
    note = wc1.text_input("Note for watchlist", key=f"note::{pick}", placeholder="Your note (optional)", label_visibility="collapsed")
    if wc2.button("⭐ Add to watchlist", width="stretch"):
        watch_add(pick, note)
        st.success("Added to watchlist.")

elif page == "What history says":
    st.title("What history says")
    st.caption(f"Based on {len(perf_f)} listed IPOs" + (" in your data sheet." if SHEET else " this year.")
               + " Use this to judge how far to trust " + ("subscription numbers." if SHEET else "GMP and subscription numbers."))
    rel = A.gmp_reliability(perf_f) if not SHEET else {}
    br = A.base_rates(perf_f)
    if rel:
        html(ui.kpis([
            ("GMP got the direction right (up vs down)", f"{rel['direction_hit']:.0f}%", None),
            ("Listing within ±10% of the GMP estimate", f"{rel['pct_within_10']:.0f}%", None),
            ("Typical miss vs GMP estimate", f"{rel['mae']:.0f} pts", None),
        ]))
    if br:
        if SHEET:
            show_chart(C.hit_rate(br["sub_bucket"], "Times subscribed"), "hr2")
        else:
            a, b = st.columns(2)
            with a:
                show_chart(C.hit_rate(br["gmp_bucket"], "GMP band"), "hr1")
            with b:
                show_chart(C.hit_rate(br["sub_bucket"], "Times subscribed"), "hr2")
        tips = []
        gb = br.get("gmp_bucket")
        hi = [i for i in ("25–50%", "50%+") if gb is not None and i in gb.index]
        if hi and not SHEET:
            tips.append(f"IPOs with GMP above 25% listed higher in {gb.loc[hi, '% listed positive'].mean():.0f}% of cases.")
            if "% listed ≥ GMP estimate" in gb:
                tips.append(f"Only {gb['% listed ≥ GMP estimate'].mean():.0f}% of IPOs (avg across bands) actually reached their GMP estimate, so treat GMP as an optimistic guide.")
        sb = br.get("sub_bucket")
        if sb is not None and not sb.empty and len(sb) >= 2:
            lo_b, hi_b = sb.index[0], sb.index[-1]
            tips.append(f"Subscribed {lo_b}: {sb.loc[lo_b, '% listed positive']:.0f}% listed above issue price; "
                        f"subscribed {hi_b}: {sb.loc[hi_b, '% listed positive']:.0f}%.")
        seg = br["by_segment"]
        for nm in ("Mainboard", "SME"):
            if nm in seg.index:
                r_ = seg.loc[nm]
                tips.append(f"{nm} IPOs: {r_['% listed positive']:.0f}% listed above issue price; average return since listing "
                            f"{r_['Avg gain now (LTP) %']:+.0f}% (n={int(r_['IPOs'])}).")
        if tips:
            html(ui.bullet_box("💡 Takeaways", tips, ui.INFO, ""))
        if SHEET and len(perf_f) < 10:
            st.caption("These patterns get more reliable as you add more listed IPOs to the Listing tab.")
    if detailed and not SHEET:
        show_chart(C.gmp_vs_actual(perf_f, rel), "gva")
        if br:
            st.dataframe(br["gmp_bucket"], width="stretch")
            st.dataframe(br["sub_bucket"], width="stretch")
            st.dataframe(br["by_segment"], width="stretch")
    h = store.history()
    if not h.empty:
        st.subheader("GMP recorded by this app")
        pick = st.selectbox("IPO", sorted(h["name"].unique()))
        show_chart(C.gmp_trend(h[h["name"] == pick][["ts", "gmp"]].dropna(), None, f"{pick}: recorded GMP"), "lh")

elif page == "Watchlist":
    st.title("⭐ Watchlist")
    w = watch_all()
    if w.empty:
        st.info("Add IPOs from the 'IPO details' page.")
    else:
        wl = live[live["name"].isin(w["name"])]
        if not wl.empty:
            html(ui.card_grid(sort_status(wl)))
        merged = w.merge(live[["name", "status", "score", "verdict", "gmp_pct", "sub_total", "close", "listing"]], on="name", how="left")
        st.dataframe(merged, column_config=table_cfg(), hide_index=True, width="stretch")
        rm = st.selectbox("Remove", [""] + w["name"].tolist())
        if rm and st.button("Remove"):
            watch_remove(rm)
            st.rerun()

elif page == "Admin panel" and IS_ADMIN:
    st.title("🔑 Admin panel")
    ok_store, store_msg = persist.check()
    if persist.backend() == "local" and not ok_store:
        st.error(store_msg)
    elif persist.backend() == "local":
        st.warning("**Storage: local files.** Fine on your own PC. On Streamlit Cloud, codes would be wiped whenever the app restarts, "
                   "so connect a GitHub Gist (see DEPLOY.md → steps 2–3).")
    elif ok_store:
        st.success(f"**Storage:** {store_msg}")
    else:
        st.error(store_msg)

    codes = AC.all_codes()
    df = pd.DataFrame(codes)
    if not df.empty:
        df["status"] = [AC.status(r) for r in codes]
        today = pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d")
        html(ui.kpis([
            ("Active codes", str(int((df["status"] == "Active").sum())), ui.GOOD),
            ("Revoked / expired", str(int((df["status"] != "Active").sum())), None),
            ("Logged in today", str(int(df["last_login"].fillna("").astype(str).str.startswith(today).sum())), None),
            ("Total logins", str(int(pd.to_numeric(df["logins"], errors="coerce").fillna(0).sum())), None),
        ]))

    # ---- create codes
    st.subheader("➕ Create access codes")
    with st.form("gen_codes", clear_on_submit=False):
        c1, c2, c3 = st.columns([2, 1, 1.4])
        label = c1.text_input("Name / who it's for", placeholder="e.g. Ravi Sharma")
        count = c2.number_input("How many", min_value=1, max_value=50, value=1, step=1)
        validity = c3.selectbox("Valid for", ["No expiry", "7 days", "30 days", "90 days", "1 year", "Until a date…"])
        c4, c5 = st.columns([1, 2])
        until = c4.date_input("Until (if chosen)", value=pd.Timestamp.today() + pd.Timedelta(days=30), format="DD/MM/YYYY")
        note = c5.text_input("Note (optional)", placeholder="e.g. WhatsApp group, trial")
        make = st.form_submit_button("Create", type="primary")
    if make:
        if not label.strip():
            st.error("Please enter a name.")
        else:
            days = {"7 days": 7, "30 days": 30, "90 days": 90, "1 year": 365}.get(validity)
            made = AC.create_many(label, int(count), days=days,
                                  until=until if validity == "Until a date…" else None, note=note)
            st.session_state.new_codes = [{"Name": r["label"], "Code": AC.pretty(c), "Expires": r["expires"] or "never"} for c, r in made]
            st.rerun()
    if st.session_state.get("new_codes"):
        nc = pd.DataFrame(st.session_state.new_codes)
        st.success("New code(s) created. **Copy them now.** For security they're stored scrambled and can't be shown again "
                   "(use *Reset* below to issue a replacement).")
        for _, r in nc.iterrows():
            st.markdown(f"**{r['Name']}** · expires {r['Expires']}")
            st.code(r["Code"], language=None)
        a, b = st.columns(2)
        a.download_button("⬇ Download as CSV", nc.to_csv(index=False), "ipo_radar_codes.csv", width="stretch")
        if b.button("Done, hide these codes", width="stretch"):
            st.session_state.pop("new_codes")
            st.rerun()

    # ---- manage codes
    st.subheader("🗂 Manage codes")
    if df.empty:
        st.info("No codes yet. Create one above.")
    else:
        df["expires"] = df["expires"].fillna("Never")
        df["last_login"] = df["last_login"].fillna("—")
        view = df.assign(code=["•••••-••" + h for h in df["hint"]])[
            ["label", "code", "status", "expires", "last_login", "logins", "created", "note", "id"]]
        flt = st.segmented_control("Show", ["All", "Active", "Revoked", "Expired"], default="All")
        if flt and flt != "All":
            view = view[view["status"] == flt]
        st.dataframe(view.drop(columns=["id"]).sort_values("created", ascending=False), hide_index=True, width="stretch",
                     column_config={"label": "Name", "code": "Code (last 3)", "status": "Status", "expires": "Expires",
                                    "last_login": "Last login", "logins": st.column_config.NumberColumn("Logins", format="%d"),
                                    "created": "Created", "note": "Note"})
        opts = {f"{r['label']}  (…{r['hint']}, {AC.status(r)})": r["id"] for r in codes}
        pick_c = st.selectbox("Choose a code to change", list(opts))
        cid = opts[pick_c]
        rec = AC.get(cid)
        b1, b2, b3, b4, b5 = st.columns(5)
        if rec and rec.get("active", True):
            if b1.button("⛔ Revoke", width="stretch", help="Switch it off. The person is logged out on their next page load."):
                AC.update(cid, active=False)
                st.rerun()
        elif b1.button("✅ Reactivate", width="stretch"):
            AC.update(cid, active=True)
            st.rerun()
        if b2.button("⏩ +30 days", width="stretch", help="Extend expiry by 30 days (also reactivates)."):
            AC.extend(cid, 30)
            st.rerun()
        if b3.button("♾ No expiry", width="stretch"):
            AC.update(cid, expires=None)
            st.rerun()
        if b4.button("🔁 Reset code", width="stretch", help="Issue a new code for the same person. The old code and saved links stop working."):
            newc = AC.reset(cid)
            st.session_state.new_codes = [{"Name": rec["label"], "Code": AC.pretty(newc), "Expires": rec.get("expires") or "never"}]
            st.rerun()
        if b5.button("🗑 Delete", width="stretch"):
            st.session_state.confirm_del = cid
        if st.session_state.get("confirm_del") == cid:
            st.warning(f"Delete **{rec['label']}** permanently? Their watchlist is kept but they can't log in.")
            y, n = st.columns(2)
            if y.button("Yes, delete", type="primary", width="stretch"):
                AC.delete(cid)
                st.session_state.pop("confirm_del")
                st.rerun()
            if n.button("Cancel", width="stretch"):
                st.session_state.pop("confirm_del")
                st.rerun()
        with st.expander("Rename or edit note"):
            with st.form(f"edit::{cid}"):
                nl = st.text_input("Name", value=rec["label"] if rec else "")
                nn_ = st.text_input("Note", value=(rec or {}).get("note") or "")
                if st.form_submit_button("Save"):
                    AC.update(cid, label=nl.strip() or rec["label"], note=nn_)
                    st.rerun()

    st.subheader("ℹ️ How people log in")
    st.markdown("""
1. Send them the site link and their code (e.g. on WhatsApp).
2. They enter the code once. The page address then includes a personal key, so they can **bookmark it** and stay logged in.
3. Revoking, expiring or resetting a code logs them out on their next page load.
""")
