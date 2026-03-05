"""
database.py — PostgreSQL connection pool and schema bootstrap.
All tables are created on first connect if they don't exist.
Uses psycopg2 with a simple connection pool.
Required env vars:
    DATABASE_URL  →  postgresql://user:password@host:5432/dbname
    (or individual: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2 import pool

logger = logging.getLogger(__name__)

# ── Schema ─────────────────────────────────────────────────────────────────
_SCHEMA_SQL = """
-- Authorized users table (replaces config/authorized_users.json)
CREATE TABLE IF NOT EXISTS authorized_users (
    email           TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL DEFAULT '',
    role            TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'viewer')),
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    granted_by      TEXT NOT NULL DEFAULT 'system',
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_by      TEXT,
    revoked_at      TIMESTAMPTZ,
    role_updated_by TEXT,
    role_updated_at TIMESTAMPTZ,
    reactivated_by  TEXT,
    reactivated_at  TIMESTAMPTZ,
    ms_id           TEXT
);
-- Sessions table (replaces config/.sessions.json)
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    email           TEXT NOT NULL,
    user_info       JSONB NOT NULL DEFAULT '{}',
    role            TEXT NOT NULL DEFAULT 'viewer',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);
-- Index for fast session lookup and cleanup
CREATE INDEX IF NOT EXISTS idx_sessions_email      ON sessions (email);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);
-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_users_active ON authorized_users (active);
"""

# ── Connection pool (singleton) ────────────────────────────────────────────
_pool: pool.ThreadedConnectionPool | None = None


def _get_dsn() -> str:
    """Build DSN from DATABASE_URL or individual env vars."""
    url = os.environ.get("DATABASE_URL", "")
    if url:
        # Render/Railway/Heroku-style postgres:// URLs
        return url.replace("postgres://", "postgresql://", 1)
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "ar_dashboard")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        init_db()
        if _pool is None:
            raise RuntimeError("Connection pool failed to initialise")
    return _pool


def init_db() -> None:
    """
    Initialize connection pool and create schema if not exists.
    Call once at app startup.
    """
    global _pool
    if _pool is not None:
        return

    dsn = _get_dsn()
    logger.info("Connecting to PostgreSQL...")
    try:
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=dsn,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    except Exception as e:
        logger.error("Failed to create DB connection pool: %s", e)
        raise RuntimeError(f"Database connection failed: {e}") from e

    # Create tables
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
        conn.commit()
    logger.info("PostgreSQL connected and schema ready.")


@contextmanager
def get_conn() -> Generator:
    """Context manager that checks out a connection and returns it to the pool."""
    p = _get_pool()  # never None — raises before we get here if broken
    conn = p.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)
