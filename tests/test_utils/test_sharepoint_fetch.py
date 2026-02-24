from unittest.mock import MagicMock, patch

import pytest

import utils.sharepoint_fetch as sf


def test_get_token_success(monkeypatch):
    class DummyApp:
        def acquire_token_for_client(self, scopes):
            return {"access_token": "dummy_token"}

    monkeypatch.setattr(
        sf.msal, "ConfidentialClientApplication", lambda *a, **k: DummyApp()
    )
    monkeypatch.setattr(sf, "TENANT_ID", "tenant")
    monkeypatch.setattr(sf, "CLIENT_ID", "client")
    monkeypatch.setattr(sf, "CLIENT_SECRET", "secret")
    token = sf.get_token()
    assert token == "dummy_token"


def test_get_token_failure(monkeypatch):
    class DummyApp:
        def acquire_token_for_client(self, scopes):
            return {"error": "fail"}

    monkeypatch.setattr(
        sf.msal, "ConfidentialClientApplication", lambda *a, **k: DummyApp()
    )
    monkeypatch.setattr(sf, "TENANT_ID", "tenant")
    monkeypatch.setattr(sf, "CLIENT_ID", "client")
    monkeypatch.setattr(sf, "CLIENT_SECRET", "secret")
    with pytest.raises(Exception) as exc:
        sf.get_token()
    assert "Failed to get token" in str(exc.value)


@patch("utils.sharepoint_fetch.get_token", return_value="dummy_token")
@patch("utils.sharepoint_fetch.get_site_id", return_value="siteid")
@patch("utils.sharepoint_fetch.get_drive_id", return_value="driveid")
@patch("utils.sharepoint_fetch.list_files")
def test_get_latest_file_info_success(
    mock_list_files, mock_drive_id, mock_site_id, mock_get_token
):
    file = {
        "name": "file.xlsx",
        "lastModifiedDateTime": "2024-01-01T00:00:00Z",
        "lastModifiedBy": {"user": {"displayName": "User"}},
        "@microsoft.graph.downloadUrl": "http://download",
    }
    mock_list_files.return_value = [file]
    info = sf.get_latest_file_info()
    assert info["name"] == "file.xlsx"
    assert info["utc_time"] == "2024-01-01T00:00:00Z"
    assert info["modified_by"] == "User"
    assert info["download_url"] == "http://download"


@patch("utils.sharepoint_fetch.get_token", return_value="dummy_token")
@patch("utils.sharepoint_fetch.get_site_id", return_value="siteid")
@patch("utils.sharepoint_fetch.get_drive_id", return_value="driveid")
@patch("utils.sharepoint_fetch.list_files", return_value=[])
def test_get_latest_file_info_none(
    mock_list_files, mock_drive_id, mock_site_id, mock_get_token
):
    info = sf.get_latest_file_info()
    assert info is None


@patch("utils.sharepoint_fetch.get_latest_file_info")
@patch("utils.sharepoint_fetch.requests.get")
def test_download_latest_file_success(mock_requests_get, mock_get_latest_file_info):
    mock_get_latest_file_info.return_value = {
        "download_url": "http://download",
        "name": "file.xlsx",
        "utc_time": "2024-01-01T00:00:00Z",
        "local_time": "2024-01-01T05:30:00+05:30",
        "modified_by": "User",
    }
    mock_resp = MagicMock()
    mock_resp.content = b"data"
    mock_resp.raise_for_status = lambda: None
    mock_requests_get.return_value = mock_resp
    content, info = sf.download_latest_file()
    assert content == b"data"
    assert info["name"] == "file.xlsx"


@patch("utils.sharepoint_fetch.get_latest_file_info", return_value=None)
def test_download_latest_file_no_info(mock_get_latest_file_info):
    with pytest.raises(Exception) as exc:
        sf.download_latest_file()
    assert "No downloadable file found" in str(exc.value)


@patch(
    "utils.sharepoint_fetch.get_latest_file_info", return_value={"download_url": None}
)
def test_download_latest_file_no_url(mock_get_latest_file_info):
    with pytest.raises(Exception) as exc:
        sf.download_latest_file()
    assert "No downloadable file found" in str(exc.value)
