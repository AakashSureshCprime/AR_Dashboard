import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests

import utils.sharepoint_fetch as sf


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setattr(sf, "TENANT_ID", "test-tenant-id")
    monkeypatch.setattr(sf, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(sf, "CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(sf, "SHAREPOINT_SITE", "test.sharepoint.com")
    monkeypatch.setattr(sf, "SITE_PATH", "/sites/TestSite")
    monkeypatch.setattr(sf, "FOLDER_PATH", "/TestFolder")
    monkeypatch.setattr(sf, "SOURCE_LINK", "")


@pytest.fixture
def sample_file_item():
    """Standard file item response from Graph API."""
    return {
        "name": "test_file.xlsx",
        "lastModifiedDateTime": "2024-06-15T10:30:00Z",
        "lastModifiedBy": {"user": {"displayName": "John Doe"}},
        "@microsoft.graph.downloadUrl": "https://download.example.com/file.xlsx",
        "id": "file-id-123",
        "size": 1024,
    }


@pytest.fixture
def sample_file_item_minimal():
    """File item with minimal properties."""
    return {
        "name": "minimal_file.xlsx",
        "lastModifiedDateTime": "2024-06-15T10:30:00Z",
    }


# ---------------------------------------------------------------------
# Test: get_token
# ---------------------------------------------------------------------


class TestGetToken:
    def test_get_token_success(self, monkeypatch, mock_env_vars):
        """Test successful token acquisition."""

        class DummyApp:
            def acquire_token_for_client(self, scopes):
                return {"access_token": "test_access_token_123"}

        monkeypatch.setattr(
            sf.msal, "ConfidentialClientApplication", lambda *a, **k: DummyApp()
        )

        token = sf.get_token()
        assert token == "test_access_token_123"

    def test_get_token_failure_no_access_token(self, monkeypatch, mock_env_vars):
        """Test token acquisition failure when no access_token returned."""

        class DummyApp:
            def acquire_token_for_client(self, scopes):
                return {"error": "invalid_client", "error_description": "Bad credentials"}

        monkeypatch.setattr(
            sf.msal, "ConfidentialClientApplication", lambda *a, **k: DummyApp()
        )

        with pytest.raises(Exception) as exc:
            sf.get_token()
        assert "Failed to get token" in str(exc.value)

    def test_get_token_empty_response(self, monkeypatch, mock_env_vars):
        """Test token acquisition with empty response."""

        class DummyApp:
            def acquire_token_for_client(self, scopes):
                return {}

        monkeypatch.setattr(
            sf.msal, "ConfidentialClientApplication", lambda *a, **k: DummyApp()
        )

        with pytest.raises(Exception) as exc:
            sf.get_token()
        assert "Failed to get token" in str(exc.value)

    def test_get_token_correct_scopes(self, monkeypatch, mock_env_vars):
        """Test that correct scopes are passed."""
        captured_scopes = []

        class DummyApp:
            def acquire_token_for_client(self, scopes):
                captured_scopes.extend(scopes)
                return {"access_token": "token"}

        monkeypatch.setattr(
            sf.msal, "ConfidentialClientApplication", lambda *a, **k: DummyApp()
        )

        sf.get_token()
        assert "https://graph.microsoft.com/.default" in captured_scopes

    def test_get_token_correct_authority(self, monkeypatch, mock_env_vars):
        """Test that correct authority URL is used."""
        captured_authority = []

        def mock_app(client_id, authority, client_credential):
            captured_authority.append(authority)
            mock = MagicMock()
            mock.acquire_token_for_client.return_value = {"access_token": "token"}
            return mock

        monkeypatch.setattr(sf.msal, "ConfidentialClientApplication", mock_app)

        sf.get_token()
        assert "https://login.microsoftonline.com/test-tenant-id" in captured_authority


# ---------------------------------------------------------------------
# Test: get_site_id
# ---------------------------------------------------------------------


class TestGetSiteId:
    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_site_id_success(self, mock_get, mock_env_vars):
        """Test successful site ID retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "site-id-456"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        site_id = sf.get_site_id(headers)

        assert site_id == "site-id-456"
        mock_get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_site_id_correct_url(self, mock_get, mock_env_vars):
        """Test that correct URL is constructed."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "site-id"}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        sf.get_site_id(headers)

        called_url = mock_get.call_args[0][0]
        assert "test.sharepoint.com" in called_url
        assert "/sites/TestSite" in called_url

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_site_id_http_error(self, mock_get, mock_env_vars):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        with pytest.raises(requests.HTTPError):
            sf.get_site_id(headers)

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_site_id_timeout(self, mock_get, mock_env_vars):
        """Test timeout handling."""
        mock_get.side_effect = requests.Timeout("Connection timed out")

        headers = {"Authorization": "Bearer token"}
        with pytest.raises(requests.Timeout):
            sf.get_site_id(headers)

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_site_id_uses_timeout(self, mock_get, mock_env_vars):
        """Test that REQUEST_TIMEOUT is used."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "site-id"}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        sf.get_site_id(headers)

        # Check timeout was passed
        assert "timeout" in mock_get.call_args[1]


# ---------------------------------------------------------------------
# Test: get_drive_id
# ---------------------------------------------------------------------


class TestGetDriveId:
    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_drive_id_success(self, mock_get):
        """Test successful drive ID retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": "drive-id-789", "name": "Documents"},
                {"id": "drive-id-other", "name": "Other"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        drive_id = sf.get_drive_id("site-id", headers)

        assert drive_id == "drive-id-789"  # First drive returned

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_drive_id_correct_url(self, mock_get):
        """Test that correct URL is constructed."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": [{"id": "drive-id"}]}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        sf.get_drive_id("my-site-id", headers)

        called_url = mock_get.call_args[0][0]
        assert "my-site-id" in called_url
        assert "/drives" in called_url

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_drive_id_empty_drives(self, mock_get):
        """Test behavior when no drives returned."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        with pytest.raises(IndexError):
            sf.get_drive_id("site-id", headers)

    @patch("utils.sharepoint_fetch.requests.get")
    def test_get_drive_id_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        with pytest.raises(requests.HTTPError):
            sf.get_drive_id("site-id", headers)


# ---------------------------------------------------------------------
# Test: list_files
# ---------------------------------------------------------------------


class TestListFiles:
    @patch("utils.sharepoint_fetch.requests.get")
    def test_list_files_success(self, mock_get, mock_env_vars, sample_file_item):
        """Test successful file listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": [sample_file_item]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        files = sf.list_files("drive-id", headers)

        assert len(files) == 1
        assert files[0]["name"] == "test_file.xlsx"

    @patch("utils.sharepoint_fetch.requests.get")
    def test_list_files_multiple(self, mock_get, mock_env_vars):
        """Test listing multiple files."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"name": "file1.xlsx", "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
                {"name": "file2.xlsx", "lastModifiedDateTime": "2024-01-02T00:00:00Z"},
                {"name": "file3.xlsx", "lastModifiedDateTime": "2024-01-03T00:00:00Z"},
            ]
        }
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        files = sf.list_files("drive-id", headers)

        assert len(files) == 3

    @patch("utils.sharepoint_fetch.requests.get")
    def test_list_files_empty(self, mock_get, mock_env_vars):
        """Test empty folder."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        files = sf.list_files("drive-id", headers)

        assert files == []

    @patch("utils.sharepoint_fetch.requests.get")
    def test_list_files_correct_url(self, mock_get, mock_env_vars):
        """Test that correct URL with folder path is constructed."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        sf.list_files("my-drive-id", headers)

        called_url = mock_get.call_args[0][0]
        assert "my-drive-id" in called_url
        assert "/TestFolder" in called_url
        assert "/children" in called_url


# ---------------------------------------------------------------------
# Test: _encode_share_url
# ---------------------------------------------------------------------


class TestEncodeShareUrl:
    def test_encode_share_url_basic(self):
        """Test basic URL encoding."""
        url = "https://example.sharepoint.com/share/file.xlsx"
        encoded = sf._encode_share_url(url)

        assert encoded.startswith("u!")
        # Verify it's valid base64 URL-safe encoding
        assert "+" not in encoded
        assert "/" not in encoded

    def test_encode_share_url_special_characters(self):
        """Test URL with special characters."""
        url = "https://example.com/path?query=value&other=test"
        encoded = sf._encode_share_url(url)

        assert encoded.startswith("u!")

    def test_encode_share_url_unicode(self):
        """Test URL with unicode characters."""
        url = "https://example.com/文件/file.xlsx"
        encoded = sf._encode_share_url(url)

        assert encoded.startswith("u!")

    def test_encode_share_url_no_padding(self):
        """Test that base64 padding is removed."""
        url = "https://test.com/a"
        encoded = sf._encode_share_url(url)

        assert "=" not in encoded

    def test_encode_share_url_decode_verify(self):
        """Verify encoded URL can be conceptually decoded."""
        url = "https://example.sharepoint.com/share/test.xlsx"
        encoded = sf._encode_share_url(url)

        # Remove prefix and add padding back
        b64_part = encoded[2:]
        # Add padding
        padding = 4 - len(b64_part) % 4
        if padding != 4:
            b64_part += "=" * padding

        decoded = base64.urlsafe_b64decode(b64_part).decode("utf-8")
        assert decoded == url


# ---------------------------------------------------------------------
# Test: get_file_info_from_share_link
# ---------------------------------------------------------------------


class TestGetFileInfoFromShareLink:
    def test_empty_share_url_returns_none(self):
        """Test that empty URL returns None."""
        result = sf.get_file_info_from_share_link("")
        assert result is None

    def test_none_share_url_returns_none(self):
        """Test that None URL returns None."""
        result = sf.get_file_info_from_share_link(None)
        assert result is None

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_successful_resolution(self, mock_get, mock_token, sample_file_item):
        """Test successful share link resolution."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = sample_file_item
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.example.com/link")

        assert result["name"] == "test_file.xlsx"
        assert result["download_url"] == "https://download.example.com/file.xlsx"
        assert result["modified_by"] == "John Doe"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_local_time_conversion(self, mock_get, mock_token):
        """Test UTC to local time conversion."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "file.xlsx",
            "lastModifiedDateTime": "2024-06-15T10:30:00Z",
            "@microsoft.graph.downloadUrl": "https://download.url",
        }
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.url")

        assert result["utc_time"] == "2024-06-15T10:30:00Z"
        assert result["local_time"] is not None
        assert isinstance(result["local_time"], datetime)

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_fallback_to_filesystem_time(self, mock_get, mock_token):
        """Test fallback to fileSystemInfo for modified time."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "file.xlsx",
            "fileSystemInfo": {"lastModifiedDateTime": "2024-06-15T08:00:00Z"},
            "@microsoft.graph.downloadUrl": "https://download.url",
        }
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.url")

        assert result["utc_time"] == "2024-06-15T08:00:00Z"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_missing_modified_time(self, mock_get, mock_token):
        """Test handling of missing modified time."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "file.xlsx",
            "@microsoft.graph.downloadUrl": "https://download.url",
        }
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.url")

        assert result["utc_time"] is None
        assert result["local_time"] is None

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_missing_modified_by(self, mock_get, mock_token):
        """Test handling of missing lastModifiedBy."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "file.xlsx",
            "lastModifiedDateTime": "2024-06-15T10:30:00Z",
            "@microsoft.graph.downloadUrl": "https://download.url",
        }
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.url")

        assert result["modified_by"] == "Unknown"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_missing_download_url(self, mock_get, mock_token):
        """Test handling of missing download URL."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "file.xlsx",
            "lastModifiedDateTime": "2024-06-15T10:30:00Z",
        }
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.url")

        assert result["download_url"] is None

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_missing_name(self, mock_get, mock_token):
        """Test handling of missing name."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lastModifiedDateTime": "2024-06-15T10:30:00Z",
            "@microsoft.graph.downloadUrl": "https://download.url",
        }
        mock_get.return_value = mock_response

        result = sf.get_file_info_from_share_link("https://share.url")

        assert result["name"] == "Unknown"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_http_error(self, mock_get, mock_token):
        """Test HTTP error handling."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            sf.get_file_info_from_share_link("https://share.url")

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_correct_api_endpoint(self, mock_get, mock_token):
        """Test that correct Graph API endpoint is called."""
        mock_token.return_value = "test_token"

        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "file.xlsx"}
        mock_get.return_value = mock_response

        sf.get_file_info_from_share_link("https://share.url")

        called_url = mock_get.call_args[0][0]
        assert "/shares/" in called_url
        assert "/driveItem" in called_url
        assert called_url.startswith("https://graph.microsoft.com/v1.0/")


# ---------------------------------------------------------------------
# Test: get_latest_file_info
# ---------------------------------------------------------------------


class TestGetLatestFileInfo:
    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    def test_uses_source_link_when_configured(self, mock_share_link, monkeypatch):
        """Test that SOURCE_LINK is used when configured."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "https://configured.link")

        mock_share_link.return_value = {
            "name": "configured_file.xlsx",
            "download_url": "https://download.url",
            "utc_time": "2024-01-01T00:00:00Z",
            "local_time": datetime.now(),
            "modified_by": "User",
        }

        result = sf.get_latest_file_info()

        assert result["name"] == "configured_file.xlsx"
        mock_share_link.assert_called_once_with("https://configured.link")

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_fallback_when_source_link_fails(
        self, mock_list, mock_drive, mock_site, mock_token, mock_share_link, monkeypatch
    ):
        """Test fallback to folder listing when SOURCE_LINK fails."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "https://bad.link")

        mock_share_link.side_effect = Exception("Link resolution failed")
        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "fallback_file.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download.url",
            }
        ]

        result = sf.get_latest_file_info()

        assert result["name"] == "fallback_file.xlsx"

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_fallback_when_source_link_no_download_url(
        self, mock_list, mock_drive, mock_site, mock_token, mock_share_link, monkeypatch
    ):
        """Test fallback when SOURCE_LINK returns no download URL."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "https://no.download.url")

        mock_share_link.return_value = {
            "name": "file.xlsx",
            "download_url": None,  # No download URL
        }
        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "fallback.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download.url",
            }
        ]

        result = sf.get_latest_file_info()

        assert result["name"] == "fallback.xlsx"

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_fallback_when_source_link_returns_none(
        self, mock_list, mock_drive, mock_site, mock_token, mock_share_link, monkeypatch
    ):
        """Test fallback when SOURCE_LINK returns None."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "https://returns.none")

        mock_share_link.return_value = None
        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "fallback.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download.url",
            }
        ]

        result = sf.get_latest_file_info()

        assert result["name"] == "fallback.xlsx"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_no_source_link_uses_folder_listing(
        self, mock_list, mock_drive, mock_site, mock_token, monkeypatch
    ):
        """Test folder listing when no SOURCE_LINK."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "")

        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "latest_file.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download.url",
            }
        ]

        result = sf.get_latest_file_info()

        assert result["name"] == "latest_file.xlsx"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_selects_most_recent_file(
        self, mock_list, mock_drive, mock_site, mock_token, monkeypatch
    ):
        """Test that most recently modified file is selected."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "")

        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "old_file.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download1.url",
            },
            {
                "name": "newest_file.xlsx",
                "lastModifiedDateTime": "2024-06-15T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download2.url",
            },
            {
                "name": "middle_file.xlsx",
                "lastModifiedDateTime": "2024-03-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download3.url",
            },
        ]

        result = sf.get_latest_file_info()

        assert result["name"] == "newest_file.xlsx"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_empty_folder_returns_none(
        self, mock_list, mock_drive, mock_site, mock_token, monkeypatch
    ):
        """Test empty folder returns None."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "")

        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = []

        result = sf.get_latest_file_info()

        assert result is None

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_missing_modified_by(
        self, mock_list, mock_drive, mock_site, mock_token, monkeypatch
    ):
        """Test handling of missing lastModifiedBy."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "")

        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "file.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                "@microsoft.graph.downloadUrl": "https://download.url",
                # No lastModifiedBy
            }
        ]

        result = sf.get_latest_file_info()

        assert result["modified_by"] == "Unknown"

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_missing_download_url(
        self, mock_list, mock_drive, mock_site, mock_token, monkeypatch
    ):
        """Test handling of missing download URL."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "")

        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "file.xlsx",
                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                # No download URL
            }
        ]

        result = sf.get_latest_file_info()

        assert result["download_url"] is None

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.get_site_id")
    @patch("utils.sharepoint_fetch.get_drive_id")
    @patch("utils.sharepoint_fetch.list_files")
    def test_local_time_conversion(
        self, mock_list, mock_drive, mock_site, mock_token, monkeypatch
    ):
        """Test UTC to local time conversion."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "")

        mock_token.return_value = "token"
        mock_site.return_value = "site-id"
        mock_drive.return_value = "drive-id"
        mock_list.return_value = [
            {
                "name": "file.xlsx",
                "lastModifiedDateTime": "2024-06-15T10:30:00Z",
                "@microsoft.graph.downloadUrl": "https://download.url",
            }
        ]

        result = sf.get_latest_file_info()

        assert result["utc_time"] == "2024-06-15T10:30:00Z"
        assert isinstance(result["local_time"], datetime)


# ---------------------------------------------------------------------
# Test: download_latest_file
# ---------------------------------------------------------------------


class TestDownloadLatestFile:
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_successful_download(self, mock_get, mock_info):
        """Test successful file download."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": "https://download.url",
            "utc_time": "2024-01-01T00:00:00Z",
            "local_time": datetime.now(),
            "modified_by": "User",
        }

        mock_response = MagicMock()
        mock_response.content = b"file content bytes"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        content, info = sf.download_latest_file()

        assert content == b"file content bytes"
        assert info["name"] == "file.xlsx"

    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_no_file_info_raises(self, mock_info):
        """Test exception when no file info."""
        mock_info.return_value = None

        with pytest.raises(Exception) as exc:
            sf.download_latest_file()
        assert "No downloadable file found" in str(exc.value)

    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_no_download_url_raises(self, mock_info):
        """Test exception when no download URL."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": None,
        }

        with pytest.raises(Exception) as exc:
            sf.download_latest_file()
        assert "No downloadable file found" in str(exc.value)

    @patch("utils.sharepoint_fetch.get_latest_file_info")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_download_http_error(self, mock_get, mock_info):
        """Test HTTP error during download."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": "https://download.url",
        }

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            sf.download_latest_file()

    @patch("utils.sharepoint_fetch.get_latest_file_info")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_download_uses_timeout(self, mock_get, mock_info):
        """Test that download uses REQUEST_TIMEOUT."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": "https://download.url",
        }

        mock_response = MagicMock()
        mock_response.content = b"content"
        mock_get.return_value = mock_response

        sf.download_latest_file()

        assert "timeout" in mock_get.call_args[1]


# ---------------------------------------------------------------------
# Test: download_file_from_share_link
# ---------------------------------------------------------------------


class TestDownloadFileFromShareLink:
    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_successful_download(self, mock_get, mock_info):
        """Test successful download from share link."""
        mock_info.return_value = {
            "name": "shared_file.xlsx",
            "download_url": "https://download.url",
            "utc_time": "2024-01-01T00:00:00Z",
            "local_time": datetime.now(),
            "modified_by": "User",
        }

        mock_response = MagicMock()
        mock_response.content = b"shared file content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        content, info = sf.download_file_from_share_link("https://share.link")

        assert content == b"shared file content"
        assert info["name"] == "shared_file.xlsx"
        mock_info.assert_called_once_with("https://share.link")

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    def test_no_info_raises(self, mock_info):
        """Test exception when info resolution fails."""
        mock_info.return_value = None

        with pytest.raises(Exception) as exc:
            sf.download_file_from_share_link("https://bad.link")
        assert "Unable to resolve or download" in str(exc.value)

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    def test_no_download_url_raises(self, mock_info):
        """Test exception when no download URL."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": None,
        }

        with pytest.raises(Exception) as exc:
            sf.download_file_from_share_link("https://no.url.link")
        assert "Unable to resolve or download" in str(exc.value)

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    def test_empty_download_url_raises(self, mock_info):
        """Test exception when download URL is empty string."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": "",
        }

        with pytest.raises(Exception) as exc:
            sf.download_file_from_share_link("https://empty.url")
        assert "Unable to resolve or download" in str(exc.value)

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_download_http_error(self, mock_get, mock_info):
        """Test HTTP error during download."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": "https://download.url",
        }

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            sf.download_file_from_share_link("https://share.link")

    @patch("utils.sharepoint_fetch.get_file_info_from_share_link")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_uses_timeout(self, mock_get, mock_info):
        """Test that download uses REQUEST_TIMEOUT."""
        mock_info.return_value = {
            "name": "file.xlsx",
            "download_url": "https://download.url",
        }

        mock_response = MagicMock()
        mock_response.content = b"content"
        mock_get.return_value = mock_response

        sf.download_file_from_share_link("https://share.link")

        assert "timeout" in mock_get.call_args[1]


# ---------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------


class TestIntegration:
    @patch("utils.sharepoint_fetch.requests.get")
    @patch("utils.sharepoint_fetch.msal.ConfidentialClientApplication")
    def test_full_flow_folder_listing(self, mock_msal, mock_get, mock_env_vars):
        """Test complete flow from token to download via folder listing."""
        # Mock MSAL
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {"access_token": "token"}
        mock_msal.return_value = mock_app

        # Mock all HTTP calls
        responses = [
            # get_site_id
            MagicMock(
                json=MagicMock(return_value={"id": "site-id"}),
                raise_for_status=MagicMock(),
            ),
            # get_drive_id
            MagicMock(
                json=MagicMock(return_value={"value": [{"id": "drive-id"}]}),
                raise_for_status=MagicMock(),
            ),
            # list_files
            MagicMock(
                json=MagicMock(
                    return_value={
                        "value": [
                            {
                                "name": "test.xlsx",
                                "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                                "@microsoft.graph.downloadUrl": "https://dl.url",
                            }
                        ]
                    }
                ),
                raise_for_status=MagicMock(),
            ),
            # download
            MagicMock(content=b"file bytes", raise_for_status=MagicMock()),
        ]
        mock_get.side_effect = responses

        content, info = sf.download_latest_file()

        assert content == b"file bytes"
        assert info["name"] == "test.xlsx"

    @patch("utils.sharepoint_fetch.requests.get")
    @patch("utils.sharepoint_fetch.msal.ConfidentialClientApplication")
    def test_full_flow_share_link(self, mock_msal, mock_get, monkeypatch):
        """Test complete flow using share link."""
        monkeypatch.setattr(sf, "SOURCE_LINK", "https://share.test.link")
        monkeypatch.setattr(sf, "TENANT_ID", "tenant")
        monkeypatch.setattr(sf, "CLIENT_ID", "client")
        monkeypatch.setattr(sf, "CLIENT_SECRET", "secret")

        # Mock MSAL
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {"access_token": "token"}
        mock_msal.return_value = mock_app

        # Mock HTTP calls
        responses = [
            # get_file_info_from_share_link
            MagicMock(
                json=MagicMock(
                    return_value={
                        "name": "shared.xlsx",
                        "lastModifiedDateTime": "2024-01-01T00:00:00Z",
                        "@microsoft.graph.downloadUrl": "https://dl.shared.url",
                    }
                ),
                raise_for_status=MagicMock(),
            ),
            # download
            MagicMock(content=b"shared file bytes", raise_for_status=MagicMock()),
        ]
        mock_get.side_effect = responses

        content, info = sf.download_latest_file()

        assert content == b"shared file bytes"
        assert info["name"] == "shared.xlsx"


# ---------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------


class TestEdgeCases:
    def test_module_level_constants_exist(self):
        """Test that all required module constants are defined."""
        assert hasattr(sf, "TENANT_ID")
        assert hasattr(sf, "CLIENT_ID")
        assert hasattr(sf, "CLIENT_SECRET")
        assert hasattr(sf, "SHAREPOINT_SITE")
        assert hasattr(sf, "SITE_PATH")
        assert hasattr(sf, "FOLDER_PATH")
        assert hasattr(sf, "SOURCE_LINK")
        assert hasattr(sf, "REQUEST_TIMEOUT")

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_connection_error(self, mock_get, mock_token):
        """Test handling of connection errors."""
        mock_token.return_value = "token"
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        with pytest.raises(requests.ConnectionError):
            sf.get_site_id({"Authorization": "Bearer token"})

    @patch("utils.sharepoint_fetch.get_token")
    @patch("utils.sharepoint_fetch.requests.get")
    def test_timeout_error(self, mock_get, mock_token):
        """Test handling of timeout errors."""
        mock_token.return_value = "token"
        mock_get.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(requests.Timeout):
            sf.get_site_id({"Authorization": "Bearer token"})

    @patch("utils.sharepoint_fetch.requests.get")
    def test_json_decode_error(self, mock_get, mock_env_vars):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(ValueError):
            sf.get_site_id({"Authorization": "Bearer token"})