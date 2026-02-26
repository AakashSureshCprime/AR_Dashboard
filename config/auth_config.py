"""
Microsoft Azure AD / SSO Authentication Configuration.

Set these values via environment variables or a .env file.
Never hard-code secrets in source code.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthConfig:
    # ── Azure AD App Registration ──────────────────────────────────────
    CLIENT_ID: str = field(
        default_factory=lambda: os.environ.get("AZURE_CLIENT_ID", "")
    )
    CLIENT_SECRET: str = field(
        default_factory=lambda: os.environ.get("AZURE_CLIENT_SECRET", "")
    )
    TENANT_ID: str = field(
        default_factory=lambda: os.environ.get("AZURE_TENANT_ID", "")
    )

    # ── OAuth Redirect / App URL ───────────────────────────────────────
    # Must match exactly what's registered in Azure AD App > Redirect URIs
    REDIRECT_URI: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_REDIRECT_URI", "http://localhost:8501"
        )
    )

    # ── Microsoft OAuth Endpoints ──────────────────────────────────────
    @property
    def AUTHORITY(self) -> str:
        return f"https://login.microsoftonline.com/{self.TENANT_ID}"

    SCOPES: tuple = ("User.Read",)

    # ── Access Control ────────────────────────────────────────────────
    # Path to the JSON file storing authorized users
    ACCESS_DB_PATH: str = field(
        default_factory=lambda: os.environ.get(
            "ACCESS_DB_PATH", "config/authorized_users.json"
        )
    )

    # Role definitions
    ROLE_ADMIN: str = "admin"
    ROLE_VIEWER: str = "viewer"

    # Bootstrap: these emails are always admins (fallback if DB is empty)
    BOOTSTRAP_ADMINS: tuple = field(
        default_factory=lambda: tuple(
            e.strip()
            for e in os.environ.get("BOOTSTRAP_ADMIN_EMAILS", "").split(",")
            if e.strip()
        )
    )

    def validate(self) -> None:
        missing = [
            name
            for name, val in [
                ("AZURE_CLIENT_ID", self.CLIENT_ID),
                ("AZURE_CLIENT_SECRET", self.CLIENT_SECRET),
                ("AZURE_TENANT_ID", self.TENANT_ID),
            ]
            if not val
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please set them in your .env file or environment."
            )


auth_config = AuthConfig()