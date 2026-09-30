"""Headless refresh: fetch live data and store a snapshot (for Task Scheduler / cron).

Example (every 30 min, Mon–Sat 9:00–19:00) with cron:
    */30 9-19 * * 1-6  cd /path/to/ipo_radar && python refresh.py
"""
from core import analysis as A, sources as S, store

if __name__ == "__main__":
    g, s = S.fetch_gmp(), S.fetch_subscription()
    merged = A.merge_live(g, s)
    store.save_snapshot(merged)
    store.cache_put("gmp", g)
    store.cache_put("sub", s)
    try:
        store.cache_put("perf", S.fetch_performance())
    except Exception as e:  # noqa: BLE001
        print("performance fetch failed:", e)
    print(f"Saved snapshot of {len(merged)} IPOs")
