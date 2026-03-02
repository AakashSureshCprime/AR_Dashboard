"""
Persistent Session Store — PostgreSQL-backed.

Replaces the JSON-file-based session store entirely.
Sessions are stored in the `sessions` table.

Cookie strategy (unchanged):
  - On login: write row to sessions table, inject JS to set browser cookie
  - On page load: read cookie → query sessions table → restore session_state
  - On logout: delete row from sessions table, inject JS to clear cookie

Table schema (created by database.py):
    session_id  TEXT PRIMARY KEY
    email       TEXT
    user_info   JSONB
    role        TEXT
    created_at  TIMESTAMPTZ
    expires_at  TIMESTAMPTZ
"""

import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from config.database import get_conn, init_db

logger = logging.getLogger(__name__)

SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "7"))
COOKIE_NAME = "ar_sid"

_USER_KEY = "_auth_user"
_ROLE_KEY = "_auth_role"


# ── Database session operations ────────────────────────────────────────────

def _write_session(session_id: str, user_info: dict, role: str) -> None:
    init_db()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean up expired sessions for this user first
            cur.execute(
                "DELETE FROM sessions WHERE expires_at < NOW()",
            )
            cur.execute(
                """
                INSERT INTO sessions (session_id, email, user_info, role, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    user_info  = EXCLUDED.user_info,
                    role       = EXCLUDED.role,
                    expires_at = EXCLUDED.expires_at
                """,
                (
                    session_id,
                    user_info.get("email", ""),
                    json.dumps(user_info),
                    role,
                    expires_at,
                ),
            )
        conn.commit()
    logger.info("Session written to DB: %s", session_id[:8])


def _read_session(session_id: str) -> Optional[dict]:
    init_db()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, email, user_info, role, created_at, expires_at
                FROM sessions
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "user_info": row["user_info"] if isinstance(row["user_info"], dict)
                             else json.loads(row["user_info"]),
                "role": row["role"],
            }


def _delete_session(session_id: str) -> None:
    init_db()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE session_id = %s",
                (session_id,),
            )
        conn.commit()
    logger.info("Session deleted from DB: %s", session_id[:8])


# ── Cookie helpers (JS injection) ──────────────────────────────────────────

def _set_cookie_js(session_id: str) -> None:
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
    components.html(
        f"""
        <script>
            document.cookie = "{COOKIE_NAME}=; max-age=0; path=/; SameSite=Strict";
        </script>
        """,
        height=0,
        width=0,
    )


def _read_cookie_from_headers() -> Optional[str]:
    """Read ar_sid cookie from incoming request headers (Streamlit >= 1.37)."""
    try:
        cookie_header = st.context.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{COOKIE_NAME}="):
                value = part[len(f"{COOKIE_NAME}="):].strip()
                return value or None
    except Exception as e:
        logger.debug("Could not read cookie from headers: %s", e)
    return None


# ── Public API ─────────────────────────────────────────────────────────────

def persist_login(user_info: dict, role: str) -> str:
    """Write session to DB + session_state. Returns session_id."""
    session_id = secrets.token_urlsafe(32)
    _write_session(session_id, user_info, role)
    st.session_state[_USER_KEY] = user_info
    st.session_state[_ROLE_KEY] = role
    st.session_state["_session_id"] = session_id
    logger.info("Session persisted for %s", user_info.get("email"))
    return session_id


def try_restore_from_cookie() -> bool:
    """
    Called on every page load. Reads cookie → queries DB → restores session_state.
    Returns True if session was restored.
    """
    if st.session_state.get(_USER_KEY):
        return True

    session_id = _read_cookie_from_headers()
    if not session_id:
        return False

    try:
        record = _read_session(session_id)
    except Exception as e:
        logger.warning("DB session restore failed: %s", e)
        return False

    if not record:
        logger.info("Session not found or expired in DB: %s", session_id[:8])
        return False

    st.session_state[_USER_KEY] = record["user_info"]
    st.session_state[_ROLE_KEY] = record["role"]
    st.session_state["_session_id"] = session_id
    logger.info("Session restored from DB for %s", record["user_info"].get("email"))
    return True


def write_cookie_after_login() -> None:
    """Inject JS to set cookie after login. Call during a render pass."""
    session_id = st.session_state.get("_session_id", "")
    if session_id:
        _set_cookie_js(session_id)


def clear_persistent_session() -> None:
    """Delete DB session record and clear browser cookie."""
    session_id = st.session_state.pop("_session_id", None)
    if session_id:
        try:
            _delete_session(session_id)
        except Exception as e:
            logger.warning("Failed to delete session from DB: %s", e)
    st.session_state.pop(_USER_KEY, None)
    st.session_state.pop(_ROLE_KEY, None)
    _clear_cookie_js()
    logger.info("Session cleared.")