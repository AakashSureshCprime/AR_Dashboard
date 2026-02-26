"""
Microsoft SSO Authentication Utilities
Clean production-ready implementation
"""

import email
import logging
from typing import Dict, Optional, Any

import msal
import requests
import streamlit as st

from config.auth_config import auth_config
from utils.session_manager import (
    SessionManager,
    get_cookie_manager,
    save_session_to_cookie,
    load_session_from_cookie,
    clear_session_cookie,
)

logger = logging.getLogger(__name__)


# ============================================================
# Microsoft Auth Client
# ============================================================

class MicrosoftAuth:
    def __init__(self):
        if not auth_config.is_configured():
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

        self.scopes = auth_config.SCOPES or ["User.Read"]

    def get_auth_url(self) -> str:
        return self.client.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=auth_config.REDIRECT_URI,
        )

    def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        result = self.client.acquire_token_by_authorization_code(
            code=code,
            scopes=self.scopes,
            redirect_uri=auth_config.REDIRECT_URI,
        )

        if "error" in result:
            logger.error(result.get("error_description"))
            return None

        return result

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if response.status_code == 200:
            return response.json()

        logger.error(f"Graph API error: {response.text}")
        return None


# ============================================================
# Authentication Flow
# ============================================================

def is_authenticated() -> bool:
    return SessionManager().is_authenticated()


def get_current_user():
    return SessionManager().current_user()


def handle_auth_callback(cookie_manager) -> bool:
    """
    Handle Microsoft redirect callback.
    """
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

    access_token = token_result["access_token"]
    user_info = auth.get_user_info(access_token)

    if not user_info:
        st.error("Failed to fetch user profile.")
        return False

    email = (
        user_info.get("mail")
        or user_info.get("userPrincipalName")
        or ""
    ).lower()
    logger.info("Microsoft returned email: %s", email)
    st.write("DEBUG EMAIL:", email)

    user_payload = {
        "email": email,
        "display_name": user_info.get("displayName"),
        "raw": user_info,
    }
    st.write("RAW USER INFO:", user_info)
    st.write("EMAIL FROM MS:", email)
    logger.info("EMAIL FROM MS: '%s'", email)
    session = SessionManager()
    success = session.login(user_payload)

    if not success:
        st.error("You are not authorized.")
        return False

    # Save to cookie
    save_session_to_cookie(
        cookie_manager,
        user_info=user_payload,
        access_token=access_token,
    )

    st.query_params.clear()
    logger.info(f"User authenticated: {email}")
    return True


def login():
    auth = MicrosoftAuth()
    auth_url = auth.get_auth_url()

    st.markdown(
        f'<meta http-equiv="refresh" content="0; url={auth_url}">',
        unsafe_allow_html=True,
    )
    st.stop()


def logout():
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

def require_auth(func):
    def wrapper(*args, **kwargs):
        cookie_manager = get_cookie_manager()

        # Restore from cookie if possible
        if not is_authenticated():
            session_data = load_session_from_cookie(cookie_manager)
            if session_data:
                SessionManager().restore(session_data)

        # Handle OAuth callback
        if "code" in st.query_params:
            if handle_auth_callback(cookie_manager):
                st.rerun()

        # Still not authenticated → show login
        if not is_authenticated():
            login()

        return func(*args, **kwargs)

    return wrapper