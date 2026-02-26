"""
Complete test suite for access_model.py

Covers all CRUD operations, bootstrap functionality, and edge cases.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile

import pytest

from models.access_model import AccessModel, _EMPTY_DB


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary path for the database file."""
    return str(tmp_path / "test_users.json")


@pytest.fixture
def access_model(temp_db_path):
    """Create an AccessModel with a temporary database."""
    return AccessModel(db_path=temp_db_path)


@pytest.fixture
def populated_db_path(tmp_path):
    """Create a temporary database with pre-populated data."""
    db_path = tmp_path / "populated_users.json"
    data = {
        "users": {
            "admin@example.com": {
                "email": "admin@example.com",
                "display_name": "Admin User",
                "role": "admin",
                "granted_by": "system",
                "granted_at": "2024-01-01T00:00:00+00:00",
                "active": True,
            },
            "viewer@example.com": {
                "email": "viewer@example.com",
                "display_name": "Viewer User",
                "role": "viewer",
                "granted_by": "admin@example.com",
                "granted_at": "2024-01-02T00:00:00+00:00",
                "active": True,
            },
            "inactive@example.com": {
                "email": "inactive@example.com",
                "display_name": "Inactive User",
                "role": "viewer",
                "granted_by": "admin@example.com",
                "granted_at": "2024-01-03T00:00:00+00:00",
                "active": False,
                "revoked_by": "admin@example.com",
                "revoked_at": "2024-01-04T00:00:00+00:00",
            },
        }
    }
    with open(db_path, "w") as f:
        json.dump(data, f)
    return str(db_path)


@pytest.fixture
def populated_access_model(populated_db_path):
    """Create an AccessModel with pre-populated data."""
    return AccessModel(db_path=populated_db_path)


@pytest.fixture
def mock_auth_config():
    """Mock auth_config with test values."""
    with patch("models.access_model.auth_config") as mock_config:
        mock_config.ACCESS_DB_PATH = "config/authorized_users.json"
        mock_config.ROLE_ADMIN = "admin"
        mock_config.ROLE_VIEWER = "viewer"
        mock_config.BOOTSTRAP_ADMINS = ("bootstrap@example.com",)
        yield mock_config


# ---------------------------------------------------------------------
# Test: Module Constants
# ---------------------------------------------------------------------


class TestModuleConstants:
    def test_empty_db_structure(self):
        """Test _EMPTY_DB has correct structure."""
        assert _EMPTY_DB == {"users": {}}
        assert "users" in _EMPTY_DB
        assert isinstance(_EMPTY_DB["users"], dict)


# ---------------------------------------------------------------------
# Test: __init__
# ---------------------------------------------------------------------


class TestInit:
    def test_creates_instance_with_custom_path(self, temp_db_path):
        """Test AccessModel initializes with custom db_path."""
        model = AccessModel(db_path=temp_db_path)
        
        assert model._path == Path(temp_db_path)
        assert model._data == {"users": {}}

    def test_creates_parent_directories(self, tmp_path):
        """Test __init__ creates parent directories if they don't exist."""
        nested_path = tmp_path / "deep" / "nested" / "path" / "users.json"
        
        model = AccessModel(db_path=str(nested_path))
        
        assert nested_path.parent.exists()

    def test_uses_default_path_from_config(self, mock_auth_config, tmp_path):
        """Test uses auth_config.ACCESS_DB_PATH when no path provided."""
        mock_auth_config.ACCESS_DB_PATH = str(tmp_path / "default.json")
        
        model = AccessModel()
        
        assert model._path == Path(mock_auth_config.ACCESS_DB_PATH)

    def test_loads_existing_database(self, populated_db_path):
        """Test __init__ loads existing database file."""
        model = AccessModel(db_path=populated_db_path)
        
        assert "admin@example.com" in model._data["users"]
        assert "viewer@example.com" in model._data["users"]

    def test_initializes_empty_when_file_not_exists(self, temp_db_path):
        """Test initializes with empty data when file doesn't exist."""
        model = AccessModel(db_path=temp_db_path)
        
        assert model._data == {"users": {}}


# ---------------------------------------------------------------------
# Test: _load
# ---------------------------------------------------------------------


class TestLoad:
    def test_load_valid_json(self, populated_db_path):
        """Test _load reads valid JSON file."""
        model = AccessModel(db_path=populated_db_path)
        
        assert len(model._data["users"]) == 3

    def test_load_invalid_json_returns_empty(self, tmp_path):
        """Test _load returns empty dict on invalid JSON."""
        db_path = tmp_path / "invalid.json"
        db_path.write_text("{ invalid json }")
        
        model = AccessModel(db_path=str(db_path))
        
        assert model._data == {"users": {}}

    def test_load_nonexistent_file_returns_empty(self, temp_db_path):
        """Test _load returns empty dict when file doesn't exist."""
        model = AccessModel(db_path=temp_db_path)
        
        assert model._data == {"users": {}}

    def test_load_handles_os_error(self, tmp_path):
        """Test _load handles OSError gracefully."""
        db_path = tmp_path / "users.json"
        db_path.write_text('{"users": {}}')
        
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Create model without the patch first, then test _load
            model = AccessModel.__new__(AccessModel)
            model._path = db_path
            result = model._load()
        
        assert result == {"users": {}}


# ---------------------------------------------------------------------
# Test: _save
# ---------------------------------------------------------------------


class TestSave:
    def test_save_writes_json_file(self, access_model, temp_db_path):
        """Test _save writes data to JSON file."""
        access_model._data = {
            "users": {
                "test@example.com": {
                    "email": "test@example.com",
                    "role": "viewer",
                    "active": True,
                }
            }
        }
        
        access_model._save()
        
        with open(temp_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert "test@example.com" in saved_data["users"]

    def test_save_formats_with_indent(self, access_model, temp_db_path):
        """Test _save formats JSON with indent."""
        access_model._data = {"users": {"a@b.com": {"email": "a@b.com"}}}
        
        access_model._save()
        
        with open(temp_db_path, "r") as f:
            content = f.read()
        
        # Indented JSON should have newlines
        assert "\n" in content

    def test_save_handles_datetime_serialization(self, access_model, temp_db_path):
        """Test _save serializes datetime objects."""
        now = datetime.now(timezone.utc)
        access_model._data = {
            "users": {
                "test@example.com": {
                    "email": "test@example.com",
                    "granted_at": now,  # datetime object
                }
            }
        }
        
        # Should not raise
        access_model._save()
        
        with open(temp_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert "test@example.com" in saved_data["users"]

    def test_save_handles_os_error(self, access_model):
        """Test _save handles OSError gracefully."""
        access_model._data = {"users": {"test@example.com": {}}}
        
        with patch("builtins.open", side_effect=OSError("Disk full")):
            # Should not raise, just log error
            access_model._save()


# ---------------------------------------------------------------------
# Test: _now
# ---------------------------------------------------------------------


class TestNow:
    def test_now_returns_iso_format(self, access_model):
        """Test _now returns ISO format string."""
        result = access_model._now()
        
        assert isinstance(result, str)
        # Should be parseable as ISO format
        datetime.fromisoformat(result)

    def test_now_returns_utc_timezone(self, access_model):
        """Test _now returns UTC timezone."""
        result = access_model._now()
        
        # UTC ISO format ends with +00:00
        assert "+00:00" in result or "Z" in result


# ---------------------------------------------------------------------
# Test: bootstrap_admins
# ---------------------------------------------------------------------


class TestBootstrapAdmins:
    def test_bootstrap_creates_admin_when_empty(self, temp_db_path, mock_auth_config):
        """Test bootstrap_admins creates admin when DB is empty."""
        mock_auth_config.BOOTSTRAP_ADMINS = ("bootstrap@example.com",)
        
        model = AccessModel(db_path=temp_db_path)
        model.bootstrap_admins()
        
        assert "bootstrap@example.com" in model._data["users"]
        user = model._data["users"]["bootstrap@example.com"]
        assert user["role"] == "admin"
        assert user["active"] is True
        assert user["granted_by"] == "system"

    def test_bootstrap_multiple_admins(self, temp_db_path, mock_auth_config):
        """Test bootstrap_admins creates multiple admins."""
        mock_auth_config.BOOTSTRAP_ADMINS = (
            "admin1@example.com",
            "admin2@example.com",
        )
        
        model = AccessModel(db_path=temp_db_path)
        model.bootstrap_admins()
        
        assert "admin1@example.com" in model._data["users"]
        assert "admin2@example.com" in model._data["users"]

    def test_bootstrap_reactivates_inactive_admin(self, tmp_path, mock_auth_config):
        """Test bootstrap_admins reactivates inactive bootstrap admin."""
        db_path = tmp_path / "users.json"
        data = {
            "users": {
                "bootstrap@example.com": {
                    "email": "bootstrap@example.com",
                    "display_name": "Bootstrap",
                    "role": "viewer",  # Was demoted
                    "active": False,  # Was deactivated
                }
            }
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        
        mock_auth_config.BOOTSTRAP_ADMINS = ("bootstrap@example.com",)
        
        model = AccessModel(db_path=str(db_path))
        model.bootstrap_admins()
        
        user = model._data["users"]["bootstrap@example.com"]
        assert user["active"] is True
        assert user["role"] == "admin"
        assert "reactivated_by" in user
        assert user["reactivated_by"] == "system"

    def test_bootstrap_skips_active_admin(self, tmp_path, mock_auth_config):
        """Test bootstrap_admins doesn't modify already active admin."""
        db_path = tmp_path / "users.json"
        original_granted_at = "2020-01-01T00:00:00+00:00"
        data = {
            "users": {
                "bootstrap@example.com": {
                    "email": "bootstrap@example.com",
                    "display_name": "Bootstrap",
                    "role": "admin",
                    "active": True,
                    "granted_at": original_granted_at,
                }
            }
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        
        mock_auth_config.BOOTSTRAP_ADMINS = ("bootstrap@example.com",)
        
        model = AccessModel(db_path=str(db_path))
        model.bootstrap_admins()
        
        user = model._data["users"]["bootstrap@example.com"]
        # Should not be modified
        assert user["granted_at"] == original_granted_at

    def test_bootstrap_no_admins_configured(self, temp_db_path, mock_auth_config):
        """Test bootstrap_admins does nothing when no admins configured."""
        mock_auth_config.BOOTSTRAP_ADMINS = ()
        
        model = AccessModel(db_path=temp_db_path)
        model.bootstrap_admins()
        
        assert model._data == {"users": {}}

    def test_bootstrap_skips_empty_emails(self, temp_db_path, mock_auth_config):
        """Test bootstrap_admins skips empty email strings."""
        mock_auth_config.BOOTSTRAP_ADMINS = ("", "  ", "valid@example.com")
        
        model = AccessModel(db_path=temp_db_path)
        model.bootstrap_admins()
        
        assert "" not in model._data["users"]
        assert "valid@example.com" in model._data["users"]

    def test_bootstrap_normalizes_email_case(self, temp_db_path, mock_auth_config):
        """Test bootstrap_admins normalizes email to lowercase."""
        mock_auth_config.BOOTSTRAP_ADMINS = ("ADMIN@EXAMPLE.COM",)
        
        model = AccessModel(db_path=temp_db_path)
        model.bootstrap_admins()
        
        assert "admin@example.com" in model._data["users"]
        assert "ADMIN@EXAMPLE.COM" not in model._data["users"]

    def test_bootstrap_saves_to_file(self, temp_db_path, mock_auth_config):
        """Test bootstrap_admins persists changes to file."""
        mock_auth_config.BOOTSTRAP_ADMINS = ("bootstrap@example.com",)
        
        model = AccessModel(db_path=temp_db_path)
        model.bootstrap_admins()
        
        # Load fresh from file
        with open(temp_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert "bootstrap@example.com" in saved_data["users"]


# ---------------------------------------------------------------------
# Test: get_user
# ---------------------------------------------------------------------


class TestGetUser:
    def test_get_existing_user(self, populated_access_model):
        """Test get_user returns existing user."""
        user = populated_access_model.get_user("admin@example.com")
        
        assert user is not None
        assert user["email"] == "admin@example.com"
        assert user["role"] == "admin"

    def test_get_nonexistent_user(self, populated_access_model):
        """Test get_user returns None for nonexistent user."""
        user = populated_access_model.get_user("nonexistent@example.com")
        
        assert user is None

    def test_get_user_case_insensitive(self, populated_access_model):
        """Test get_user is case-insensitive."""
        user = populated_access_model.get_user("ADMIN@EXAMPLE.COM")
        
        assert user is not None
        assert user["email"] == "admin@example.com"

    def test_get_inactive_user(self, populated_access_model):
        """Test get_user returns inactive user."""
        user = populated_access_model.get_user("inactive@example.com")
        
        assert user is not None
        assert user["active"] is False


# ---------------------------------------------------------------------
# Test: is_authorized
# ---------------------------------------------------------------------


class TestIsAuthorized:
    def test_active_user_is_authorized(self, populated_access_model):
        """Test is_authorized returns True for active user."""
        assert populated_access_model.is_authorized("admin@example.com") is True
        assert populated_access_model.is_authorized("viewer@example.com") is True

    def test_inactive_user_not_authorized(self, populated_access_model):
        """Test is_authorized returns False for inactive user."""
        assert populated_access_model.is_authorized("inactive@example.com") is False

    def test_nonexistent_user_not_authorized(self, populated_access_model):
        """Test is_authorized returns False for nonexistent user."""
        assert populated_access_model.is_authorized("nonexistent@example.com") is False

    def test_is_authorized_case_insensitive(self, populated_access_model):
        """Test is_authorized is case-insensitive."""
        assert populated_access_model.is_authorized("ADMIN@EXAMPLE.COM") is True

    def test_user_without_active_field(self, access_model):
        """Test is_authorized handles user without active field."""
        access_model._data["users"]["test@example.com"] = {
            "email": "test@example.com",
            "role": "viewer",
            # No 'active' field
        }
        
        assert access_model.is_authorized("test@example.com") is False


# ---------------------------------------------------------------------
# Test: is_admin
# ---------------------------------------------------------------------


class TestIsAdmin:
    def test_admin_role_is_admin(self, populated_access_model):
        """Test is_admin returns True for admin role."""
        assert populated_access_model.is_admin("admin@example.com") is True

    def test_viewer_role_not_admin(self, populated_access_model):
        """Test is_admin returns False for viewer role."""
        assert populated_access_model.is_admin("viewer@example.com") is False

    def test_inactive_admin_not_admin(self, tmp_path, mock_auth_config):
        """Test is_admin returns False for inactive admin."""
        db_path = tmp_path / "users.json"
        data = {
            "users": {
                "admin@example.com": {
                    "email": "admin@example.com",
                    "role": "admin",
                    "active": False,
                }
            }
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        
        model = AccessModel(db_path=str(db_path))
        
        assert model.is_admin("admin@example.com") is False

    def test_nonexistent_user_not_admin(self, populated_access_model):
        """Test is_admin returns False for nonexistent user."""
        assert populated_access_model.is_admin("nonexistent@example.com") is False

    def test_is_admin_case_insensitive(self, populated_access_model):
        """Test is_admin is case-insensitive."""
        assert populated_access_model.is_admin("ADMIN@EXAMPLE.COM") is True


# ---------------------------------------------------------------------
# Test: list_users
# ---------------------------------------------------------------------


class TestListUsers:
    def test_list_all_users(self, populated_access_model):
        """Test list_users returns all users."""
        users = populated_access_model.list_users()
        
        assert len(users) == 3
        emails = [u["email"] for u in users]
        assert "admin@example.com" in emails
        assert "viewer@example.com" in emails
        assert "inactive@example.com" in emails

    def test_list_users_empty_db(self, access_model):
        """Test list_users returns empty list for empty DB."""
        users = access_model.list_users()
        
        assert users == []

    def test_list_users_returns_list(self, populated_access_model):
        """Test list_users returns a list type."""
        users = populated_access_model.list_users()
        
        assert isinstance(users, list)


# ---------------------------------------------------------------------
# Test: list_active_users
# ---------------------------------------------------------------------


class TestListActiveUsers:
    def test_list_only_active_users(self, populated_access_model):
        """Test list_active_users returns only active users."""
        users = populated_access_model.list_active_users()
        
        assert len(users) == 2
        emails = [u["email"] for u in users]
        assert "admin@example.com" in emails
        assert "viewer@example.com" in emails
        assert "inactive@example.com" not in emails

    def test_list_active_users_empty_db(self, access_model):
        """Test list_active_users returns empty list for empty DB."""
        users = access_model.list_active_users()
        
        assert users == []

    def test_list_active_users_all_inactive(self, tmp_path):
        """Test list_active_users when all users are inactive."""
        db_path = tmp_path / "users.json"
        data = {
            "users": {
                "user1@example.com": {"email": "user1@example.com", "active": False},
                "user2@example.com": {"email": "user2@example.com", "active": False},
            }
        }
        with open(db_path, "w") as f:
            json.dump(data, f)
        
        model = AccessModel(db_path=str(db_path))
        users = model.list_active_users()
        
        assert users == []


# ---------------------------------------------------------------------
# Test: grant_access
# ---------------------------------------------------------------------


class TestGrantAccess:
    def test_grant_access_new_user(self, access_model):
        """Test grant_access creates new user."""
        record = access_model.grant_access(
            email="new@example.com",
            display_name="New User",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        assert record["email"] == "new@example.com"
        assert record["display_name"] == "New User"
        assert record["role"] == "viewer"
        assert record["granted_by"] == "admin@example.com"
        assert record["active"] is True
        assert "granted_at" in record

    def test_grant_access_updates_existing_user(self, populated_access_model):
        """Test grant_access updates existing user."""
        record = populated_access_model.grant_access(
            email="viewer@example.com",
            display_name="Updated Viewer",
            role="admin",
            granted_by="admin@example.com",
        )
        
        assert record["display_name"] == "Updated Viewer"
        assert record["role"] == "admin"

    def test_grant_access_normalizes_email(self, access_model):
        """Test grant_access normalizes email to lowercase."""
        record = access_model.grant_access(
            email="  NEW@EXAMPLE.COM  ",
            display_name="New User",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        assert record["email"] == "new@example.com"
        assert "new@example.com" in access_model._data["users"]

    def test_grant_access_persists_to_file(self, access_model, temp_db_path):
        """Test grant_access saves to file."""
        access_model.grant_access(
            email="new@example.com",
            display_name="New User",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        with open(temp_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert "new@example.com" in saved_data["users"]

    def test_grant_access_returns_record(self, access_model):
        """Test grant_access returns the saved record."""
        record = access_model.grant_access(
            email="new@example.com",
            display_name="New User",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        assert isinstance(record, dict)
        assert record == access_model.get_user("new@example.com")


# ---------------------------------------------------------------------
# Test: revoke_access
# ---------------------------------------------------------------------


class TestRevokeAccess:
    def test_revoke_existing_user(self, populated_access_model):
        """Test revoke_access deactivates existing user."""
        result = populated_access_model.revoke_access(
            email="viewer@example.com",
            revoked_by="admin@example.com",
        )
        
        assert result is True
        user = populated_access_model.get_user("viewer@example.com")
        assert user["active"] is False
        assert user["revoked_by"] == "admin@example.com"
        assert "revoked_at" in user

    def test_revoke_nonexistent_user(self, access_model):
        """Test revoke_access returns False for nonexistent user."""
        result = access_model.revoke_access(
            email="nonexistent@example.com",
            revoked_by="admin@example.com",
        )
        
        assert result is False

    def test_revoke_normalizes_email(self, populated_access_model):
        """Test revoke_access normalizes email to lowercase."""
        result = populated_access_model.revoke_access(
            email="  VIEWER@EXAMPLE.COM  ",
            revoked_by="admin@example.com",
        )
        
        assert result is True
        assert populated_access_model.get_user("viewer@example.com")["active"] is False

    def test_revoke_persists_to_file(self, populated_access_model, populated_db_path):
        """Test revoke_access saves to file."""
        populated_access_model.revoke_access(
            email="viewer@example.com",
            revoked_by="admin@example.com",
        )
        
        with open(populated_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert saved_data["users"]["viewer@example.com"]["active"] is False


# ---------------------------------------------------------------------
# Test: update_role
# ---------------------------------------------------------------------


class TestUpdateRole:
    def test_update_role_existing_user(self, populated_access_model):
        """Test update_role changes user role."""
        result = populated_access_model.update_role(
            email="viewer@example.com",
            new_role="admin",
            updated_by="admin@example.com",
        )
        
        assert result is True
        user = populated_access_model.get_user("viewer@example.com")
        assert user["role"] == "admin"
        assert user["role_updated_by"] == "admin@example.com"
        assert "role_updated_at" in user

    def test_update_role_nonexistent_user(self, access_model):
        """Test update_role returns False for nonexistent user."""
        result = access_model.update_role(
            email="nonexistent@example.com",
            new_role="admin",
            updated_by="admin@example.com",
        )
        
        assert result is False

    def test_update_role_normalizes_email(self, populated_access_model):
        """Test update_role normalizes email to lowercase."""
        result = populated_access_model.update_role(
            email="  VIEWER@EXAMPLE.COM  ",
            new_role="admin",
            updated_by="admin@example.com",
        )
        
        assert result is True
        assert populated_access_model.get_user("viewer@example.com")["role"] == "admin"

    def test_update_role_persists_to_file(self, populated_access_model, populated_db_path):
        """Test update_role saves to file."""
        populated_access_model.update_role(
            email="viewer@example.com",
            new_role="admin",
            updated_by="admin@example.com",
        )
        
        with open(populated_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert saved_data["users"]["viewer@example.com"]["role"] == "admin"


# ---------------------------------------------------------------------
# Test: reactivate
# ---------------------------------------------------------------------


class TestReactivate:
    def test_reactivate_inactive_user(self, populated_access_model):
        """Test reactivate enables inactive user."""
        result = populated_access_model.reactivate(
            email="inactive@example.com",
            granted_by="admin@example.com",
        )
        
        assert result is True
        user = populated_access_model.get_user("inactive@example.com")
        assert user["active"] is True
        assert user["reactivated_by"] == "admin@example.com"
        assert "reactivated_at" in user

    def test_reactivate_removes_revoked_fields(self, populated_access_model):
        """Test reactivate removes revoked_by and revoked_at."""
        result = populated_access_model.reactivate(
            email="inactive@example.com",
            granted_by="admin@example.com",
        )
        
        assert result is True
        user = populated_access_model.get_user("inactive@example.com")
        assert "revoked_by" not in user
        assert "revoked_at" not in user

    def test_reactivate_nonexistent_user(self, access_model):
        """Test reactivate returns False for nonexistent user."""
        result = access_model.reactivate(
            email="nonexistent@example.com",
            granted_by="admin@example.com",
        )
        
        assert result is False

    def test_reactivate_normalizes_email(self, populated_access_model):
        """Test reactivate normalizes email to lowercase."""
        result = populated_access_model.reactivate(
            email="  INACTIVE@EXAMPLE.COM  ",
            granted_by="admin@example.com",
        )
        
        assert result is True
        assert populated_access_model.get_user("inactive@example.com")["active"] is True

    def test_reactivate_persists_to_file(self, populated_access_model, populated_db_path):
        """Test reactivate saves to file."""
        populated_access_model.reactivate(
            email="inactive@example.com",
            granted_by="admin@example.com",
        )
        
        with open(populated_db_path, "r") as f:
            saved_data = json.load(f)
        
        assert saved_data["users"]["inactive@example.com"]["active"] is True

    def test_reactivate_already_active_user(self, populated_access_model):
        """Test reactivate works on already active user."""
        result = populated_access_model.reactivate(
            email="viewer@example.com",
            granted_by="admin@example.com",
        )
        
        assert result is True
        user = populated_access_model.get_user("viewer@example.com")
        assert user["active"] is True
        assert user["reactivated_by"] == "admin@example.com"


# ---------------------------------------------------------------------
# Test: Integration and Edge Cases
# ---------------------------------------------------------------------


class TestIntegration:
    def test_full_user_lifecycle(self, access_model):
        """Test complete user lifecycle: create, update, revoke, reactivate."""
        # Grant access
        access_model.grant_access(
            email="user@example.com",
            display_name="Test User",
            role="viewer",
            granted_by="admin@example.com",
        )
        assert access_model.is_authorized("user@example.com") is True
        
        # Update role
        access_model.update_role(
            email="user@example.com",
            new_role="admin",
            updated_by="admin@example.com",
        )
        assert access_model.is_admin("user@example.com") is True
        
        # Revoke access
        access_model.revoke_access(
            email="user@example.com",
            revoked_by="admin@example.com",
        )
        assert access_model.is_authorized("user@example.com") is False
        
        # Reactivate
        access_model.reactivate(
            email="user@example.com",
            granted_by="admin@example.com",
        )
        assert access_model.is_authorized("user@example.com") is True
        assert access_model.is_admin("user@example.com") is True

    def test_concurrent_operations(self, temp_db_path):
        """Test multiple operations don't corrupt data."""
        model = AccessModel(db_path=temp_db_path)
        
        # Create multiple users
        for i in range(10):
            model.grant_access(
                email=f"user{i}@example.com",
                display_name=f"User {i}",
                role="viewer" if i % 2 == 0 else "admin",
                granted_by="system",
            )
        
        # Verify all users exist
        assert len(model.list_users()) == 10
        
        # Revoke half
        for i in range(0, 10, 2):
            model.revoke_access(f"user{i}@example.com", "system")
        
        # Verify active count
        assert len(model.list_active_users()) == 5


class TestEdgeCases:
    def test_special_characters_in_email(self, access_model):
        """Test handling of special characters in email."""
        email = "user+tag@sub.example.com"
        access_model.grant_access(
            email=email,
            display_name="Tagged User",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        assert access_model.is_authorized(email) is True

    def test_unicode_in_display_name(self, access_model):
        """Test handling of unicode in display name."""
        access_model.grant_access(
            email="user@example.com",
            display_name="José García 日本語",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        user = access_model.get_user("user@example.com")
        assert user["display_name"] == "José García 日本語"

    def test_empty_display_name(self, access_model):
        """Test handling of empty display name."""
        access_model.grant_access(
            email="user@example.com",
            display_name="",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        user = access_model.get_user("user@example.com")
        assert user["display_name"] == ""

    def test_very_long_email(self, access_model):
        """Test handling of very long email."""
        long_email = "a" * 200 + "@example.com"
        access_model.grant_access(
            email=long_email,
            display_name="Long Email User",
            role="viewer",
            granted_by="admin@example.com",
        )
        
        assert access_model.is_authorized(long_email.lower()) is True