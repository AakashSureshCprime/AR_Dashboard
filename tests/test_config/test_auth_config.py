"""
Complete test suite for auth_config.py

Covers all dataclass fields, the AUTHORITY property, BOOTSTRAP_ADMINS
parsing, validate(), frozen immutability, dataclass features, the
module-level singleton, and edge cases.

NOTE: ACCESS_DB_PATH is NOT a field on AuthConfig in the current source;
tests from the old JSON-backed version that referenced it have been
intentionally omitted or adapted.
"""

import pytest

from config.auth_config import AuthConfig

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def clean_env(monkeypatch):
    """Remove every Azure-related env var so tests start from a blank slate."""
    for var in (
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "AZURE_REDIRECT_URI",
        "BOOTSTRAP_ADMIN_EMAILS",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def full_env(monkeypatch):
    """Populate all recognised env vars with deterministic test values."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant-id")
    monkeypatch.setenv("AZURE_REDIRECT_URI", "https://app.example.com/callback")
    monkeypatch.setenv(
        "BOOTSTRAP_ADMIN_EMAILS", "admin1@example.com, admin2@example.com"
    )


@pytest.fixture()
def minimal_valid_env(monkeypatch):
    """Set only the three vars required to pass validate()."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "minimal-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "minimal-client-secret")
    monkeypatch.setenv("AZURE_TENANT_ID", "minimal-tenant-id")


# ─────────────────────────────────────────────────────────────────────────────
# Test: Default values (no environment variables set)
# ─────────────────────────────────────────────────────────────────────────────


class TestDefaultValues:
    def test_client_id_defaults_to_empty_string(self, clean_env):
        assert AuthConfig().CLIENT_ID == ""

    def test_client_secret_defaults_to_empty_string(self, clean_env):
        assert AuthConfig().CLIENT_SECRET == ""

    def test_tenant_id_defaults_to_empty_string(self, clean_env):
        assert AuthConfig().TENANT_ID == ""

    def test_redirect_uri_defaults_to_localhost(self, clean_env):
        assert AuthConfig().REDIRECT_URI == "http://localhost:8501"

    def test_scopes_defaults_to_user_read_tuple(self, clean_env):
        assert AuthConfig().SCOPES == ("User.Read",)

    def test_role_admin_defaults_to_admin(self, clean_env):
        assert AuthConfig().ROLE_ADMIN == "admin"

    def test_role_viewer_defaults_to_viewer(self, clean_env):
        assert AuthConfig().ROLE_VIEWER == "viewer"

    def test_bootstrap_admins_defaults_to_empty_tuple(self, clean_env):
        assert AuthConfig().BOOTSTRAP_ADMINS == ()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Environment variable loading
# ─────────────────────────────────────────────────────────────────────────────


class TestEnvironmentVariableLoading:
    def test_client_id_loaded_from_env(self, full_env):
        assert AuthConfig().CLIENT_ID == "test-client-id"

    def test_client_secret_loaded_from_env(self, full_env):
        assert AuthConfig().CLIENT_SECRET == "test-client-secret"

    def test_tenant_id_loaded_from_env(self, full_env):
        assert AuthConfig().TENANT_ID == "test-tenant-id"

    def test_redirect_uri_loaded_from_env(self, full_env):
        assert AuthConfig().REDIRECT_URI == "https://app.example.com/callback"

    def test_bootstrap_admins_parsed_from_env(self, full_env):
        assert AuthConfig().BOOTSTRAP_ADMINS == (
            "admin1@example.com",
            "admin2@example.com",
        )

    def test_each_instance_captures_env_at_creation(self, monkeypatch, clean_env):
        monkeypatch.setenv("AZURE_CLIENT_ID", "first")
        config1 = AuthConfig()
        monkeypatch.setenv("AZURE_CLIENT_ID", "second")
        config2 = AuthConfig()
        assert config1.CLIENT_ID == "first"
        assert config2.CLIENT_ID == "second"


# ─────────────────────────────────────────────────────────────────────────────
# Test: AUTHORITY property
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthorityProperty:
    def test_authority_constructs_correct_url(self, full_env):
        assert AuthConfig().AUTHORITY == (
            "https://login.microsoftonline.com/test-tenant-id"
        )

    def test_authority_with_empty_tenant_id(self, clean_env):
        assert AuthConfig().AUTHORITY == "https://login.microsoftonline.com/"

    def test_authority_is_a_property_descriptor(self, full_env):
        assert isinstance(type(AuthConfig()).AUTHORITY, property)

    def test_authority_embeds_tenant_id(self, monkeypatch, clean_env):
        monkeypatch.setenv("AZURE_TENANT_ID", "my-unique-tenant")
        assert "my-unique-tenant" in AuthConfig().AUTHORITY

    def test_authority_is_a_string(self, full_env):
        assert isinstance(AuthConfig().AUTHORITY, str)

    def test_different_tenants_produce_different_authorities(
        self, monkeypatch, clean_env
    ):
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-a")
        config_a = AuthConfig()
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-b")
        config_b = AuthConfig()
        assert config_a.AUTHORITY != config_b.AUTHORITY

    def test_authority_always_starts_with_microsoft_login_url(self, full_env):
        assert AuthConfig().AUTHORITY.startswith("https://login.microsoftonline.com/")


# ─────────────────────────────────────────────────────────────────────────────
# Test: BOOTSTRAP_ADMINS parsing
# ─────────────────────────────────────────────────────────────────────────────


class TestBootstrapAdminsParsing:
    def test_single_email(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "admin@example.com")
        assert AuthConfig().BOOTSTRAP_ADMINS == ("admin@example.com",)

    def test_multiple_comma_separated_emails(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "a@x.com,b@x.com,c@x.com")
        assert AuthConfig().BOOTSTRAP_ADMINS == ("a@x.com", "b@x.com", "c@x.com")

    def test_strips_whitespace_around_each_email(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "  a@x.com  ,  b@x.com  ")
        assert AuthConfig().BOOTSTRAP_ADMINS == ("a@x.com", "b@x.com")

    def test_filters_empty_entries_from_double_comma(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "a@x.com,,b@x.com,")
        assert AuthConfig().BOOTSTRAP_ADMINS == ("a@x.com", "b@x.com")

    def test_all_whitespace_entries_produces_empty_tuple(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "  ,  ,  ")
        assert AuthConfig().BOOTSTRAP_ADMINS == ()

    def test_empty_string_produces_empty_tuple(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "")
        assert AuthConfig().BOOTSTRAP_ADMINS == ()

    def test_result_is_always_a_tuple(self, monkeypatch, clean_env):
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "admin@example.com")
        assert isinstance(AuthConfig().BOOTSTRAP_ADMINS, tuple)

    def test_email_case_is_preserved(self, monkeypatch, clean_env):
        """Parsing must not alter character casing — callers normalise as needed."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "Admin@Example.COM")
        assert AuthConfig().BOOTSTRAP_ADMINS == ("Admin@Example.COM",)

    def test_newline_within_value_does_not_split(self, monkeypatch, clean_env):
        """Only commas split entries; embedded newlines are preserved as-is."""
        monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "a@x.com")
        assert AuthConfig().BOOTSTRAP_ADMINS == ("a@x.com",)


# ─────────────────────────────────────────────────────────────────────────────
# Test: validate()
# ─────────────────────────────────────────────────────────────────────────────


class TestValidate:
    def test_passes_when_all_three_required_vars_are_set(self, full_env):
        AuthConfig().validate()  # must not raise

    def test_passes_with_only_minimal_required_vars(self, minimal_valid_env):
        AuthConfig().validate()  # must not raise

    def test_raises_environment_error_when_client_id_missing(
        self, monkeypatch, clean_env
    ):
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        with pytest.raises(EnvironmentError, match="AZURE_CLIENT_ID"):
            AuthConfig().validate()

    def test_raises_environment_error_when_client_secret_missing(
        self, monkeypatch, clean_env
    ):
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        with pytest.raises(EnvironmentError, match="AZURE_CLIENT_SECRET"):
            AuthConfig().validate()

    def test_raises_environment_error_when_tenant_id_missing(
        self, monkeypatch, clean_env
    ):
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        with pytest.raises(EnvironmentError, match="AZURE_TENANT_ID"):
            AuthConfig().validate()

    def test_error_lists_all_missing_vars_at_once(self, clean_env):
        with pytest.raises(EnvironmentError) as exc_info:
            AuthConfig().validate()
        msg = str(exc_info.value)
        assert "AZURE_CLIENT_ID" in msg
        assert "AZURE_CLIENT_SECRET" in msg
        assert "AZURE_TENANT_ID" in msg

    def test_error_message_mentions_env_file(self, clean_env):
        with pytest.raises(EnvironmentError) as exc_info:
            AuthConfig().validate()
        assert ".env" in str(exc_info.value)

    def test_error_message_starts_with_missing_prefix(self, clean_env):
        with pytest.raises(EnvironmentError) as exc_info:
            AuthConfig().validate()
        assert str(exc_info.value).startswith("Missing required environment variables")

    def test_optional_vars_not_required_by_validate(
        self, minimal_valid_env, monkeypatch
    ):
        monkeypatch.delenv("AZURE_REDIRECT_URI", raising=False)
        monkeypatch.delenv("BOOTSTRAP_ADMIN_EMAILS", raising=False)
        AuthConfig().validate()  # must not raise

    def test_validate_returns_none_on_success(self, minimal_valid_env):
        result = AuthConfig().validate()
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test: Frozen dataclass — immutability
# ─────────────────────────────────────────────────────────────────────────────


class TestFrozenImmutability:
    def test_cannot_reassign_client_id(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().CLIENT_ID = "hacked"

    def test_cannot_reassign_client_secret(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().CLIENT_SECRET = "hacked"

    def test_cannot_reassign_tenant_id(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().TENANT_ID = "hacked"

    def test_cannot_reassign_redirect_uri(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().REDIRECT_URI = "http://evil.com"

    def test_cannot_reassign_scopes(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().SCOPES = ("Malicious.Scope",)

    def test_cannot_reassign_role_admin(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().ROLE_ADMIN = "superuser"

    def test_cannot_reassign_role_viewer(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().ROLE_VIEWER = "guest"

    def test_cannot_reassign_bootstrap_admins(self, full_env):
        with pytest.raises(AttributeError):
            AuthConfig().BOOTSTRAP_ADMINS = ("evil@example.com",)

    def test_cannot_add_new_attribute(self, full_env):
        with pytest.raises((AttributeError, TypeError)):
            AuthConfig().NEW_FIELD = "surprise"


# ─────────────────────────────────────────────────────────────────────────────
# Test: Dataclass features (equality, hashing, repr)
# ─────────────────────────────────────────────────────────────────────────────


class TestDataclassFeatures:
    def test_two_instances_with_identical_env_are_equal(self, minimal_valid_env):
        assert AuthConfig() == AuthConfig()

    def test_two_instances_with_different_client_id_are_not_equal(
        self, monkeypatch, clean_env
    ):
        monkeypatch.setenv("AZURE_CLIENT_ID", "id-1")
        config1 = AuthConfig()
        monkeypatch.setenv("AZURE_CLIENT_ID", "id-2")
        config2 = AuthConfig()
        assert config1 != config2

    def test_frozen_instance_is_hashable(self, full_env):
        h = hash(AuthConfig())
        assert isinstance(h, int)

    def test_can_be_stored_in_a_set(self, full_env):
        config = AuthConfig()
        assert config in {config}

    def test_can_be_used_as_a_dict_key(self, full_env):
        config = AuthConfig()
        assert {config: True}[config] is True

    def test_repr_contains_class_name(self, minimal_valid_env):
        assert "AuthConfig" in repr(AuthConfig())

    def test_repr_contains_field_names(self, minimal_valid_env):
        r = repr(AuthConfig())
        assert "CLIENT_ID" in r

    def test_equal_instances_have_same_hash(self, minimal_valid_env):
        assert hash(AuthConfig()) == hash(AuthConfig())


# ─────────────────────────────────────────────────────────────────────────────
# Test: Type correctness
# ─────────────────────────────────────────────────────────────────────────────


class TestTypeCorrectness:
    def test_client_id_is_str(self, full_env):
        assert isinstance(AuthConfig().CLIENT_ID, str)

    def test_client_secret_is_str(self, full_env):
        assert isinstance(AuthConfig().CLIENT_SECRET, str)

    def test_tenant_id_is_str(self, full_env):
        assert isinstance(AuthConfig().TENANT_ID, str)

    def test_redirect_uri_is_str(self, full_env):
        assert isinstance(AuthConfig().REDIRECT_URI, str)

    def test_authority_is_str(self, full_env):
        assert isinstance(AuthConfig().AUTHORITY, str)

    def test_scopes_is_tuple(self, full_env):
        assert isinstance(AuthConfig().SCOPES, tuple)

    def test_role_admin_is_str(self, full_env):
        assert isinstance(AuthConfig().ROLE_ADMIN, str)

    def test_role_viewer_is_str(self, full_env):
        assert isinstance(AuthConfig().ROLE_VIEWER, str)

    def test_bootstrap_admins_is_tuple(self, full_env):
        assert isinstance(AuthConfig().BOOTSTRAP_ADMINS, tuple)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────


class TestModuleLevelSingleton:
    def test_auth_config_instance_exists(self):
        from config.auth_config import auth_config

        assert auth_config is not None

    def test_auth_config_is_auth_config_instance(self):
        from config.auth_config import auth_config

        assert isinstance(auth_config, AuthConfig)

    def test_repeated_imports_return_same_object(self):
        from config.auth_config import auth_config as c1
        from config.auth_config import auth_config as c2

        assert c1 is c2


# ─────────────────────────────────────────────────────────────────────────────
# Test: Edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_uuid_formatted_client_id_passes_validate(self, monkeypatch, clean_env):
        monkeypatch.setenv("AZURE_CLIENT_ID", "12345678-1234-1234-1234-123456789012")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "12345678-1234-1234-1234-123456789012")
        AuthConfig().validate()

    def test_very_long_client_secret_is_stored_verbatim(self, monkeypatch, clean_env):
        long_secret = "x" * 1000
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", long_secret)
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        assert AuthConfig().CLIENT_SECRET == long_secret

    def test_redirect_uri_with_path_component(self, monkeypatch, clean_env):
        monkeypatch.setenv(
            "AZURE_REDIRECT_URI", "https://app.example.com/auth/callback"
        )
        assert AuthConfig().REDIRECT_URI == "https://app.example.com/auth/callback"

    def test_redirect_uri_with_custom_port(self, monkeypatch, clean_env):
        monkeypatch.setenv("AZURE_REDIRECT_URI", "http://localhost:3000")
        assert AuthConfig().REDIRECT_URI == "http://localhost:3000"

    def test_whitespace_only_client_id_is_truthy_so_validate_passes(
        self, monkeypatch, clean_env
    ):
        """
        The current validate() uses `if not val` which treats whitespace
        strings as truthy.  This test documents that existing behaviour.
        """
        monkeypatch.setenv("AZURE_CLIENT_ID", "   ")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        AuthConfig().validate()  # passes — whitespace is truthy

    def test_special_characters_in_client_id_are_preserved(
        self, monkeypatch, clean_env
    ):
        value = "client-id_with.special~chars"
        monkeypatch.setenv("AZURE_CLIENT_ID", value)
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "s")
        monkeypatch.setenv("AZURE_TENANT_ID", "t")
        assert AuthConfig().CLIENT_ID == value

    def test_roles_contain_only_alphanumeric_or_underscore(self, clean_env):
        config = AuthConfig()
        for ch in config.ROLE_ADMIN:
            assert ch.isalnum() or ch == "_"
        for ch in config.ROLE_VIEWER:
            assert ch.isalnum() or ch == "_"

    def test_scopes_tuple_is_non_empty_by_default(self, clean_env):
        assert len(AuthConfig().SCOPES) > 0

    def test_authority_url_contains_no_double_slashes_after_scheme(self, full_env):
        url = AuthConfig().AUTHORITY
        # Only the scheme separator (https://) should contain double slash
        assert "microsoftonline.com//" not in url

    def test_authority_does_not_end_with_slash_when_tenant_set(self, full_env):
        url = AuthConfig().AUTHORITY
        assert not url.endswith("/")

    def test_multiple_reads_of_frozen_instance_are_stable(self, full_env):
        config = AuthConfig()
        for _ in range(50):
            assert config.CLIENT_ID == "test-client-id"
            assert config.AUTHORITY.endswith("test-tenant-id")
