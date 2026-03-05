"""
Microsoft SSO Authentication Utilities
Clean production-ready implementation
"""

import logging
from typing import Any

import msal
import requests
import streamlit as st

from config.auth_config import auth_config
from utils.session_manager import SessionManager

try:
    from utils.session_manager import (  # type: ignore[attr-defined]
        clear_session_cookie,
        get_cookie_manager,
        load_session_from_cookie,
        save_session_to_cookie,
    )
except ImportError:
    def get_cookie_manager() -> Any:  # type: ignore[misc]
        return None

    def save_session_to_cookie(cookie_manager: Any, *, user_info: Any, access_token: str) -> None:  # type: ignore[misc]
        pass

    def load_session_from_cookie(cookie_manager: Any) -> Any:  # type: ignore[misc]
        return None

    def clear_session_cookie(cookie_manager: Any) -> None:  # type: ignore[misc]
        pass

logger = logging.getLogger(__name__)


# ============================================================
# Microsoft Auth Client
# ============================================================


class MicrosoftAuth:
    def __init__(self) -> None:
        # auth_config.is_configured() may not exist on AuthConfig — guard both cases
        is_cfg: bool = (
            auth_config.is_configured()  # type: ignore[attr-defined]
            if hasattr(auth_config, "is_configured")
            else bool(
                getattr(auth_config, "CLIENT_ID", None)
                and getattr(auth_config, "CLIENT_SECRET", None)
                and getattr(auth_config, "TENANT_ID", None)
            )
        )
        if not is_cfg:
            st.error(
                "Microsoft SSO is not configured. Please set "
                "AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID."
            )
            st.stop()

        self.client = msal.ConfidentialClientApplication(
            client_id=auth_config.CLIENT_ID,
            client_credential=auth_config.CLIENT_SECRET,
            authority=auth_config.AUTHORITY,
        )
        # SCOPES may be a tuple or list — normalise to list[str] to satisfy mypy
        raw_scopes = getattr(auth_config, "SCOPES", None)
        self.scopes: list[str] = list(raw_scopes) if raw_scopes else ["User.Read"]

    def get_auth_url(self) -> str:
        return self.client.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=auth_config.REDIRECT_URI,
        )

    def exchange_code(self, code: str) -> dict[str, Any] | None:
        result = self.client.acquire_token_by_authorization_code(
            code=code,
            scopes=self.scopes,
            redirect_uri=auth_config.REDIRECT_URI,
        )
        if "error" in result:
            logger.error(result.get("error_description"))
            return None
        return result  # type: ignore[return-value]

    def get_user_info(self, access_token: str) -> dict[str, Any] | None:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        logger.error("Graph API error: %s", response.text)
        return None


# ============================================================
# Authentication Flow
# ============================================================


def is_authenticated() -> bool:
    return SessionManager().is_authenticated()


def get_current_user() -> Any:
    return SessionManager().current_user()


def handle_auth_callback(cookie_manager: Any) -> bool:
    """Handle Microsoft redirect callback."""
    code = st.query_params.get("code")
    error = st.query_params.get("error")

    if error:
        st.error("Authentication failed.")
        return False

    if not code:
        return False

    auth = MicrosoftAuth()
    token_result = auth.exchange_code(code)

    if not token_result or "access_token" not in token_result:
        st.error("Failed to retrieve access token.")
        return False

    access_token: str = token_result["access_token"]
    user_info = auth.get_user_info(access_token)

    if not user_info:
        st.error("Failed to fetch user profile.")
        return False

    email: str = (
        user_info.get("mail") or user_info.get("userPrincipalName") or ""
    ).lower()
    logger.info("Microsoft returned email: %s", email)

    user_payload: dict[str, Any] = {
        "email": email,
        "display_name": user_info.get("displayName"),
        "raw": user_info,
    }

    session = SessionManager()
    success = session.login(user_payload)

    if not success:
        st.error("You are not authorized.")
        return False

    save_session_to_cookie(
        cookie_manager,
        user_info=user_payload,
        access_token=access_token,
    )

    st.query_params.clear()
    logger.info("User authenticated: %s", email)
    return True


def login() -> None:
    auth = MicrosoftAuth()
    auth_url = auth.get_auth_url()
    st.markdown(
        f'<meta http-equiv="refresh" content="0; url={auth_url}">',
        unsafe_allow_html=True,
    )
    st.stop()


def logout() -> None:
    cookie_manager = get_cookie_manager()
    clear_session_cookie(cookie_manager)
    SessionManager().logout()

    logout_url = (
        f"{auth_config.AUTHORITY}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={auth_config.REDIRECT_URI}"
    )
    st.markdown(
        f'<meta http-equiv="refresh" content="0; url={logout_url}">',
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# Decorator
# ============================================================


def require_auth(func: Any) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        cookie_manager = get_cookie_manager()

        if not is_authenticated():
            session_data = load_session_from_cookie(cookie_manager)
            if session_data:
                session = SessionManager()
                # Use restore() if SessionManager exposes it, else fall back to login()
                if hasattr(session, "restore"):
                    session.restore(session_data)  # type: ignore[attr-defined]
                else:
                    session.login(session_data)

        if "code" in st.query_params:
            if handle_auth_callback(cookie_manager):
                st.rerun()

        if not is_authenticated():
            login()

        return func(*args, **kwargs)

    return wrapper
