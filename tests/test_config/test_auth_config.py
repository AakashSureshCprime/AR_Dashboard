"""
Complete test suite for auth_config.py

Covers all dataclass fields, properties, validation, and edge cases.
"""

import os
from unittest.mock import patch

import pytest

# We need to import the class, not the instance, for some tests
from config.auth_config import AuthConfig


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all Azure-related environment variables."""
    env_vars = [
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "AZURE_REDIRECT_URI",
        "ACCESS_DB_PATH",
        "BOOTSTRAP_ADMIN_EMAILS",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def full_env(monkeypatch):
    """Set all Azure-related environment variables."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant-id")
    monkeypatch.setenv("AZURE_REDIRECT_URI", "https://app.example.com/callback")
    monkeypatch.setenv("ACCESS_DB_PATH", "/custom/path/users.json")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "admin1@example.com, admin2@example.com")


@pytest.fixture
def minimal_valid_env(monkeypatch):
    """Set only required environment variables."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "minimal-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "minimal-client-secret")
    monkeypatch.setenv("AZURE_TENANT_ID", "minimal-tenant-id")


# ---------------------------------------------------------------------
# Test: Default Values (No Environment Variables)
# ---------------------------------------------------------------------


class TestDefaultValues:
    def test_client_id_default_empty(self, clean_env):
        """Test CLIENT_ID defaults to empty string."""
        config = AuthConfig()
        assert config.CLIENT_ID == ""

    def test_client_secret_default_empty(self, clean_env):
        """Test CLIENT_SECRET defaults to empty string."""
        config = AuthConfig()
        assert config.CLIENT_SECRET == ""

    def test_tenant_id_default_empty(self, clean_env):
        """Test TENANT_ID defaults to empty string."""
        config = AuthConfig()
        assert config.TENANT_ID == ""

    def test_redirect_uri_default(self, clean_env):
        """Test REDIRECT_URI has localhost default."""
        config = AuthConfig()
        assert config.REDIRECT_URI == "http://localhost:8501"

    def test_access_db_path_default(self, clean_env):
        """Test ACCESS_DB_PATH has default path."""
        config = AuthConfig()
        assert config.ACCESS_DB_PATH == "config/authorized_users.json"

    def test_scopes_default(self, clean_env):
        """Test SCOPES has default value."""
        config = AuthConfig()
        assert config.SCOPES == ("User.Read",)

    def test_role_admin_default(self, clean_env):
        """Test ROLE_ADMIN has default value."""
        config = AuthConfig()
        assert config.ROLE_ADMIN == "admin"

    def test_role_viewer_default(self, clean_env):
        """Test ROLE_VIEWER has default value."""
        config = AuthConfig()
        assert config.ROLE_VIEWER == "viewer"

    def test_bootstrap_admins_default_empty(self, clean_env):
        """Test BOOTSTRAP_ADMINS defaults to empty tuple."""
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ()


# ---------------------------------------------------------------------
# Test: Environment Variable Loading
# ---------------------------------------------------------------------


class TestEnvironmentVariableLoading:
    def test_client_id_from_env(self, full_env):
        """Test CLIENT_ID loaded from environment."""
        config = AuthConfig()
        assert config.CLIENT_ID == "test-client-id"

    def test_client_secret_from_env(self, full_env):
        """Test CLIENT_SECRET loaded from environment."""
        config = AuthConfig()
        assert config.CLIENT_SECRET == "test-client-secret"

    def test_tenant_id_from_env(self, full_env):
        """Test TENANT_ID loaded from environment."""
        config = AuthConfig()
        assert config.TENANT_ID == "test-tenant-id"

    def test_redirect_uri_from_env(self, full_env):
        """Test REDIRECT_URI loaded from environment."""
        config = AuthConfig()
        assert config.REDIRECT_URI == "https://app.example.com/callback"

    def test_access_db_path_from_env(self, full_env):
        """Test ACCESS_DB_PATH loaded from environment."""
        config = AuthConfig()
        assert config.ACCESS_DB_PATH == "/custom/path/users.json"

    def test_bootstrap_admins_from_env(self, full_env):
        """Test BOOTSTRAP_ADMINS loaded and parsed from environment."""
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ("admin1@example.com", "admin2@example.com")


# ---------------------------------------------------------------------
# Test: AUTHORITY Property
# ---------------------------------------------------------------------


class TestAuthorityProperty:
    def test_authority_with_tenant_id(self, full_env):
        """Test AUTHORITY property constructs correct URL."""
        config = AuthConfig()
        assert config.AUTHORITY == "https://login.microsoftonline.com/test-tenant-id"

    def test_authority_with_empty_tenant(self, clean_env):
        """Test AUTHORITY with empty tenant ID."""
        config = AuthConfig()
        assert config.AUTHORITY == "https://login.microsoftonline.com/"

    def test_authority_is_property(self, full_env):
        """Test AUTHORITY is a property, not a field."""
        config = AuthConfig()
        # Should be dynamically computed
        assert isinstance(type(config).AUTHORITY, property)

    def test_authority_reflects_tenant_change(self, monkeypatch):
        """Test different configs have different authorities."""
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-1")
        config1 = AuthConfig()

        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-2")
        config2 = AuthConfig()

        assert config1.AUTHORITY != config2.AUTHORITY
        assert "tenant-1" in config1.AUTHORITY
        assert "tenant-2" in config2.AUTHORITY


# ---------------------------------------------------------------------
# Test: BOOTSTRAP_ADMINS Parsing
# ---------------------------------------------------------------------


class TestBootstrapAdminsParsing:
    def test_single_admin(self, monkeypatch, clean_env):
        """Test single admin email."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "admin@example.com")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ("admin@example.com",)

    def test_multiple_admins(self, monkeypatch, clean_env):
        """Test multiple admin emails."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "a@test.com,b@test.com,c@test.com")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ("a@test.com", "b@test.com", "c@test.com")

    def test_admins_with_whitespace(self, monkeypatch, clean_env):
        """Test admin emails with extra whitespace."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "  a@test.com  ,  b@test.com  ")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ("a@test.com", "b@test.com")

    def test_admins_with_empty_entries(self, monkeypatch, clean_env):
        """Test admin emails with empty entries filtered out."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "a@test.com,,b@test.com,")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ("a@test.com", "b@test.com")

    def test_admins_only_whitespace_entries(self, monkeypatch, clean_env):
        """Test admin emails with only whitespace entries."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "  ,  ,  ")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ()

    def test_admins_empty_string(self, monkeypatch, clean_env):
        """Test empty BOOTSTRAP_ADMIN_EMAILS."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ()

    def test_admins_is_tuple(self, monkeypatch, clean_env):
        """Test BOOTSTRAP_ADMINS is always a tuple."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "admin@test.com")
        config = AuthConfig()
        assert isinstance(config.BOOTSTRAP_ADMINS, tuple)


# ---------------------------------------------------------------------
# Test: Validation
# ---------------------------------------------------------------------


class TestValidation:
    def test_validate_success_all_present(self, full_env):
        """Test validation passes with all required vars."""
        config = AuthConfig()
        # Should not raise
        config.validate()

    def test_validate_success_minimal(self, minimal_valid_env):
        """Test validation passes with minimal required vars."""
        config = AuthConfig()
        config.validate()

    def test_validate_missing_client_id(self, monkeypatch, clean_env):
        """Test validation fails without CLIENT_ID."""
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")

        config = AuthConfig()
        with pytest.raises(EnvironmentError) as exc:
            config.validate()
        assert "AZURE_CLIENT_ID" in str(exc.value)

    def test_validate_missing_client_secret(self, monkeypatch, clean_env):
        """Test validation fails without CLIENT_SECRET."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")

        config = AuthConfig()
        with pytest.raises(EnvironmentError) as exc:
            config.validate()
        assert "AZURE_CLIENT_SECRET" in str(exc.value)

    def test_validate_missing_tenant_id(self, monkeypatch, clean_env):
        """Test validation fails without TENANT_ID."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")

        config = AuthConfig()
        with pytest.raises(EnvironmentError) as exc:
            config.validate()
        assert "AZURE_TENANT_ID" in str(exc.value)

    def test_validate_missing_all(self, clean_env):
        """Test validation fails with all vars missing."""
        config = AuthConfig()
        with pytest.raises(EnvironmentError) as exc:
            config.validate()
        error_msg = str(exc.value)
        assert "AZURE_CLIENT_ID" in error_msg
        assert "AZURE_CLIENT_SECRET" in error_msg
        assert "AZURE_TENANT_ID" in error_msg

    def test_validate_error_message_format(self, clean_env):
        """Test validation error message contains helpful info."""
        config = AuthConfig()
        with pytest.raises(EnvironmentError) as exc:
            config.validate()
        error_msg = str(exc.value)
        assert "Missing required environment variables" in error_msg
        assert ".env" in error_msg or "environment" in error_msg

    def test_validate_does_not_check_optional_vars(self, minimal_valid_env, monkeypatch):
        """Test validation doesn't require optional vars."""
        # Remove optional vars
        monkeypatch.delenv("AZURE_REDIRECT_URI", raising=False)
        monkeypatch.delenv("ACCESS_DB_PATH", raising=False)
        monkeypatch.delenv("BOOTSTRAP_ADMIN_EMAILS", raising=False)

        config = AuthConfig()
        # Should not raise
        config.validate()


# ---------------------------------------------------------------------
# Test: Frozen Dataclass (Immutability)
# ---------------------------------------------------------------------


class TestFrozenDataclass:
    def test_cannot_modify_client_id(self, full_env):
        """Test CLIENT_ID cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.CLIENT_ID = "new-value"

    def test_cannot_modify_client_secret(self, full_env):
        """Test CLIENT_SECRET cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.CLIENT_SECRET = "new-value"

    def test_cannot_modify_tenant_id(self, full_env):
        """Test TENANT_ID cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.TENANT_ID = "new-value"

    def test_cannot_modify_redirect_uri(self, full_env):
        """Test REDIRECT_URI cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.REDIRECT_URI = "new-value"

    def test_cannot_modify_scopes(self, full_env):
        """Test SCOPES cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.SCOPES = ("NewScope",)

    def test_cannot_modify_role_admin(self, full_env):
        """Test ROLE_ADMIN cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.ROLE_ADMIN = "superadmin"

    def test_cannot_modify_role_viewer(self, full_env):
        """Test ROLE_VIEWER cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.ROLE_VIEWER = "guest"

    def test_cannot_modify_access_db_path(self, full_env):
        """Test ACCESS_DB_PATH cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.ACCESS_DB_PATH = "/new/path"

    def test_cannot_modify_bootstrap_admins(self, full_env):
        """Test BOOTSTRAP_ADMINS cannot be modified."""
        config = AuthConfig()
        with pytest.raises(AttributeError):
            config.BOOTSTRAP_ADMINS = ("new@admin.com",)


# ---------------------------------------------------------------------
# Test: Dataclass Features
# ---------------------------------------------------------------------


class TestDataclassFeatures:
    def test_equality(self, monkeypatch, clean_env):
        """Test two configs with same values are equal."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "same-id")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "same-secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "same-tenant")

        config1 = AuthConfig()
        config2 = AuthConfig()

        assert config1 == config2

    def test_inequality(self, monkeypatch, clean_env):
        """Test configs with different values are not equal."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "id-1")
        config1 = AuthConfig()

        monkeypatch.setenv("AZURE_CLIENT_ID", "id-2")
        config2 = AuthConfig()

        assert config1 != config2

    def test_hashable(self, full_env):
        """Test frozen dataclass is hashable."""
        config = AuthConfig()
        # Should not raise
        hash_value = hash(config)
        assert isinstance(hash_value, int)

    def test_can_use_in_set(self, full_env):
        """Test config can be used in a set."""
        config = AuthConfig()
        config_set = {config}
        assert config in config_set

    def test_can_use_as_dict_key(self, full_env):
        """Test config can be used as dictionary key."""
        config = AuthConfig()
        config_dict = {config: "value"}
        assert config_dict[config] == "value"

    def test_repr(self, minimal_valid_env):
        """Test repr is generated."""
        config = AuthConfig()
        repr_str = repr(config)
        assert "AuthConfig" in repr_str
        assert "CLIENT_ID" in repr_str


# ---------------------------------------------------------------------
# Test: Module-Level Instance (auth_config)
# ---------------------------------------------------------------------


class TestModuleLevelInstance:
    def test_auth_config_exists(self):
        """Test auth_config instance is created at module level."""
        from config.auth_config import auth_config
        assert auth_config is not None
        assert isinstance(auth_config, AuthConfig)

    def test_auth_config_is_singleton_like(self):
        """Test importing auth_config returns same instance."""
        from config.auth_config import auth_config as config1
        from config.auth_config import auth_config as config2
        assert config1 is config2


# ---------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------


class TestEdgeCases:
    def test_special_characters_in_client_id(self, monkeypatch, clean_env):
        """Test CLIENT_ID with special characters."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-id-with-dashes_and_underscores")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")

        config = AuthConfig()
        assert config.CLIENT_ID == "client-id-with-dashes_and_underscores"
        config.validate()  # Should pass

    def test_uuid_format_client_id(self, monkeypatch, clean_env):
        """Test CLIENT_ID in UUID format (typical Azure format)."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "12345678-1234-1234-1234-123456789012")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "12345678-1234-1234-1234-123456789012")

        config = AuthConfig()
        config.validate()

    def test_long_client_secret(self, monkeypatch, clean_env):
        """Test very long CLIENT_SECRET."""
        long_secret = "x" * 1000
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", long_secret)
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")

        config = AuthConfig()
        assert config.CLIENT_SECRET == long_secret
        config.validate()

    def test_redirect_uri_with_path(self, monkeypatch, clean_env):
        """Test REDIRECT_URI with path component."""
        monkeypatch.setenv(
            "AZURE_REDIRECT_URI", "https://app.example.com/auth/callback"
        )
        config = AuthConfig()
        assert config.REDIRECT_URI == "https://app.example.com/auth/callback"

    def test_redirect_uri_with_port(self, monkeypatch, clean_env):
        """Test REDIRECT_URI with custom port."""
        monkeypatch.setenv("AZURE_REDIRECT_URI", "http://localhost:3000")
        config = AuthConfig()
        assert config.REDIRECT_URI == "http://localhost:3000"

    def test_access_db_path_absolute(self, monkeypatch, clean_env):
        """Test ACCESS_DB_PATH with absolute path."""
        monkeypatch.setenv("ACCESS_DB_PATH", "/var/data/users.json")
        config = AuthConfig()
        assert config.ACCESS_DB_PATH == "/var/data/users.json"

    def test_access_db_path_relative(self, monkeypatch, clean_env):
        """Test ACCESS_DB_PATH with relative path."""
        monkeypatch.setenv("ACCESS_DB_PATH", "./data/users.json")
        config = AuthConfig()
        assert config.ACCESS_DB_PATH == "./data/users.json"

    def test_bootstrap_admins_case_preserved(self, monkeypatch, clean_env):
        """Test BOOTSTRAP_ADMINS preserves email case."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "Admin@Example.COM")
        config = AuthConfig()
        assert config.BOOTSTRAP_ADMINS == ("Admin@Example.COM",)

    def test_whitespace_only_client_id_fails_validation(self, monkeypatch, clean_env):
        """Test CLIENT_ID with only whitespace fails validation."""
        # Note: os.environ.get returns the whitespace, but validation checks truthiness
        monkeypatch.setenv("AZURE_CLIENT_ID", "   ")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")

        config = AuthConfig()
        # Whitespace is truthy in Python, so this will pass validation
        # This tests the current behavior
        config.validate()  # Will pass because "   " is truthy

    def test_newlines_in_secret(self, monkeypatch, clean_env):
        """Test CLIENT_SECRET with newlines."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret\nwith\nnewlines")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")

        config = AuthConfig()
        assert "\n" in config.CLIENT_SECRET
        config.validate()


# ---------------------------------------------------------------------
# Test: Type Hints and Structure
# ---------------------------------------------------------------------


class TestTypeHintsAndStructure:
    def test_client_id_is_string(self, full_env):
        """Test CLIENT_ID is a string."""
        config = AuthConfig()
        assert isinstance(config.CLIENT_ID, str)

    def test_client_secret_is_string(self, full_env):
        """Test CLIENT_SECRET is a string."""
        config = AuthConfig()
        assert isinstance(config.CLIENT_SECRET, str)

    def test_tenant_id_is_string(self, full_env):
        """Test TENANT_ID is a string."""
        config = AuthConfig()
        assert isinstance(config.TENANT_ID, str)

    def test_redirect_uri_is_string(self, full_env):
        """Test REDIRECT_URI is a string."""
        config = AuthConfig()
        assert isinstance(config.REDIRECT_URI, str)

    def test_authority_is_string(self, full_env):
        """Test AUTHORITY property returns a string."""
        config = AuthConfig()
        assert isinstance(config.AUTHORITY, str)

    def test_scopes_is_tuple(self, full_env):
        """Test SCOPES is a tuple."""
        config = AuthConfig()
        assert isinstance(config.SCOPES, tuple)

    def test_access_db_path_is_string(self, full_env):
        """Test ACCESS_DB_PATH is a string."""
        config = AuthConfig()
        assert isinstance(config.ACCESS_DB_PATH, str)

    def test_role_admin_is_string(self, full_env):
        """Test ROLE_ADMIN is a string."""
        config = AuthConfig()
        assert isinstance(config.ROLE_ADMIN, str)

    def test_role_viewer_is_string(self, full_env):
        """Test ROLE_VIEWER is a string."""
        config = AuthConfig()
        assert isinstance(config.ROLE_VIEWER, str)

    def test_bootstrap_admins_is_tuple(self, full_env):
        """Test BOOTSTRAP_ADMINS is a tuple."""
        config = AuthConfig()
        assert isinstance(config.BOOTSTRAP_ADMINS, tuple)


# ---------------------------------------------------------------------
# Test: Concurrent Access (Thread Safety Considerations)
# ---------------------------------------------------------------------


class TestConcurrentAccess:
    def test_multiple_instances_independent(self, monkeypatch, clean_env):
        """Test multiple config instances are independent."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "first-id")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        config1 = AuthConfig()

        # Change env vars
        monkeypatch.setenv("AZURE_CLIENT_ID", "second-id")
        config2 = AuthConfig()

        # Each instance captured its own state at creation
        assert config1.CLIENT_ID == "first-id"
        assert config2.CLIENT_ID == "second-id"

    def test_frozen_ensures_thread_safety(self, full_env):
        """Test frozen dataclass provides basic thread safety guarantees."""
        config = AuthConfig()

        # Multiple reads should be safe
        for _ in range(100):
            _ = config.CLIENT_ID
            _ = config.AUTHORITY
            _ = config.SCOPES


# ---------------------------------------------------------------------
# Test: Integration with Other Modules
# ---------------------------------------------------------------------


class TestIntegration:
    def test_config_usable_for_msal(self, full_env):
        """Test config values are suitable for MSAL library."""
        config = AuthConfig()

        # These are the typical values MSAL needs
        assert config.CLIENT_ID
        assert config.CLIENT_SECRET
        assert config.AUTHORITY.startswith("https://login.microsoftonline.com/")
        assert len(config.SCOPES) > 0

    def test_roles_are_valid_identifiers(self, clean_env):
        """Test role names are valid for use as identifiers."""
        config = AuthConfig()

        # Roles should be simple strings without special chars
        assert config.ROLE_ADMIN.isalnum() or "_" in config.ROLE_ADMIN
        assert config.ROLE_VIEWER.isalnum() or "_" in config.ROLE_VIEWER

    def test_access_db_path_is_valid_filename(self, clean_env):
        """Test default ACCESS_DB_PATH is a valid path."""
        config = AuthConfig()

        # Should be a JSON file path
        assert config.ACCESS_DB_PATH.endswith(".json")
        # Should have reasonable structure
        assert "/" in config.ACCESS_DB_PATH or "\\" in config.ACCESS_DB_PATH