"""
Access Model — PostgreSQL-backed authorized users store.

Replaces the JSON-file-based AccessModel entirely.
All reads/writes go directly to the `authorized_users` table.

Table schema (created by database.py):
    email           TEXT PRIMARY KEY
    display_name    TEXT
    role            TEXT  ('admin' | 'viewer')
    active          BOOLEAN
    granted_by      TEXT
    granted_at      TIMESTAMPTZ
    revoked_by      TEXT  (nullable)
    revoked_at      TIMESTAMPTZ (nullable)
    role_updated_by TEXT  (nullable)
    role_updated_at TIMESTAMPTZ (nullable)
    reactivated_by  TEXT  (nullable)
    reactivated_at  TIMESTAMPTZ (nullable)
    ms_id           TEXT  (nullable)
"""

import logging
from typing import List, Optional

from config.auth_config import auth_config
from config.database import get_conn, init_db

logger = logging.getLogger(__name__)


class AccessModel:
    """PostgreSQL-backed CRUD interface for the authorized-users store."""

    def __init__(self) -> None:
        init_db()  # no-op if already initialized

    # ── Bootstrap ──────────────────────────────────────────────────────

    def bootstrap_admins(self) -> None:
        """Ensure BOOTSTRAP_ADMIN_EMAILS always have active admin access."""
        if not auth_config.BOOTSTRAP_ADMINS:
            return

        for raw_email in auth_config.BOOTSTRAP_ADMINS:
            email = raw_email.lower().strip()
            if not email:
                continue

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT email, active, role FROM authorized_users WHERE email = %s",
                        (email,),
                    )
                    existing = cur.fetchone()

                    if not existing:
                        cur.execute(
                            """
                            INSERT INTO authorized_users
                                (email, display_name, role, active, granted_by)
                            VALUES (%s, %s, 'admin', TRUE, 'system')
                            ON CONFLICT (email) DO NOTHING
                            """,
                            (email, email.split("@")[0]),
                        )
                        logger.info("Bootstrap admin seeded: %s", email)

                    elif not existing["active"]:
                        cur.execute(
                            """
                            UPDATE authorized_users
                            SET active = TRUE,
                                role = 'admin',
                                reactivated_by = 'system',
                                reactivated_at = NOW()
                            WHERE email = %s
                            """,
                            (email,),
                        )
                        logger.info("Bootstrap admin reactivated: %s", email)

                conn.commit()

    # ── Read ───────────────────────────────────────────────────────────

    def get_user(self, email: str) -> Optional[dict]:
        """Return user record dict or None."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM authorized_users WHERE email = %s",
                    (email.lower(),),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def is_authorized(self, email: str) -> bool:
        """Return True if user exists and is active."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT active FROM authorized_users WHERE email = %s",
                    (email.lower(),),
                )
                row = cur.fetchone()
                return bool(row and row["active"])

    def is_admin(self, email: str) -> bool:
        """Return True if user is active admin."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT active, role FROM authorized_users WHERE email = %s",
                    (email.lower(),),
                )
                row = cur.fetchone()
                return bool(row and row["active"] and row["role"] == "admin")

    def list_users(self) -> List[dict]:
        """Return all user records."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM authorized_users ORDER BY granted_at DESC"
                )
                return [dict(r) for r in cur.fetchall()]

    def list_active_users(self) -> List[dict]:
        """Return only active user records."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM authorized_users WHERE active = TRUE ORDER BY email"
                )
                return [dict(r) for r in cur.fetchall()]

    # ── Write ──────────────────────────────────────────────────────────

    def grant_access(
        self,
        email: str,
        display_name: str,
        role: str,
        granted_by: str,
        ms_id: str = "",
    ) -> dict:
        """Insert or update a user record. Returns the saved record."""
        email = email.lower().strip()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO authorized_users
                        (email, display_name, role, active, granted_by, granted_at, ms_id)
                    VALUES (%s, %s, %s, TRUE, %s, NOW(), %s)
                    ON CONFLICT (email) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        role         = EXCLUDED.role,
                        active       = TRUE,
                        granted_by   = EXCLUDED.granted_by,
                        granted_at   = NOW(),
                        revoked_by   = NULL,
                        revoked_at   = NULL,
                        ms_id        = COALESCE(EXCLUDED.ms_id, authorized_users.ms_id)
                    RETURNING *
                    """,
                    (email, display_name, role, granted_by, ms_id or None),
                )
                row = dict(cur.fetchone())
            conn.commit()
        logger.info("Access granted: %s as %s by %s", email, role, granted_by)
        return row

    def revoke_access(self, email: str, revoked_by: str) -> bool:
        """Soft-delete: mark user inactive. Returns True if found."""
        email = email.lower().strip()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE authorized_users
                    SET active = FALSE, revoked_by = %s, revoked_at = NOW()
                    WHERE email = %s
                    """,
                    (revoked_by, email),
                )
                affected = cur.rowcount
            conn.commit()
        if affected:
            logger.info("Access revoked: %s by %s", email, revoked_by)
        return bool(affected)

    def update_role(self, email: str, new_role: str, updated_by: str) -> bool:
        """Change role of an existing user. Returns True if found."""
        email = email.lower().strip()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE authorized_users
                    SET role = %s, role_updated_by = %s, role_updated_at = NOW()
                    WHERE email = %s
                    """,
                    (new_role, updated_by, email),
                )
                affected = cur.rowcount
            conn.commit()
        if affected:
            logger.info("Role updated: %s → %s by %s", email, new_role, updated_by)
        return bool(affected)

    def reactivate(self, email: str, granted_by: str) -> bool:
        """Re-enable a previously revoked user."""
        email = email.lower().strip()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE authorized_users
                    SET active = TRUE,
                        revoked_by = NULL,
                        revoked_at = NULL,
                        reactivated_by = %s,
                        reactivated_at = NOW()
                    WHERE email = %s
                    """,
                    (granted_by, email),
                )
                affected = cur.rowcount
            conn.commit()
        return bool(affected)