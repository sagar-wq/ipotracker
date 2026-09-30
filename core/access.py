"""Access codes: 10-character alphanumeric codes created from the admin panel.

* Codes use an unambiguous alphabet (no 0/O, 1/I/L) and are typed case-insensitively.
* Only a salted SHA-256 hash of each code is stored; the full code is shown once, when it's created.
* Each code can have a name, an expiry date, and be revoked / reactivated / reset at any time.
* After login the browser URL gets a signed token (?k=...) so refreshing or bookmarking keeps
  the visitor logged in; revoking or expiring the code logs them out on their next page load.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta, timezone

from . import persist

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 10
DOC = "access_codes"
_SECRET = {"key": "change-me"}


def configure(secret_key: str) -> None:
    _SECRET["key"] = secret_key or "change-me"


def normalize(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def pretty(code: str) -> str:
    return f"{code[:5]}-{code[5:]}"


def _hash(code: str) -> str:
    return hashlib.sha256(f"{_SECRET['key']}::{normalize(code)}".encode()).hexdigest()


IST = timezone(timedelta(hours=5, minutes=30))


def _now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M")


def _today() -> date:
    return datetime.now(IST).date()


def all_codes() -> list[dict]:
    return persist.load(DOC, []) or []


def _save(rows: list[dict]) -> None:
    persist.save(DOC, rows)


def status(rec: dict) -> str:
    if not rec.get("active", True):
        return "Revoked"
    exp = rec.get("expires")
    if exp and date.fromisoformat(exp) < _today():
        return "Expired"
    return "Active"


def create(label: str, days: int | None = None, until: date | None = None, note: str = "") -> tuple[str, dict]:
    rows = all_codes()
    existing = {r["hash"] for r in rows}
    code = new_code()
    while _hash(code) in existing:
        code = new_code()
    expires = until.isoformat() if until else ((_today() + timedelta(days=days)).isoformat() if days else None)
    rec = {"id": secrets.token_hex(4), "hash": _hash(code), "hint": code[-3:], "label": label.strip() or "Unnamed",
           "note": note, "created": _now(), "expires": expires, "active": True, "last_login": None, "logins": 0}
    rows.append(rec)
    _save(rows)
    return code, rec


def create_many(label: str, count: int, **kw) -> list[tuple[str, dict]]:
    out = []
    for i in range(count):
        out.append(create(label if count == 1 else f"{label} #{i + 1}", **kw))
    return out


def verify(code: str) -> tuple[dict | None, str]:
    c = normalize(code)
    if len(c) != LENGTH:
        return None, f"Codes are {LENGTH} characters (letters and numbers)."
    h = _hash(c)
    for r in all_codes():
        if hmac.compare_digest(r["hash"], h):
            st = status(r)
            if st == "Revoked":
                return None, "This code has been switched off. Please contact the admin."
            if st == "Expired":
                return None, f"This code expired on {r['expires']}. Please contact the admin."
            return r, "ok"
    return None, "That code isn't valid. Check for typos and try again."


def record_login(code_id: str) -> None:
    rows = all_codes()
    for r in rows:
        if r["id"] == code_id:
            r["logins"] = int(r.get("logins") or 0) + 1
            r["last_login"] = _now()
    _save(rows)


def get(code_id: str) -> dict | None:
    return next((r for r in all_codes() if r["id"] == code_id), None)


def update(code_id: str, **changes) -> None:
    rows = all_codes()
    for r in rows:
        if r["id"] == code_id:
            r.update(changes)
    _save(rows)


def extend(code_id: str, days: int) -> None:
    r = get(code_id)
    if not r:
        return
    base = max(_today(), date.fromisoformat(r["expires"])) if r.get("expires") else _today()
    update(code_id, expires=(base + timedelta(days=days)).isoformat(), active=True)


def reset(code_id: str) -> str | None:
    """Give the same person a brand-new code (the old one stops working)."""
    rows = all_codes()
    for r in rows:
        if r["id"] == code_id:
            code = new_code()
            r.update(hash=_hash(code), hint=code[-3:], active=True)  # same id → watchlist kept; old links stop working
            _save(rows)
            return code
    return None


def delete(code_id: str) -> None:
    _save([r for r in all_codes() if r["id"] != code_id])


# ---- stay-logged-in token --------------------------------------------------
def _sig(rec: dict) -> str:
    # bound to the current code hash, so resetting a code invalidates old stay-logged-in links
    msg = f"{rec['id']}:{rec['hash'][:16]}".encode()
    return hmac.new(_SECRET["key"].encode(), msg, hashlib.sha256).hexdigest()[:20]


def token_for(code_id: str) -> str:
    r = get(code_id)
    return f"{code_id}.{_sig(r)}" if r else ""


def from_token(tok: str | None) -> dict | None:
    if not tok or "." not in tok:
        return None
    code_id, sig = tok.split(".", 1)
    r = get(code_id)
    if not r or not hmac.compare_digest(sig, _sig(r)):
        return None
    return r if status(r) == "Active" else None


# ---- per-user watchlists -----------------------------------------------------
def watchlist(user: str) -> list[dict]:
    return (persist.load("watchlists", {}) or {}).get(user, [])


def watch_set(user: str, items: list[dict]) -> None:
    allw = persist.load("watchlists", {}) or {}
    allw[user] = items
    persist.save("watchlists", allw)
