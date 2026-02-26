"""
Session Manager — Single source of truth for auth state.
"""
import logging
from typing import Optional

import streamlit as st

from config.auth_config import auth_config
from models.access_model import AccessModel
from utils.persistent_session import (
    clear_persistent_session,
    persist_login,
)

logger = logging.getLogger(__name__)

_USER_KEY = "_auth_user"
_ROLE_KEY = "_auth_role"


class SessionManager:
    def __init__(self, access_model: Optional[AccessModel] = None) -> None:
        self._access = access_model or AccessModel()
        self._access.bootstrap_admins()

    def login(self, user_info: dict) -> bool:
        email = user_info.get("email", "").lower().strip()
        logger.info("login() called for: '%s'", email)
        self._access.bootstrap_admins()

        if not self._access.is_authorized(email):
            known = [u["email"] for u in self._access.list_users()]
            logger.warning("NOT authorized. Email='%s' | Known=%s", email, known)
            return False

        user_record = self._access.get_user(email)
        role = user_record.get("role", auth_config.ROLE_VIEWER) if user_record else auth_config.ROLE_VIEWER
        persist_login(user_info, role)
        logger.info("Login success: %s (%s)", email, role)
        return True

    def logout(self) -> None:
        clear_persistent_session()

    def is_authenticated(self) -> bool:
        return st.session_state.get(_USER_KEY) is not None

    def current_user(self) -> Optional[dict]:
        return st.session_state.get(_USER_KEY)

    def current_email(self) -> str:
        u = self.current_user()
        return u.get("email", "") if u else ""

    def current_display_name(self) -> str:
        u = self.current_user()
        return u.get("display_name", "") if u else ""

    def current_role(self) -> Optional[str]:
        return st.session_state.get(_ROLE_KEY)

    def is_admin(self) -> bool:
        return self.current_role() == auth_config.ROLE_ADMIN

    def is_viewer(self) -> bool:
        return self.current_role() == auth_config.ROLE_VIEWER