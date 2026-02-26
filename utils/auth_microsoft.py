"""
Microsoft SSO — MSAL token exchange.
"""
import logging
from typing import Optional

import msal
import requests

from config.auth_config import auth_config

logger = logging.getLogger(__name__)


class MicrosoftAuthClient:
    def __init__(self) -> None:
        auth_config.validate()
        self._app = msal.ConfidentialClientApplication(
            client_id=auth_config.CLIENT_ID,
            client_credential=auth_config.CLIENT_SECRET,
            authority=auth_config.AUTHORITY,
        )

    def get_authorization_url(self, state: str = "") -> str:
        return self._app.get_authorization_request_url(
            scopes=list(auth_config.SCOPES),
            redirect_uri=auth_config.REDIRECT_URI,
            state=state,
        )

    def exchange_code_for_user(self, code: str) -> Optional[dict]:
        logger.info("Exchanging code for token (redirect_uri=%s)", auth_config.REDIRECT_URI)

        result = self._app.acquire_token_by_authorization_code(
            code=code,
            scopes=list(auth_config.SCOPES),
            redirect_uri=auth_config.REDIRECT_URI,
        )

        logger.info("MSAL result keys: %s", list(result.keys()))

        if "error" in result:
            logger.error("MSAL error: %s | %s", result["error"], result.get("error_description"))
            return None

        # Try id_token_claims first (no extra network call)
        claims = result.get("id_token_claims", {})
        if claims:
            email = (
                claims.get("email") or
                claims.get("preferred_username") or
                claims.get("upn") or ""
            ).lower().strip()
            logger.info("Email from id_token_claims: '%s'", email)
            if email:
                return {
                    "email": email,
                    "display_name": claims.get("name", email),
                    "given_name": claims.get("given_name", ""),
                    "surname": claims.get("family_name", ""),
                    "ms_id": claims.get("oid", ""),
                }

        # Fallback: Graph API
        access_token = result.get("access_token", "")
        if not access_token:
            logger.error("No access_token and no usable id_token_claims")
            return None

        logger.info("Falling back to Graph API call")
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=10)
        logger.info("Graph API status: %s", resp.status_code)

        if not resp.ok:
            logger.error("Graph API error: %s", resp.text)
            return None

        profile = resp.json()
        logger.info("Graph profile keys: %s", list(profile.keys()))

        email = (profile.get("mail") or profile.get("userPrincipalName") or "").lower().strip()
        logger.info("Email from Graph: '%s'", email)

        return {
            "email": email,
            "display_name": profile.get("displayName", email),
            "given_name": profile.get("givenName", ""),
            "surname": profile.get("surname", ""),
            "ms_id": profile.get("id", ""),
        }