"""
Complete test suite for admin_view.py

Covers all rendering functions, helper functions, user actions, and edge cases.
"""

from unittest.mock import MagicMock, patch, call
import pandas as pd
import pytest

import views.admin_view as av


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def mock_session_admin():
    """Mock SessionManager for admin user."""
    session = MagicMock()
    session.is_admin.return_value = True
    session.current_email.return_value = "admin@example.com"
    return session


@pytest.fixture
def mock_session_non_admin():
    """Mock SessionManager for non-admin user."""
    session = MagicMock()
    session.is_admin.return_value = False
    session.current_email.return_value = "viewer@example.com"
    return session


@pytest.fixture
def mock_access_model():
    """Mock AccessModel with sample data."""
    access = MagicMock()
    access.list_users.return_value = [
        {
            "email": "admin@example.com",
            "display_name": "Admin User",
            "role": "admin",
            "active": True,
            "granted_by": "system",
            "granted_at": "2024-01-01T00:00:00+00:00",
        },
        {
            "email": "viewer@example.com",
            "display_name": "Viewer User",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-02T00:00:00+00:00",
        },
        {
            "email": "inactive@example.com",
            "display_name": "Inactive User",
            "role": "viewer",
            "active": False,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-03T00:00:00+00:00",
            "revoked_by": "admin@example.com",
            "revoked_at": "2024-01-04T00:00:00+00:00",
        },
    ]
    access.get_user.return_value = None
    return access


@pytest.fixture
def mock_auth_config():
    """Mock auth_config."""
    with patch("views.admin_view.auth_config") as mock_config:
        mock_config.ROLE_ADMIN = "admin"
        mock_config.ROLE_VIEWER = "viewer"
        yield mock_config


def create_mock_columns(count):
    """Helper to create mock columns with context manager support."""
    cols = []
    for _ in range(count):
        col = MagicMock()
        col.__enter__ = MagicMock(return_value=col)
        col.__exit__ = MagicMock(return_value=False)
        cols.append(col)
    return cols


def setup_columns_side_effect(mock_st):
    """Setup st.columns to return correct number of columns based on input."""
    def columns_side_effect(arg):
        if isinstance(arg, int):
            return create_mock_columns(arg)
        elif isinstance(arg, list):
            return create_mock_columns(len(arg))
        return create_mock_columns(3)
    
    mock_st.columns.side_effect = columns_side_effect


# ---------------------------------------------------------------------
# Test: Helper Functions
# ---------------------------------------------------------------------


class TestRoleBadge:
    def test_admin_role_badge(self, mock_auth_config):
        """Test _role_badge for admin role."""
        result = av._role_badge("admin")
        
        assert "Admin" in result
        assert "#0078D4" in result  # Admin color
        assert "<span" in result
        assert "style=" in result

    def test_viewer_role_badge(self, mock_auth_config):
        """Test _role_badge for viewer role."""
        result = av._role_badge("viewer")
        
        assert "Viewer" in result
        assert "#555" in result  # Non-admin color
        assert "<span" in result

    def test_role_badge_capitalizes(self, mock_auth_config):
        """Test _role_badge capitalizes role name."""
        result = av._role_badge("viewer")
        
        assert "Viewer" in result

    def test_role_badge_unknown_role(self, mock_auth_config):
        """Test _role_badge with unknown role."""
        result = av._role_badge("unknown")
        
        assert "Unknown" in result
        assert "#555" in result  # Falls back to non-admin color


class TestStatusBadge:
    def test_active_status_badge(self):
        """Test _status_badge for active user."""
        result = av._status_badge(True)
        
        assert "Active" in result
        assert "#22c55e" in result  # Green color
        assert "●" in result

    def test_revoked_status_badge(self):
        """Test _status_badge for revoked user."""
        result = av._status_badge(False)
        
        assert "Revoked" in result
        assert "#ef4444" in result  # Red color
        assert "●" in result

    def test_status_badge_returns_html(self):
        """Test _status_badge returns HTML span."""
        result_active = av._status_badge(True)
        result_revoked = av._status_badge(False)
        
        assert "<span" in result_active
        assert "</span>" in result_active
        assert "<span" in result_revoked
        assert "</span>" in result_revoked


# ---------------------------------------------------------------------
# Test: render_admin_page - Access Control
# ---------------------------------------------------------------------


class TestRenderAdminPageAccess:
    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_non_admin_sees_error(self, mock_access_cls, mock_st, mock_session_non_admin):
        """Test non-admin user sees error message."""
        av.render_admin_page(mock_session_non_admin)
        
        mock_st.error.assert_called_once()
        assert "permission" in mock_st.error.call_args[0][0].lower()
        # Should not proceed to render content
        mock_st.title.assert_not_called()

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_admin_sees_page(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test admin user sees the page."""
        mock_access_cls.return_value = mock_access_model
        
        # Mock tabs
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        # Setup dynamic columns
        setup_columns_side_effect(mock_st)
        
        # Mock expander
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        mock_st.title.assert_called_with("Access Management")
        mock_st.error.assert_not_called()


# ---------------------------------------------------------------------
# Test: render_admin_page - Tab 1: Current Users
# ---------------------------------------------------------------------


class TestCurrentUsersTab:
    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_empty_users_shows_info(self, mock_access_cls, mock_st, mock_session_admin):
        """Test empty user list shows info message."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = []
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        # Check that info was called - it may be called multiple times
        assert mock_st.info.called
        # Find the call that contains "Grant Access"
        info_calls = [str(c) for c in mock_st.info.call_args_list]
        # The first info call should be about empty users
        first_info = mock_st.info.call_args_list[0][0][0]
        assert "No users" in first_info or "Grant Access" in first_info

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_displays_user_metrics(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test metrics are displayed for users."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        # Verify columns were created for metrics
        mock_st.columns.assert_called()

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_show_revoked_toggle(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test show revoked users toggle."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        mock_st.toggle.assert_called_with("Show revoked users", value=False)


# ---------------------------------------------------------------------
# Test: render_admin_page - Tab 2: Grant Access
# ---------------------------------------------------------------------


class TestGrantAccessTab:
    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_form_rendered(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test grant access form is rendered."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        mock_st.form.assert_called_with("grant_access_form", clear_on_submit=True)

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_invalid_email(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test grant access with invalid email shows error."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        # Simulate form submission with invalid email
        mock_st.text_input.side_effect = ["invalid-email", "Display Name"]
        mock_st.selectbox.return_value = "viewer"
        mock_st.form_submit_button.return_value = True
        
        av.render_admin_page(mock_session_admin)
        
        mock_st.error.assert_called()
        error_calls = [str(c) for c in mock_st.error.call_args_list]
        assert any("valid email" in str(c).lower() for c in error_calls)

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_empty_email(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test grant access with empty email shows error."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.text_input.side_effect = ["", ""]
        mock_st.selectbox.return_value = "viewer"
        mock_st.form_submit_button.return_value = True
        
        av.render_admin_page(mock_session_admin)
        
        mock_st.error.assert_called()

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_existing_active_user(self, mock_access_cls, mock_st, mock_session_admin):
        """Test grant access to existing active user shows warning."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = []
        mock_access.get_user.return_value = {
            "email": "existing@example.com",
            "role": "viewer",
            "active": True,
        }
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.text_input.side_effect = ["existing@example.com", "Existing User"]
        mock_st.selectbox.return_value = "viewer"
        mock_st.form_submit_button.return_value = True
        
        av.render_admin_page(mock_session_admin)
        
        mock_st.warning.assert_called()
        warning_calls = [str(c) for c in mock_st.warning.call_args_list]
        assert any("already has active access" in str(c) for c in warning_calls)

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_reactivate_inactive_user(self, mock_access_cls, mock_st, mock_session_admin):
        """Test grant access to inactive user reactivates them."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = []
        mock_access.get_user.return_value = {
            "email": "inactive@example.com",
            "role": "viewer",
            "active": False,
        }
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.text_input.side_effect = ["inactive@example.com", "Inactive User"]
        mock_st.selectbox.return_value = "admin"
        mock_st.form_submit_button.return_value = True
        
        av.render_admin_page(mock_session_admin)
        
        mock_access.reactivate.assert_called_once_with(
            "inactive@example.com", granted_by="admin@example.com"
        )
        mock_access.update_role.assert_called_once_with(
            "inactive@example.com", "admin", updated_by="admin@example.com"
        )
        mock_st.success.assert_called()
        mock_st.rerun.assert_called()

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_new_user_success(self, mock_access_cls, mock_st, mock_session_admin):
        """Test grant access to new user succeeds."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = []
        mock_access.get_user.return_value = None
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.text_input.side_effect = ["new@example.com", "New User"]
        mock_st.selectbox.return_value = "viewer"
        mock_st.form_submit_button.return_value = True
        
        av.render_admin_page(mock_session_admin)
        
        mock_access.grant_access.assert_called_once_with(
            email="new@example.com",
            display_name="New User",
            role="viewer",
            granted_by="admin@example.com",
        )
        mock_st.success.assert_called()
        mock_st.rerun.assert_called()

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_grant_access_empty_display_name_uses_email(self, mock_access_cls, mock_st, mock_session_admin):
        """Test grant access with empty display name uses email prefix."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = []
        mock_access.get_user.return_value = None
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.text_input.side_effect = ["newuser@example.com", ""]  # Empty display name
        mock_st.selectbox.return_value = "viewer"
        mock_st.form_submit_button.return_value = True
        
        av.render_admin_page(mock_session_admin)
        
        mock_access.grant_access.assert_called_once()
        call_kwargs = mock_access.grant_access.call_args[1]
        assert call_kwargs["display_name"] == "newuser"  # Email prefix


# ---------------------------------------------------------------------
# Test: render_admin_page - Tab 3: Audit Log
# ---------------------------------------------------------------------


class TestAuditLogTab:
    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_audit_log_empty(self, mock_access_cls, mock_st, mock_session_admin):
        """Test audit log with no users shows info."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = []
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        # Info should be called for empty audit log
        assert mock_st.info.called

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_audit_log_displays_dataframe(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test audit log displays dataframe."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        av.render_admin_page(mock_session_admin)
        
        # Dataframe should be called for audit log
        mock_st.dataframe.assert_called()


# ---------------------------------------------------------------------
# Test: _render_user_card
# ---------------------------------------------------------------------


class TestRenderUserCard:
    @patch("views.admin_view.st")
    def test_renders_user_info(self, mock_st, mock_session_admin):
        """Test user card renders user information."""
        mock_access = MagicMock()
        user = {
            "email": "viewer@example.com",
            "display_name": "Viewer User",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        mock_st.expander.assert_called()
        mock_st.markdown.assert_called()

    @patch("views.admin_view.st")
    def test_self_user_shows_caption(self, mock_st, mock_session_admin):
        """Test own user card shows 'your account' caption."""
        mock_access = MagicMock()
        user = {
            "email": "admin@example.com",  # Same as admin_email
            "display_name": "Admin User",
            "role": "admin",
            "active": True,
            "granted_by": "system",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        # Should show "your account" caption
        caption_calls = [str(call) for call in mock_st.caption.call_args_list]
        assert any("your account" in str(call) for call in caption_calls)

    @patch("views.admin_view.st")
    def test_active_user_shows_role_and_revoke_buttons(self, mock_st, mock_session_admin):
        """Test active user card shows role toggle and revoke buttons."""
        mock_access = MagicMock()
        user = {
            "email": "viewer@example.com",
            "display_name": "Viewer User",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        # Should have button calls for role toggle and revoke
        button_calls = mock_st.button.call_args_list
        assert len(button_calls) >= 2

    @patch("views.admin_view.st")
    def test_inactive_user_shows_revoked_info(self, mock_st, mock_session_admin):
        """Test inactive user card shows revoked info."""
        mock_access = MagicMock()
        user = {
            "email": "inactive@example.com",
            "display_name": "Inactive User",
            "role": "viewer",
            "active": False,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
            "revoked_by": "admin@example.com",
            "revoked_at": "2024-01-02T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        # Should show revoked info in caption
        caption_calls = [str(call) for call in mock_st.caption.call_args_list]
        assert any("Revoked by" in str(call) for call in caption_calls)

    @patch("views.admin_view.st")
    def test_inactive_user_shows_reactivate_button(self, mock_st, mock_session_admin):
        """Test inactive user card shows reactivate button."""
        mock_access = MagicMock()
        user = {
            "email": "inactive@example.com",
            "display_name": "Inactive User",
            "role": "viewer",
            "active": False,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        # Should have reactivate button
        button_calls = [str(call) for call in mock_st.button.call_args_list]
        assert any("Reactivate" in str(call) for call in button_calls)

    @patch("views.admin_view.st")
    def test_role_toggle_admin_to_viewer(self, mock_st, mock_session_admin):
        """Test role toggle button for admin shows 'Make Viewer'."""
        mock_access = MagicMock()
        user = {
            "email": "other_admin@example.com",
            "display_name": "Other Admin",
            "role": "admin",
            "active": True,
            "granted_by": "system",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        button_calls = [str(call) for call in mock_st.button.call_args_list]
        assert any("Make Viewer" in str(call) for call in button_calls)

    @patch("views.admin_view.st")
    def test_role_toggle_viewer_to_admin(self, mock_st, mock_session_admin):
        """Test role toggle button for viewer shows 'Make Admin'."""
        mock_access = MagicMock()
        user = {
            "email": "viewer@example.com",
            "display_name": "Viewer User",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        button_calls = [str(call) for call in mock_st.button.call_args_list]
        assert any("Make Admin" in str(call) for call in button_calls)

    @patch("views.admin_view.st")
    def test_role_change_action(self, mock_st, mock_session_admin):
        """Test clicking role change button calls update_role."""
        mock_access = MagicMock()
        user = {
            "email": "viewer@example.com",
            "display_name": "Viewer User",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        
        # First button click (role change) returns True
        mock_st.button.side_effect = [True, False]
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        mock_access.update_role.assert_called_once_with(
            "viewer@example.com", "admin", updated_by="admin@example.com"
        )
        mock_st.success.assert_called()
        mock_st.rerun.assert_called()

    @patch("views.admin_view.st")
    def test_revoke_action(self, mock_st, mock_session_admin):
        """Test clicking revoke button calls revoke_access."""
        mock_access = MagicMock()
        user = {
            "email": "viewer@example.com",
            "display_name": "Viewer User",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        
        # Second button click (revoke) returns True
        mock_st.button.side_effect = [False, True]
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        mock_access.revoke_access.assert_called_once_with(
            "viewer@example.com", revoked_by="admin@example.com"
        )
        mock_st.warning.assert_called()
        mock_st.rerun.assert_called()

    @patch("views.admin_view.st")
    def test_reactivate_action(self, mock_st, mock_session_admin):
        """Test clicking reactivate button calls reactivate."""
        mock_access = MagicMock()
        user = {
            "email": "inactive@example.com",
            "display_name": "Inactive User",
            "role": "viewer",
            "active": False,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        
        # Reactivate button returns True
        mock_st.button.return_value = True
        
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)
        
        mock_access.reactivate.assert_called_once_with(
            "inactive@example.com", granted_by="admin@example.com"
        )
        mock_st.success.assert_called()
        mock_st.rerun.assert_called()


# ---------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------


class TestEdgeCases:
    @patch("views.admin_view.st")
    def test_user_without_display_name(self, mock_st, mock_session_admin):
        """Test user card handles missing display_name."""
        mock_access = MagicMock()
        user = {
            "email": "nodisplay@example.com",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
            # No display_name
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        # Should not raise
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)

    @patch("views.admin_view.st")
    def test_user_without_granted_by(self, mock_st, mock_session_admin):
        """Test user card handles missing granted_by."""
        mock_access = MagicMock()
        user = {
            "email": "nogranted@example.com",
            "display_name": "No Granted",
            "role": "viewer",
            "active": True,
            "granted_at": "2024-01-01T00:00:00+00:00",
            # No granted_by
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        # Should not raise
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)

    @patch("views.admin_view.st")
    def test_user_without_role_defaults_to_viewer(self, mock_st, mock_session_admin):
        """Test user card handles missing role."""
        mock_access = MagicMock()
        user = {
            "email": "norole@example.com",
            "display_name": "No Role",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
            # No role
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        # Should not raise
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)

    @patch("views.admin_view.st")
    def test_inactive_user_without_revoked_fields(self, mock_st, mock_session_admin):
        """Test inactive user card handles missing revoked_by/revoked_at."""
        mock_access = MagicMock()
        user = {
            "email": "inactive@example.com",
            "display_name": "Inactive User",
            "role": "viewer",
            "active": False,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01T00:00:00+00:00",
            # No revoked_by or revoked_at
        }
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        setup_columns_side_effect(mock_st)
        mock_st.button.return_value = False
        
        # Should not raise
        av._render_user_card(user, mock_access, "admin@example.com", mock_session_admin)

    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_audit_log_handles_missing_fields(self, mock_access_cls, mock_st, mock_session_admin):
        """Test audit log handles users with missing fields."""
        mock_access = MagicMock()
        mock_access.list_users.return_value = [
            {
                "email": "minimal@example.com",
                "active": True,
                # Minimal fields
            }
        ]
        mock_access_cls.return_value = mock_access
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_st.button.return_value = False
        mock_st.toggle.return_value = False
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        mock_st.form_submit_button.return_value = False
        
        # Should not raise
        av.render_admin_page(mock_session_admin)


# ---------------------------------------------------------------------
# Test: Integration
# ---------------------------------------------------------------------


class TestIntegration:
    @patch("views.admin_view.st")
    @patch("views.admin_view.AccessModel")
    def test_full_page_render(self, mock_access_cls, mock_st, mock_session_admin, mock_access_model):
        """Test full page renders without errors."""
        mock_access_cls.return_value = mock_access_model
        
        mock_tabs = [MagicMock(), MagicMock(), MagicMock()]
        for tab in mock_tabs:
            tab.__enter__ = MagicMock(return_value=tab)
            tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = mock_tabs
        
        setup_columns_side_effect(mock_st)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = mock_expander
        
        mock_form = MagicMock()
        mock_form.__enter__ = MagicMock(return_value=mock_form)
        mock_form.__exit__ = MagicMock(return_value=False)
        mock_st.form.return_value = mock_form
        
        mock_st.toggle.return_value = True  # Show revoked users
        mock_st.form_submit_button.return_value = False
        mock_st.button.return_value = False
        
        # Should not raise
        av.render_admin_page(mock_session_admin)
        
        mock_st.title.assert_called_with("Access Management")
        mock_st.tabs.assert_called()