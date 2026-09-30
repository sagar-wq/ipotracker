"""Small permanent key/value store for JSON documents (access codes, watchlists, expert views).

Backends
--------
* GitHub Gist  – used when GITHUB_TOKEN and GIST_ID are configured. Free and permanent, so data
                 survives Streamlit Cloud restarts. Each document is one file in the (secret) gist.
* Local files  – data/<name>.json. Used when running on your own PC (or if the gist isn't set up).
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CFG: dict[str, str] = {"token": "", "gist": ""}
_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()
TTL = 20  # seconds a read stays cached


def configure(token: str | None, gist_id: str | None) -> None:
    _CFG["token"], _CFG["gist"] = (token or "").strip(), (gist_id or "").strip()
    _cache.clear()


def backend() -> str:
    return "gist" if _CFG["token"] and _CFG["gist"] else "local"


def _headers() -> dict:
    return {"Authorization": f"Bearer {_CFG['token']}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def _gist_read_all() -> dict[str, Any]:
    r = requests.get(f"https://api.github.com/gists/{_CFG['gist']}", headers=_headers(), timeout=20)
    r.raise_for_status()
    out = {}
    for fname, f in (r.json().get("files") or {}).items():
        if not fname.endswith(".json"):
            continue
        content = f.get("content")
        if f.get("truncated") and f.get("raw_url"):
            content = requests.get(f["raw_url"], headers=_headers(), timeout=20).text
        try:
            out[fname[:-5]] = json.loads(content or "null")
        except json.JSONDecodeError:
            out[fname[:-5]] = None
    return out


def load(name: str, default: Any = None) -> Any:
    now = time.time()
    with _lock:
        hit = _cache.get(name)
        if hit and now - hit[0] < TTL:
            return json.loads(json.dumps(hit[1]))  # defensive copy
    if backend() == "gist":
        allv = _gist_read_all()
        with _lock:
            for k, v in allv.items():
                _cache[k] = (now, v)
        val = allv.get(name)
    else:
        p = DATA_DIR / f"{name}.json"
        val = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        with _lock:
            _cache[name] = (now, val)
    return default if val is None else json.loads(json.dumps(val))


def save(name: str, value: Any) -> None:
    text = json.dumps(value, indent=1, default=str, ensure_ascii=False)
    if backend() == "gist":
        r = requests.patch(f"https://api.github.com/gists/{_CFG['gist']}", headers=_headers(),
                           json={"files": {f"{name}.json": {"content": text}}}, timeout=20)
        r.raise_for_status()
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = DATA_DIR / f".{name}.json.tmp"
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(DATA_DIR / f"{name}.json")
    with _lock:
        _cache[name] = (time.time(), json.loads(text))


def check() -> tuple[bool, str]:
    """Health check shown in the admin panel."""
    if backend() == "local":
        return True, f"Local files in {DATA_DIR} (fine on your PC; on Streamlit Cloud they are wiped on restart)."
    try:
        _gist_read_all()
        return True, "GitHub Gist connected. Codes and lists are stored permanently."
    except Exception as e:  # noqa: BLE001
        return False, f"GitHub Gist not reachable: {e}"
