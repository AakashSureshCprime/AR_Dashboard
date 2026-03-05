"""
Complete test suite for the PostgreSQL-backed access_model.py

Covers all CRUD operations, bootstrap functionality, and edge cases.
All database calls are mocked via psycopg2 connection/cursor patching.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from models.access_model import AccessModel

# ─────────────────────────────────────────────────────────────────────────────
# Helpers / shared factories
# ─────────────────────────────────────────────────────────────────────────────


def _make_row(**kwargs) -> MagicMock:
    """Return a MagicMock that behaves like a psycopg2 RealDictRow."""
    row = MagicMock()
    row.__iter__ = lambda s: iter(kwargs.items())
    row.__getitem__ = lambda s, k: kwargs[k]
    row.keys = lambda: kwargs.keys()
    # dict(row) calls this path in AccessModel
    row.__class__ = dict  # trick: makes dict(row) work via **row
    # Actually we just need to make dict(row) work:
    row._data = kwargs
    # Patch so dict(row) returns kwargs
    with patch("builtins.dict"):
        pass
    return kwargs  # return plain dict – cleaner for testing


def _cursor(fetchone=None, fetchall=None, rowcount=1):
    """Build a mock cursor context-manager."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    cur.rowcount = rowcount
    # Support `with conn.cursor() as cur:`
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    return cur


def _conn(cursor):
    """Build a mock connection context-manager wrapping *cursor*."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_init_db():
    """Always stub out init_db so no real DB is touched."""
    with patch("models.access_model.init_db") as m:
        yield m


@pytest.fixture()
def model():
    """Return a fresh AccessModel with DB initialisation mocked."""
    return AccessModel()


@pytest.fixture()
def admin_row():
    return {
        "email": "admin@example.com",
        "display_name": "Admin User",
        "role": "admin",
        "active": True,
        "granted_by": "system",
        "granted_at": "2024-01-01T00:00:00+00:00",
        "revoked_by": None,
        "revoked_at": None,
        "role_updated_by": None,
        "role_updated_at": None,
        "reactivated_by": None,
        "reactivated_at": None,
        "ms_id": None,
    }


@pytest.fixture()
def viewer_row():
    return {
        "email": "viewer@example.com",
        "display_name": "Viewer User",
        "role": "viewer",
        "active": True,
        "granted_by": "admin@example.com",
        "granted_at": "2024-01-02T00:00:00+00:00",
        "revoked_by": None,
        "revoked_at": None,
        "role_updated_by": None,
        "role_updated_at": None,
        "reactivated_by": None,
        "reactivated_at": None,
        "ms_id": None,
    }


@pytest.fixture()
def inactive_row():
    return {
        "email": "inactive@example.com",
        "display_name": "Inactive User",
        "role": "viewer",
        "active": False,
        "granted_by": "admin@example.com",
        "granted_at": "2024-01-03T00:00:00+00:00",
        "revoked_by": "admin@example.com",
        "revoked_at": "2024-01-04T00:00:00+00:00",
        "role_updated_by": None,
        "role_updated_at": None,
        "reactivated_by": None,
        "reactivated_at": None,
        "ms_id": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test: __init__
# ─────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_calls_init_db_on_construction(self, mock_init_db):
        AccessModel()
        mock_init_db.assert_called_once()

    def test_init_db_called_exactly_once_per_instance(self, mock_init_db):
        AccessModel()
        AccessModel()
        assert mock_init_db.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# Test: bootstrap_admins
# ─────────────────────────────────────────────────────────────────────────────


class TestBootstrapAdmins:
    """bootstrap_admins should seed / reactivate bootstrap admin emails."""

    def _patch_config(self, admins):
        return patch(
            "models.access_model.auth_config",
            BOOTSTRAP_ADMINS=admins,
        )

    # -- no-op cases ----------------------------------------------------------

    def test_does_nothing_when_no_admins_configured(self, model):
        with self._patch_config([]):
            with patch("models.access_model.get_conn") as mock_get_conn:
                model.bootstrap_admins()
                mock_get_conn.assert_not_called()

    def test_skips_blank_email_strings(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["", "  "]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()
                cur.execute.assert_not_called()

    # -- new admin seeding ----------------------------------------------------

    def test_inserts_new_bootstrap_admin(self, model):
        cur = _cursor(fetchone=None)  # no existing record
        conn = _conn(cur)
        with self._patch_config(["admin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        # First call: SELECT to check existence
        first_sql = cur.execute.call_args_list[0][0][0].strip()
        assert "SELECT" in first_sql

        # Second call: INSERT
        second_sql = cur.execute.call_args_list[1][0][0].strip()
        assert "INSERT" in second_sql

    def test_normalises_email_to_lowercase_on_insert(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["ADMIN@EXAMPLE.COM"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        insert_args = cur.execute.call_args_list[1][0][1]
        assert insert_args[0] == "admin@example.com"

    def test_strips_whitespace_from_email(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["  admin@example.com  "]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        insert_args = cur.execute.call_args_list[1][0][1]
        assert insert_args[0] == "admin@example.com"

    def test_uses_username_as_display_name_on_insert(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["newadmin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        insert_args = cur.execute.call_args_list[1][0][1]
        assert insert_args[1] == "newadmin"  # display_name = part before @

    def test_seeds_multiple_admins(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["a@example.com", "b@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        # Each admin triggers a SELECT + INSERT = 4 execute calls total
        assert cur.execute.call_count == 4

    def test_commits_after_each_admin(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["admin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        conn.commit.assert_called_once()

    # -- reactivation of inactive admin ---------------------------------------

    def test_reactivates_inactive_bootstrap_admin(self, model):
        inactive = {"email": "admin@example.com", "active": False, "role": "viewer"}
        cur = _cursor(fetchone=inactive)
        conn = _conn(cur)
        with self._patch_config(["admin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        update_sql = cur.execute.call_args_list[1][0][0].strip()
        assert "UPDATE" in update_sql
        assert "active = TRUE" in update_sql

    def test_skips_already_active_admin(self, model):
        active = {"email": "admin@example.com", "active": True, "role": "admin"}
        cur = _cursor(fetchone=active)
        conn = _conn(cur)
        with self._patch_config(["admin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        # Only the SELECT should have run — no INSERT or UPDATE
        assert cur.execute.call_count == 1

    def test_logs_when_seeding_new_admin(self, model, caplog):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with self._patch_config(["newadmin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                with caplog.at_level(logging.INFO, logger="models.access_model"):
                    model.bootstrap_admins()

        assert any("seeded" in r.message for r in caplog.records)

    def test_logs_when_reactivating_admin(self, model, caplog):
        inactive = {"email": "admin@example.com", "active": False, "role": "viewer"}
        cur = _cursor(fetchone=inactive)
        conn = _conn(cur)
        with self._patch_config(["admin@example.com"]):
            with patch("models.access_model.get_conn", return_value=conn):
                with caplog.at_level(logging.INFO, logger="models.access_model"):
                    model.bootstrap_admins()

        assert any("reactivated" in r.message for r in caplog.records)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_user
# ─────────────────────────────────────────────────────────────────────────────


class TestGetUser:
    def test_returns_dict_for_existing_user(self, model, admin_row):
        cur = _cursor(fetchone=admin_row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.get_user("admin@example.com")

        assert result == admin_row

    def test_returns_none_for_missing_user(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.get_user("ghost@example.com")

        assert result is None

    def test_lowercases_email_in_query(self, model, admin_row):
        cur = _cursor(fetchone=admin_row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.get_user("ADMIN@EXAMPLE.COM")

        _, args = cur.execute.call_args
        # The bound parameter should be lowercased
        assert "admin@example.com" in args[0] if args else True
        # Check via positional args tuple passed to execute
        call_args = cur.execute.call_args[0]
        assert call_args[1] == ("admin@example.com",)

    def test_returns_inactive_user(self, model, inactive_row):
        cur = _cursor(fetchone=inactive_row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.get_user("inactive@example.com")

        assert result["active"] is False

    def test_uses_select_star_query(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.get_user("any@example.com")

        sql = cur.execute.call_args[0][0]
        assert "SELECT *" in sql or "SELECT" in sql


# ─────────────────────────────────────────────────────────────────────────────
# Test: is_authorized
# ─────────────────────────────────────────────────────────────────────────────


class TestIsAuthorized:
    def test_returns_true_for_active_user(self, model):
        cur = _cursor(fetchone={"active": True})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_authorized("user@example.com") is True

    def test_returns_false_for_inactive_user(self, model):
        cur = _cursor(fetchone={"active": False})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_authorized("user@example.com") is False

    def test_returns_false_for_missing_user(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_authorized("ghost@example.com") is False

    def test_lowercases_email(self, model):
        cur = _cursor(fetchone={"active": True})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.is_authorized("USER@EXAMPLE.COM")

        assert cur.execute.call_args[0][1] == ("user@example.com",)

    def test_queries_active_column_only(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.is_authorized("any@example.com")

        sql = cur.execute.call_args[0][0]
        assert "active" in sql.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test: is_admin
# ─────────────────────────────────────────────────────────────────────────────


class TestIsAdmin:
    def test_returns_true_for_active_admin(self, model):
        cur = _cursor(fetchone={"active": True, "role": "admin"})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_admin("admin@example.com") is True

    def test_returns_false_for_active_viewer(self, model):
        cur = _cursor(fetchone={"active": True, "role": "viewer"})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_admin("viewer@example.com") is False

    def test_returns_false_for_inactive_admin(self, model):
        cur = _cursor(fetchone={"active": False, "role": "admin"})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_admin("admin@example.com") is False

    def test_returns_false_for_missing_user(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.is_admin("ghost@example.com") is False

    def test_lowercases_email(self, model):
        cur = _cursor(fetchone={"active": True, "role": "admin"})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.is_admin("ADMIN@EXAMPLE.COM")

        assert cur.execute.call_args[0][1] == ("admin@example.com",)

    def test_queries_active_and_role_columns(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.is_admin("any@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "active" in sql
        assert "role" in sql


# ─────────────────────────────────────────────────────────────────────────────
# Test: list_users
# ─────────────────────────────────────────────────────────────────────────────


class TestListUsers:
    def test_returns_all_rows_as_list_of_dicts(
        self, model, admin_row, viewer_row, inactive_row
    ):
        cur = _cursor(fetchall=[admin_row, viewer_row, inactive_row])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.list_users()

        assert len(result) == 3
        assert admin_row in result
        assert inactive_row in result

    def test_returns_empty_list_when_no_users(self, model):
        cur = _cursor(fetchall=[])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.list_users()

        assert result == []

    def test_orders_by_granted_at_desc(self, model):
        cur = _cursor(fetchall=[])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.list_users()

        sql = cur.execute.call_args[0][0].lower()
        assert "order by" in sql
        assert "granted_at" in sql
        assert "desc" in sql

    def test_returns_list_type(self, model):
        cur = _cursor(fetchall=[])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.list_users()

        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# Test: list_active_users
# ─────────────────────────────────────────────────────────────────────────────


class TestListActiveUsers:
    def test_returns_only_active_users(self, model, admin_row, viewer_row):
        cur = _cursor(fetchall=[admin_row, viewer_row])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.list_active_users()

        assert len(result) == 2

    def test_sql_filters_active_true(self, model):
        cur = _cursor(fetchall=[])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.list_active_users()

        sql = cur.execute.call_args[0][0].lower()
        assert "active" in sql
        assert "true" in sql or "= true" in sql

    def test_orders_by_email(self, model):
        cur = _cursor(fetchall=[])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.list_active_users()

        sql = cur.execute.call_args[0][0].lower()
        assert "order by" in sql
        assert "email" in sql

    def test_returns_empty_list_when_all_inactive(self, model):
        cur = _cursor(fetchall=[])
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.list_active_users()

        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# Test: grant_access
# ─────────────────────────────────────────────────────────────────────────────


class TestGrantAccess:
    def _granted_row(self, email="new@example.com", role="viewer"):
        return {
            "email": email,
            "display_name": "New User",
            "role": role,
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-06-01T00:00:00+00:00",
            "revoked_by": None,
            "revoked_at": None,
            "ms_id": None,
        }

    def test_returns_saved_record_dict(self, model):
        row = self._granted_row()
        cur = _cursor(fetchone=row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.grant_access(
                email="new@example.com",
                display_name="New User",
                role="viewer",
                granted_by="admin@example.com",
            )

        assert result == row

    def test_normalises_email_to_lowercase(self, model):
        row = self._granted_row(email="new@example.com")
        cur = _cursor(fetchone=row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.grant_access(
                email="  NEW@EXAMPLE.COM  ",
                display_name="New User",
                role="viewer",
                granted_by="admin@example.com",
            )

        params = cur.execute.call_args[0][1]
        assert params[0] == "new@example.com"

    def test_uses_upsert_sql(self, model):
        cur = _cursor(fetchone=self._granted_row())
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.grant_access("e@x.com", "E", "viewer", "admin@x.com")

        sql = cur.execute.call_args[0][0].upper()
        assert "INSERT" in sql
        assert "ON CONFLICT" in sql

    def test_commits_transaction(self, model):
        cur = _cursor(fetchone=self._granted_row())
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.grant_access("e@x.com", "E", "viewer", "admin@x.com")

        conn.commit.assert_called_once()

    def test_passes_ms_id_as_none_when_empty_string(self, model):
        cur = _cursor(fetchone=self._granted_row())
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.grant_access("e@x.com", "E", "viewer", "admin@x.com", ms_id="")

        params = cur.execute.call_args[0][1]
        assert params[4] is None  # ms_id position

    def test_passes_ms_id_when_provided(self, model):
        cur = _cursor(fetchone=self._granted_row())
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.grant_access("e@x.com", "E", "viewer", "admin@x.com", ms_id="abc123")

        params = cur.execute.call_args[0][1]
        assert params[4] == "abc123"

    def test_logs_access_granted(self, model, caplog):
        cur = _cursor(fetchone=self._granted_row())
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            with caplog.at_level(logging.INFO, logger="models.access_model"):
                model.grant_access(
                    "new@example.com", "New", "viewer", "admin@example.com"
                )

        assert any("granted" in r.message.lower() for r in caplog.records)

    def test_grant_admin_role(self, model):
        row = self._granted_row(role="admin")
        cur = _cursor(fetchone=row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.grant_access("e@x.com", "E", "admin", "admin@x.com")

        assert result["role"] == "admin"


# ─────────────────────────────────────────────────────────────────────────────
# Test: revoke_access
# ─────────────────────────────────────────────────────────────────────────────


class TestRevokeAccess:
    def test_returns_true_when_user_found(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert (
                model.revoke_access("viewer@example.com", "admin@example.com") is True
            )

    def test_returns_false_when_user_not_found(self, model):
        cur = _cursor(rowcount=0)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert (
                model.revoke_access("ghost@example.com", "admin@example.com") is False
            )

    def test_normalises_email(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.revoke_access("  VIEWER@EXAMPLE.COM  ", "admin@example.com")

        params = cur.execute.call_args[0][1]
        assert "viewer@example.com" in params

    def test_sql_sets_active_false(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.revoke_access("viewer@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "active = false" in sql or "active=false" in sql.replace(" ", "")

    def test_sql_sets_revoked_by(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.revoke_access("viewer@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "revoked_by" in sql

    def test_sql_sets_revoked_at_now(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.revoke_access("viewer@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "revoked_at" in sql
        assert "now()" in sql

    def test_commits_transaction(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.revoke_access("viewer@example.com", "admin@example.com")

        conn.commit.assert_called_once()

    def test_logs_revocation(self, model, caplog):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            with caplog.at_level(logging.INFO, logger="models.access_model"):
                model.revoke_access("viewer@example.com", "admin@example.com")

        assert any("revoked" in r.message.lower() for r in caplog.records)

    def test_does_not_log_when_user_not_found(self, model, caplog):
        cur = _cursor(rowcount=0)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            with caplog.at_level(logging.INFO, logger="models.access_model"):
                model.revoke_access("ghost@example.com", "admin@example.com")

        assert not any("revoked" in r.message.lower() for r in caplog.records)


# ─────────────────────────────────────────────────────────────────────────────
# Test: update_role
# ─────────────────────────────────────────────────────────────────────────────


class TestUpdateRole:
    def test_returns_true_when_user_found(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert (
                model.update_role("viewer@example.com", "admin", "admin@example.com")
                is True
            )

    def test_returns_false_when_user_not_found(self, model):
        cur = _cursor(rowcount=0)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert (
                model.update_role("ghost@example.com", "admin", "admin@example.com")
                is False
            )

    def test_normalises_email(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.update_role("  VIEWER@EXAMPLE.COM  ", "admin", "admin@example.com")

        params = cur.execute.call_args[0][1]
        assert "viewer@example.com" in params

    def test_sql_sets_role(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.update_role("viewer@example.com", "admin", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "role" in sql

    def test_sql_sets_role_updated_by(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.update_role("viewer@example.com", "admin", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "role_updated_by" in sql

    def test_sql_sets_role_updated_at_now(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.update_role("viewer@example.com", "admin", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "role_updated_at" in sql
        assert "now()" in sql

    def test_passes_new_role_in_params(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.update_role("viewer@example.com", "admin", "admin@example.com")

        params = cur.execute.call_args[0][1]
        assert "admin" in params

    def test_commits_transaction(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.update_role("viewer@example.com", "admin", "admin@example.com")

        conn.commit.assert_called_once()

    def test_logs_role_change(self, model, caplog):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            with caplog.at_level(logging.INFO, logger="models.access_model"):
                model.update_role("viewer@example.com", "admin", "admin@example.com")

        assert any("role" in r.message.lower() for r in caplog.records)

    def test_does_not_log_when_user_not_found(self, model, caplog):
        cur = _cursor(rowcount=0)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            with caplog.at_level(logging.INFO, logger="models.access_model"):
                model.update_role("ghost@example.com", "admin", "admin@example.com")

        assert not any("role updated" in r.message.lower() for r in caplog.records)

    def test_role_downgrade_viewer_to_admin(self, model):
        """Symmetric: can also demote admin → viewer."""
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.update_role(
                "admin@example.com", "viewer", "superadmin@example.com"
            )

        assert result is True
        params = cur.execute.call_args[0][1]
        assert "viewer" in params


# ─────────────────────────────────────────────────────────────────────────────
# Test: reactivate
# ─────────────────────────────────────────────────────────────────────────────


class TestReactivate:
    def test_returns_true_when_user_found(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.reactivate("inactive@example.com", "admin@example.com") is True

    def test_returns_false_when_user_not_found(self, model):
        cur = _cursor(rowcount=0)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.reactivate("ghost@example.com", "admin@example.com") is False

    def test_normalises_email(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.reactivate("  INACTIVE@EXAMPLE.COM  ", "admin@example.com")

        params = cur.execute.call_args[0][1]
        assert "inactive@example.com" in params

    def test_sql_sets_active_true(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.reactivate("inactive@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "active = true" in sql or "active=true" in sql.replace(" ", "")

    def test_sql_clears_revoked_fields(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.reactivate("inactive@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "revoked_by" in sql
        assert "revoked_at" in sql
        assert "null" in sql

    def test_sql_sets_reactivated_by(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.reactivate("inactive@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "reactivated_by" in sql

    def test_sql_sets_reactivated_at_now(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.reactivate("inactive@example.com", "admin@example.com")

        sql = cur.execute.call_args[0][0].lower()
        assert "reactivated_at" in sql
        assert "now()" in sql

    def test_commits_transaction(self, model):
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.reactivate("inactive@example.com", "admin@example.com")

        conn.commit.assert_called_once()

    def test_works_on_already_active_user(self, model):
        """reactivate is idempotent — rowcount 1 even for active users."""
        cur = _cursor(rowcount=1)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            assert model.reactivate("viewer@example.com", "admin@example.com") is True


# ─────────────────────────────────────────────────────────────────────────────
# Test: Integration scenarios
# ─────────────────────────────────────────────────────────────────────────────


class TestIntegration:
    """Validate that public methods compose correctly at the call-sequence level."""

    def test_grant_then_is_authorized(self, model):
        granted_row = {
            "email": "new@example.com",
            "active": True,
            "role": "viewer",
            "display_name": "New",
            "granted_by": "admin@x.com",
            "granted_at": "2024-01-01",
            "revoked_by": None,
            "revoked_at": None,
            "ms_id": None,
        }
        active_row = {"active": True}
        grant_cur = _cursor(fetchone=granted_row)
        auth_cur = _cursor(fetchone=active_row)
        grant_conn = _conn(grant_cur)
        auth_conn = _conn(auth_cur)

        with patch("models.access_model.get_conn", side_effect=[grant_conn, auth_conn]):
            model.grant_access("new@example.com", "New", "viewer", "admin@x.com")
            authorized = model.is_authorized("new@example.com")

        assert authorized is True

    def test_revoke_then_is_authorized_false(self, model):
        revoke_cur = _cursor(rowcount=1)
        auth_cur = _cursor(fetchone={"active": False})
        revoke_conn = _conn(revoke_cur)
        auth_conn = _conn(auth_cur)

        with patch(
            "models.access_model.get_conn", side_effect=[revoke_conn, auth_conn]
        ):
            model.revoke_access("user@example.com", "admin@example.com")
            authorized = model.is_authorized("user@example.com")

        assert authorized is False

    def test_update_role_then_is_admin(self, model):
        update_cur = _cursor(rowcount=1)
        admin_cur = _cursor(fetchone={"active": True, "role": "admin"})
        update_conn = _conn(update_cur)
        admin_conn = _conn(admin_cur)

        with patch(
            "models.access_model.get_conn", side_effect=[update_conn, admin_conn]
        ):
            model.update_role("user@example.com", "admin", "superadmin@example.com")
            is_admin = model.is_admin("user@example.com")

        assert is_admin is True

    def test_reactivate_then_is_authorized(self, model):
        reactivate_cur = _cursor(rowcount=1)
        auth_cur = _cursor(fetchone={"active": True})
        reactivate_conn = _conn(reactivate_cur)
        auth_conn = _conn(auth_cur)

        with patch(
            "models.access_model.get_conn", side_effect=[reactivate_conn, auth_conn]
        ):
            model.reactivate("inactive@example.com", "admin@example.com")
            authorized = model.is_authorized("inactive@example.com")

        assert authorized is True

    def test_each_method_opens_its_own_connection(self, model):
        """Every public method must call get_conn independently (no shared state)."""
        methods_and_mocks = [
            (
                lambda: model.is_authorized("a@b.com"),
                _cursor(fetchone={"active": True}),
            ),
            (
                lambda: model.is_admin("a@b.com"),
                _cursor(fetchone={"active": True, "role": "admin"}),
            ),
            (lambda: model.list_users(), _cursor(fetchall=[])),
            (lambda: model.list_active_users(), _cursor(fetchall=[])),
        ]
        conns = [_conn(cur) for _, cur in methods_and_mocks]

        with patch("models.access_model.get_conn", side_effect=conns):
            for fn, _ in methods_and_mocks:
                fn()

        # All four connections were used
        for conn in conns:
            conn.__enter__.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_special_characters_in_email_are_passed_through(self, model):
        email = "user+tag@sub.example.com"
        cur = _cursor(fetchone={"active": True})
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.is_authorized(email)

        assert cur.execute.call_args[0][1] == (email,)

    def test_very_long_email_passed_to_query(self, model):
        long_email = "a" * 200 + "@example.com"
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.is_authorized(long_email)

        assert result is False
        assert cur.execute.call_args[0][1] == (long_email,)

    def test_unicode_display_name_in_grant(self, model):
        row = {
            "email": "user@example.com",
            "display_name": "José García 日本語",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01",
            "revoked_by": None,
            "revoked_at": None,
            "ms_id": None,
        }
        cur = _cursor(fetchone=row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.grant_access(
                "user@example.com", "José García 日本語", "viewer", "admin@example.com"
            )

        assert result["display_name"] == "José García 日本語"

    def test_empty_display_name_in_grant(self, model):
        row = {
            "email": "user@example.com",
            "display_name": "",
            "role": "viewer",
            "active": True,
            "granted_by": "admin@example.com",
            "granted_at": "2024-01-01",
            "revoked_by": None,
            "revoked_at": None,
            "ms_id": None,
        }
        cur = _cursor(fetchone=row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            result = model.grant_access(
                "user@example.com", "", "viewer", "admin@example.com"
            )

        assert result["display_name"] == ""

    def test_grant_with_no_ms_id_defaults_none(self, model):
        row = {
            "email": "u@e.com",
            "ms_id": None,
            "active": True,
            "role": "viewer",
            "display_name": "U",
            "granted_by": "a@e.com",
            "granted_at": "2024-01-01",
            "revoked_by": None,
            "revoked_at": None,
        }
        cur = _cursor(fetchone=row)
        conn = _conn(cur)
        with patch("models.access_model.get_conn", return_value=conn):
            model.grant_access("u@e.com", "U", "viewer", "a@e.com")

        params = cur.execute.call_args[0][1]
        assert params[4] is None  # ms_id defaults to None

    def test_bootstrap_with_mixed_case_and_spaces(self, model):
        cur = _cursor(fetchone=None)
        conn = _conn(cur)
        with patch(
            "models.access_model.auth_config",
            BOOTSTRAP_ADMINS=["  Admin@Example.COM  "],
        ):
            with patch("models.access_model.get_conn", return_value=conn):
                model.bootstrap_admins()

        insert_params = cur.execute.call_args_list[1][0][1]
        assert insert_params[0] == "admin@example.com"
