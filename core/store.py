"""SQLite storage: every refresh is snapshotted so you build your own GMP / subscription
history over time (the trend charts get richer the longer the app runs)."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parent.parent / "data" / "ipo_radar.db"


def _con() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute(
        """CREATE TABLE IF NOT EXISTS snapshots(
            ts TEXT, name TEXT, status TEXT, gmp REAL, gmp_pct REAL,
            sub_total REAL, sub_qib REAL, sub_nii REAL, sub_retail REAL)"""
    )
    con.execute("CREATE TABLE IF NOT EXISTS watchlist(name TEXT PRIMARY KEY, note TEXT, added TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, ts TEXT, payload TEXT)")
    return con


def save_snapshot(merged: pd.DataFrame) -> None:
    if merged is None or merged.empty:
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    cols = ["name", "status", "gmp", "gmp_pct", "sub_total", "sub_qib", "sub_nii", "sub_retail"]
    d = merged.reindex(columns=cols).copy()
    d.insert(0, "ts", ts)
    with _con() as con:
        # avoid duplicate snapshots inside the same minute
        con.execute("DELETE FROM snapshots WHERE ts=?", (ts,))
        d.to_sql("snapshots", con, if_exists="append", index=False)


def history(name: str | None = None) -> pd.DataFrame:
    with _con() as con:
        q = "SELECT * FROM snapshots" + (" WHERE name=?" if name else "")
        df = pd.read_sql(q, con, params=(name,) if name else None)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
    return df


def cache_put(key: str, df: pd.DataFrame) -> None:
    with _con() as con:
        con.execute("REPLACE INTO cache VALUES(?,?,?)",
                    (key, datetime.now().isoformat(timespec="minutes"), df.to_json(orient="split", date_format="iso")))


def cache_get(key: str) -> tuple[pd.DataFrame | None, str | None]:
    from io import StringIO

    with _con() as con:
        row = con.execute("SELECT ts,payload FROM cache WHERE key=?", (key,)).fetchone()
    if not row:
        return None, None
    df = pd.read_json(StringIO(row[1]), orient="split")
    for c in df.columns:
        if c in ("open", "close", "allotment", "listing", "listing_date", "close_date"):
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.tz_localize(None)
    return df, row[0]


def watchlist() -> pd.DataFrame:
    with _con() as con:
        return pd.read_sql("SELECT * FROM watchlist ORDER BY added DESC", con)


def watch_add(name: str, note: str = "") -> None:
    with _con() as con:
        con.execute("REPLACE INTO watchlist VALUES(?,?,?)", (name, note, datetime.now().strftime("%Y-%m-%d %H:%M")))


def watch_remove(name: str) -> None:
    with _con() as con:
        con.execute("DELETE FROM watchlist WHERE name=?", (name,))
