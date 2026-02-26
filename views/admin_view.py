"""
Admin View — Access Management Page.

Only visible to users with role="admin".
Lets admins:
  • View all authorized users
  • Grant access to new users (by email)
  • Change roles
  • Revoke access
  • Reactivate revoked users
"""

import logging

import streamlit as st

from config.auth_config import auth_config
from models.access_model import AccessModel
from utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────


def _role_badge(role: str) -> str:
    color = "#0078D4" if role == auth_config.ROLE_ADMIN else "#555"
    label = role.capitalize()
    return (
        f"<span style='background:{color};color:white;"
        f"padding:2px 10px;border-radius:12px;font-size:0.78rem;"
        f"font-weight:600;'>{label}</span>"
    )


def _status_badge(active: bool) -> str:
    if active:
        return "<span style='color:#22c55e;font-weight:600;'>● Active</span>"
    return "<span style='color:#ef4444;font-weight:600;'>● Revoked</span>"


# ── Main render ────────────────────────────────────────────────────────────


def render_admin_page(session: SessionManager) -> None:
    """Full access management admin page."""
    if not session.is_admin():
        st.error("⛔ You do not have permission to view this page.")
        return

    access = AccessModel()
    admin_email = session.current_email()

    st.title("Access Management")
    st.caption(
        "Manage who can access the AR Inflow Dashboard. "
        "Changes take effect immediately on next login."
    )

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_users, tab_grant, tab_audit = st.tabs(
        ["👥 Current Users", "➕ Grant Access", "📋 Audit Log"]
    )

    # ───────────────────────────────────────────────────────────────────
    # Tab 1: Current Users
    # ───────────────────────────────────────────────────────────────────
    with tab_users:
        st.subheader("Authorized Users")

        users = access.list_users()
        if not users:
            st.info("No users in the system yet. Use **Grant Access** to add the first user.")
        else:
            # Summary metrics
            active = [u for u in users if u.get("active")]
            admins = [u for u in active if u.get("role") == auth_config.ROLE_ADMIN]
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Users", len(users))
            c2.metric("Active", len(active))
            c3.metric("Admins", len(admins))

            st.divider()

            # Filter
            show_revoked = st.toggle("Show revoked users", value=False)
            filtered = users if show_revoked else [u for u in users if u.get("active")]

            for user in sorted(filtered, key=lambda u: u["email"]):
                _render_user_card(user, access, admin_email, session)

    # ───────────────────────────────────────────────────────────────────
    # Tab 2: Grant Access
    # ───────────────────────────────────────────────────────────────────
    with tab_grant:
        st.subheader("Grant Access to New User")
        st.caption(
            "Enter the Microsoft organizational email of the person you want to grant access to. "
            "They will be able to log in with their Microsoft account immediately."
        )

        with st.form("grant_access_form", clear_on_submit=True):
            new_email = st.text_input(
                "Email address *",
                placeholder="colleague@yourcompany.com",
            )
            display_name = st.text_input(
                "Display name",
                placeholder="Jane Doe  (optional — will be shown in the user list)",
            )
            role = st.selectbox(
                "Role *",
                options=[auth_config.ROLE_VIEWER, auth_config.ROLE_ADMIN],
                format_func=lambda r: "👁️ Viewer — can view the dashboard"
                if r == auth_config.ROLE_VIEWER
                else "Admin — can view dashboard AND manage access",
            )
            submitted = st.form_submit_button("✅ Grant Access", type="primary")

        if submitted:
            if not new_email or "@" not in new_email:
                st.error("Please enter a valid email address.")
            else:
                existing = access.get_user(new_email)
                if existing and existing.get("active"):
                    # Offer role update
                    st.warning(
                        f"**{new_email}** already has active access as "
                        f"**{existing['role']}**. Use the user card above to change their role."
                    )
                elif existing and not existing.get("active"):
                    access.reactivate(new_email, granted_by=admin_email)
                    access.update_role(new_email, role, updated_by=admin_email)
                    st.success(f"✅ Access reactivated for **{new_email}** as **{role}**.")
                    st.rerun()
                else:
                    name = display_name.strip() or new_email.split("@")[0]
                    access.grant_access(
                        email=new_email,
                        display_name=name,
                        role=role,
                        granted_by=admin_email,
                    )
                    st.success(f"✅ Access granted to **{new_email}** as **{role}**.")
                    st.rerun()

    # ───────────────────────────────────────────────────────────────────
    # Tab 3: Audit Log
    # ───────────────────────────────────────────────────────────────────
    with tab_audit:
        st.subheader("User Audit Log")
        st.caption("Full history of all user records (including revoked).")

        users_all = access.list_users()
        if not users_all:
            st.info("No records yet.")
        else:
            import pandas as pd

            rows = []
            for u in users_all:
                rows.append(
                    {
                        "Email": u.get("email", ""),
                        "Name": u.get("display_name", ""),
                        "Role": u.get("role", "").capitalize(),
                        "Status": "Active" if u.get("active") else "Revoked",
                        "Granted By": u.get("granted_by", ""),
                        "Granted At": u.get("granted_at", "")[:19].replace("T", " "),
                        "Revoked By": u.get("revoked_by", "—"),
                    }
                )
            df = pd.DataFrame(rows).sort_values("Granted At", ascending=False)
            st.dataframe(df, width="stretch", hide_index=True)


# ── User card ──────────────────────────────────────────────────────────────


def _render_user_card(
    user: dict, access: AccessModel, admin_email: str, session: SessionManager
) -> None:
    """Render an individual user management card."""
    email = user["email"]
    active = user.get("active", False)
    role = user.get("role", auth_config.ROLE_VIEWER)
    is_self = email == admin_email

    with st.expander(
        f"{user.get('display_name', email)}  •  {email}",
        expanded=False,
    ):
        col_info, col_actions = st.columns([2, 1])

        with col_info:
            st.markdown(
                f"{_role_badge(role)}&nbsp;&nbsp;{_status_badge(active)}",
                unsafe_allow_html=True,
            )
            st.caption(f"Granted by: {user.get('granted_by', '—')}  |  {user.get('granted_at', '')[:10]}")
            if not active:
                st.caption(
                    f"Revoked by: {user.get('revoked_by', '—')}  |  {user.get('revoked_at', '')[:10]}"
                )

        with col_actions:
            if is_self:
                st.caption("*(your account)*")
            else:
                # Role toggle
                new_role = (
                    auth_config.ROLE_ADMIN
                    if role == auth_config.ROLE_VIEWER
                    else auth_config.ROLE_VIEWER
                )
                role_btn_label = (
                    "⬆️ Make Admin" if new_role == auth_config.ROLE_ADMIN else "⬇️ Make Viewer"
                )
                if active and st.button(
                    role_btn_label,
                    key=f"role_{email}",
                    width="stretch",
                ):
                    access.update_role(email, new_role, updated_by=admin_email)
                    st.success(f"Role updated to **{new_role}**.")
                    st.rerun()

                # Revoke / Reactivate
                if active:
                    if st.button(
                        "🚫 Revoke Access",
                        key=f"revoke_{email}",
                        width="stretch",
                        type="secondary",
                    ):
                        access.revoke_access(email, revoked_by=admin_email)
                        st.warning(f"Access revoked for **{email}**.")
                        st.rerun()
                else:
                    if st.button(
                        "✅ Reactivate",
                        key=f"reactivate_{email}",
                        width="stretch",
                    ):
                        access.reactivate(email, granted_by=admin_email)
                        st.success(f"Access reactivated for **{email}**.")
                        st.rerun()