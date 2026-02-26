"""
Auth View — Login page and OAuth callback.
"""
import logging
import secrets

import streamlit as st

from utils.auth_microsoft import MicrosoftAuthClient
from utils.session_manager import SessionManager

logger = logging.getLogger(__name__)


def handle_oauth_callback(session: SessionManager) -> bool:
    """
    Handle Microsoft redirect. Returns True if login succeeded.
    """
    code = st.query_params.get("code", "")
    if not code:
        return False

    # Guard: don't exchange the same code twice
    if st.session_state.get("_code_exchanged") == code:
        return session.is_authenticated()

    logger.info("OAuth code received. Exchanging...")
    st.session_state["_code_exchanged"] = code

    try:
        client = MicrosoftAuthClient()
        user_info = client.exchange_code_for_user(code)
    except Exception as e:
        logger.error("Token exchange exception: %s", e, exc_info=True)
        st.error(f"Sign-in error: {e}")
        return False

    if not user_info:
        st.error("Sign-in failed — could not fetch your profile. Check terminal logs.")
        return False

    email = user_info.get("email", "")
    if not email:
        st.error("Sign-in failed — Microsoft did not return an email address.")
        return False

    logger.info("Got user_info for: '%s'", email)

    authorized = session.login(user_info)
    if not authorized:
        render_access_denied(email)
        return False

    # Clear ?code= from URL — cookie handles persistence from here
    st.query_params.clear()
    st.rerun()
    return True


def render_login_page() -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align:center; padding: 8px 0 16px;">
                    
                    <h2 style="margin:8px 0 4px;">AR Inflow Dashboard</h2>
                    <p style="color:#888; margin:0;">Sign in to continue</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.divider()

            if "oauth_state" not in st.session_state:
                st.session_state["oauth_state"] = secrets.token_urlsafe(16)

            try:
                client = MicrosoftAuthClient()
                auth_url = client.get_authorization_url(state=st.session_state["oauth_state"])
                st.markdown(
                    f"""
                    <div style="text-align:center; margin: 20px 0;">
                        <a href="{auth_url}" target="_self" style="
                            display:inline-flex; align-items:center; gap:10px;
                            background:#0078D4; color:white; padding:12px 28px;
                            border-radius:4px; text-decoration:none;
                            font-size:0.95rem; font-weight:600;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 23 23">
                              <path fill="#f3f3f3" d="M0 0h23v23H0z"/>
                              <path fill="#f35325" d="M1 1h10v10H1z"/>
                              <path fill="#81bc06" d="M12 1h10v10H12z"/>
                              <path fill="#05a6f0" d="M1 12h10v10H1z"/>
                              <path fill="#ffba08" d="M12 12h10v10H12z"/>
                            </svg>
                            Sign in with Microsoft
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except EnvironmentError as e:
                st.error(f"Configuration error: {e}")

            st.markdown(
                "<p style='text-align:center;color:#aaa;font-size:0.75rem;margin-top:12px;'>"
                "Only authorized personnel may access this application.</p>",
                unsafe_allow_html=True,
            )


def render_access_denied(email: str = "") -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="text-align:center; padding:16px 0;">
                    <span style="font-size:3rem;">🔒</span>
                    <h3>Access Not Granted</h3>
                    <p style="color:#666;"><strong>{email}</strong> is not authorized.</p>
                    <p style="color:#888;font-size:0.88rem;">Contact your administrator.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("← Back to Login", width="stretch"):
                st.session_state.clear()
                st.rerun()