"""
Access Model — Manages the persistent store of authorized users and their roles.

Storage: JSON file at config/authorized_users.json
Schema:
{
  "users": {
    "user@example.com": {
      "email": "user@example.com",
      "display_name": "Jane Doe",
      "role": "viewer",          # "admin" | "viewer"
      "granted_by": "admin@example.com",
      "granted_at": "2024-01-01T00:00:00",
      "active": true
    }
  }
}
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from config.auth_config import auth_config

logger = logging.getLogger(__name__)

_EMPTY_DB: dict = {"users": {}}


class AccessModel:
    """CRUD interface for the authorized-users store."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._path = Path(db_path or auth_config.ACCESS_DB_PATH)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = self._load()

    # ── Private helpers ────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load access DB: %s", e)
        return {"users": {}}

    def _save(self) -> None:
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2, default=str)
        except OSError as e:
            logger.error("Failed to save access DB: %s", e)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Bootstrap ──────────────────────────────────────────────────────

    def bootstrap_admins(self) -> None:
        """Ensure bootstrap admin emails always have active admin access.

        Previously this only ran when the DB was completely empty, which meant
        the first admin could get locked out if the DB had any other records.
        Now it always ensures bootstrap emails are present and active.
        """
        if not auth_config.BOOTSTRAP_ADMINS:
            return

        changed = False
        for email in auth_config.BOOTSTRAP_ADMINS:
            if not email:
                continue
            email = email.lower().strip()
            existing = self._data["users"].get(email)
            if not existing:
                # New — create with admin role
                self._data["users"][email] = {
                    "email": email,
                    "display_name": email.split("@")[0],
                    "role": auth_config.ROLE_ADMIN,
                    "granted_by": "system",
                    "granted_at": self._now(),
                    "active": True,
                }
                changed = True
                logger.info("Bootstrap admin seeded: %s", email)
            elif not existing.get("active"):
                # Was revoked — reactivate
                existing["active"] = True
                existing["role"] = auth_config.ROLE_ADMIN
                existing["reactivated_by"] = "system"
                existing["reactivated_at"] = self._now()
                changed = True
                logger.info("Bootstrap admin reactivated: %s", email)

        if changed:
            self._save()

    # ── Read ───────────────────────────────────────────────────────────

    def get_user(self, email: str) -> Optional[dict]:
        return self._data["users"].get(email.lower())

    def is_authorized(self, email: str) -> bool:
        user = self.get_user(email.lower())
        return bool(user and user.get("active", False))

    def is_admin(self, email: str) -> bool:
        user = self.get_user(email.lower())
        return bool(
            user
            and user.get("active", False)
            and user.get("role") == auth_config.ROLE_ADMIN
        )

    def list_users(self) -> List[dict]:
        return list(self._data["users"].values())

    def list_active_users(self) -> List[dict]:
        return [u for u in self.list_users() if u.get("active", False)]

    # ── Write ──────────────────────────────────────────────────────────

    def grant_access(
        self,
        email: str,
        display_name: str,
        role: str,
        granted_by: str,
    ) -> dict:
        """Add or update a user record. Returns the saved record."""
        email = email.lower().strip()
        record = {
            "email": email,
            "display_name": display_name,
            "role": role,
            "granted_by": granted_by,
            "granted_at": self._now(),
            "active": True,
        }
        self._data["users"][email] = record
        self._save()
        logger.info("Access granted: %s as %s by %s", email, role, granted_by)
        return record

    def revoke_access(self, email: str, revoked_by: str) -> bool:
        """Soft-delete: mark user inactive. Returns True if found."""
        email = email.lower().strip()
        user = self._data["users"].get(email)
        if not user:
            return False
        user["active"] = False
        user["revoked_by"] = revoked_by
        user["revoked_at"] = self._now()
        self._save()
        logger.info("Access revoked: %s by %s", email, revoked_by)
        return True

    def update_role(self, email: str, new_role: str, updated_by: str) -> bool:
        """Change the role of an existing user. Returns True if found."""
        email = email.lower().strip()
        user = self._data["users"].get(email)
        if not user:
            return False
        old_role = user["role"]
        user["role"] = new_role
        user["role_updated_by"] = updated_by
        user["role_updated_at"] = self._now()
        self._save()
        logger.info(
            "Role updated: %s %s → %s by %s", email, old_role, new_role, updated_by
        )
        return True

    def reactivate(self, email: str, granted_by: str) -> bool:
        """Re-enable a previously revoked user."""
        email = email.lower().strip()
        user = self._data["users"].get(email)
        if not user:
            return False
        user["active"] = True
        user.pop("revoked_by", None)
        user.pop("revoked_at", None)
        user["reactivated_by"] = granted_by
        user["reactivated_at"] = self._now()
        self._save()
        return True