"""
Persistent Session Store.

Strategy: session_id is stored in a browser cookie (ar_sid).
  - On login: write session to JSON file, inject JS to set the cookie
  - On page load: read cookie from request headers → restore session_state
  - On logout: delete JSON record, inject JS to clear cookie
"""

import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "7"))
SESSION_STORE_PATH = Path(os.environ.get("SESSION_STORE_PATH", "config/.sessions.json"))
COOKIE_NAME = "ar_sid"

_USER_KEY = "_auth_user"
_ROLE_KEY = "_auth_role"


# ── Server-side session store ──────────────────────────────────────────────

def _load_store() -> dict:
    SESSION_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SESSION_STORE_PATH.exists():
        try:
            return json.loads(SESSION_STORE_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_store(store: dict) -> None:
    SESSION_STORE_PATH.write_text(json.dumps(store, indent=2, default=str))


def _write_session(session_id: str, user_info: dict, role: str) -> None:
    store = _load_store()
    cutoff = time.time() - SESSION_TTL_DAYS * 86400
    store = {k: v for k, v in store.items() if v.get("created_at", 0) > cutoff}
    store[session_id] = {
        "user_info": user_info,
        "role": role,
        "created_at": time.time(),
    }
    _save_store(store)
    logger.info("Session written: %s", session_id[:8])


def _read_session(session_id: str) -> Optional[dict]:
    store = _load_store()
    record = store.get(session_id)
    if not record:
        return None
    if time.time() - record.get("created_at", 0) > SESSION_TTL_DAYS * 86400:
        store.pop(session_id, None)
        _save_store(store)
        return None
    return record


def _delete_session(session_id: str) -> None:
    store = _load_store()
    store.pop(session_id, None)
    _save_store(store)


# ── Cookie read (from request headers) ────────────────────────────────────

def _read_cookie_from_headers() -> Optional[str]:
    """
    Read the ar_sid cookie from the incoming request headers.
    st.context.headers is available in Streamlit >= 1.37.
    """
    try:
        headers = st.context.headers
        cookie_header = headers.get("Cookie", "")
        if not cookie_header:
            return None
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{COOKIE_NAME}="):
                value = part[len(f"{COOKIE_NAME}="):].strip()
                return value if value else None
    except Exception as e:
        logger.debug("Could not read cookie from headers: %s", e)
    return None


# ── Cookie write/delete (via JS injection) ─────────────────────────────────

def _set_cookie_js(session_id: str) -> None:
    """Inject JS that sets the session cookie in the browser."""
    max_age = SESSION_TTL_DAYS * 86400
    components.html(
        f"""
        <script>
            document.cookie = "{COOKIE_NAME}={session_id}; "
                + "max-age={max_age}; path=/; SameSite=Strict";
        </script>
        """,
        height=0,
        width=0,
    )


def _clear_cookie_js() -> None:
    """Inject JS that expires the session cookie."""
    components.html(
        f"""
        <script>
            document.cookie = "{COOKIE_NAME}=; max-age=0; path=/; SameSite=Strict";
        </script>
        """,
        height=0,
        width=0,
    )


# ── Public API ─────────────────────────────────────────────────────────────

def persist_login(user_info: dict, role: str) -> str:
    """Write session to disk + session_state. Returns session_id."""
    session_id = secrets.token_urlsafe(32)
    _write_session(session_id, user_info, role)
    st.session_state[_USER_KEY] = user_info
    st.session_state[_ROLE_KEY] = role
    st.session_state["_session_id"] = session_id
    logger.info("Session persisted for %s", user_info.get("email"))
    return session_id


def try_restore_from_cookie() -> bool:
    """
    Called on every page load. Reads cookie from request headers,
    looks up the session store, restores session_state.
    Returns True if session was restored.
    """
    if st.session_state.get(_USER_KEY):
        return True  # Already in memory

    session_id = _read_cookie_from_headers()
    if not session_id:
        return False

    record = _read_session(session_id)
    if not record:
        logger.info("Cookie sid not found or expired.")
        return False

    st.session_state[_USER_KEY] = record["user_info"]
    st.session_state[_ROLE_KEY] = record["role"]
    st.session_state["_session_id"] = session_id
    logger.info("Session restored from cookie for %s", record["user_info"].get("email"))
    return True


def write_cookie_after_login() -> None:
    """
    Call this AFTER persist_login() to write the cookie to the browser.
    Must be called during a render pass (not inside a cached function).
    """
    session_id = st.session_state.get("_session_id", "")
    if session_id:
        _set_cookie_js(session_id)


def clear_persistent_session() -> None:
    """Delete server-side session and clear the browser cookie."""
    session_id = st.session_state.pop("_session_id", None)
    if session_id:
        _delete_session(session_id)
    st.session_state.pop(_USER_KEY, None)
    st.session_state.pop(_ROLE_KEY, None)
    _clear_cookie_js()
    logger.info("Session cleared.")