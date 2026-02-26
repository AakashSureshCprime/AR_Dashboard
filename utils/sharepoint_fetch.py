import os
from datetime import datetime

import msal
import requests
from dotenv import load_dotenv

from config.settings import REQUEST_TIMEOUT
import base64
from urllib.parse import quote

load_dotenv()

TENANT_ID = os.getenv("SP_TENANT_ID")
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
SHAREPOINT_SITE = os.getenv("SHAREPOINT_SITE")
SITE_PATH = "/sites/FIN_AccountsReceivable"
FOLDER_PATH = "/2026/Automation"
SOURCE_LINK = os.getenv("SP_SOURCE_LINK", "").strip()


def get_token():
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET
    )
    token = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in token:
        raise Exception(f"Failed to get token: {token}")
    return token["access_token"]


def get_site_id(headers):
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE}:{SITE_PATH}"
    resp = resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["id"]


def get_drive_id(site_id, headers):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    resp = requests.get(url, headers=headers,timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["value"][0]["id"]


def _encode_share_url(url: str) -> str:
    """Base64-URL encode a sharing URL for Microsoft Graph /shares API."""
    # Base64 URL-safe without padding
    b = url.encode("utf-8")
    token = base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")
    return f"u!{token}"


def get_file_info_from_share_link(share_url: str):
    """
    Resolve a SharePoint sharing URL to a driveItem via Graph /shares API
    and return file info consistent with get_latest_file_info().
    """
    if not share_url:
        return None
    access_token = get_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    encoded = _encode_share_url(share_url)
    url = f"https://graph.microsoft.com/v1.0/shares/{encoded}/driveItem"
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    item = resp.json()
    # Some properties live under parent references; guard accesses
    name = item.get("name", "Unknown")
    modified = item.get("lastModifiedDateTime") or item.get("fileSystemInfo", {}).get("lastModifiedDateTime")
    download_url = item.get("@microsoft.graph.downloadUrl")
    local_time = None
    if modified:
        local_time = datetime.fromisoformat(modified.replace("Z", "+00:00")).astimezone()
    return {
        "name": name,
        "utc_time": modified,
        "local_time": local_time,
        "modified_by": item.get("lastModifiedBy", {}).get("user", {}).get("displayName", "Unknown"),
        "download_url": download_url,
    }


def list_files(drive_id, headers):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{FOLDER_PATH}:/children"
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["value"]


def get_latest_file_info():
    # If a specific source link is configured, prefer that file
    if SOURCE_LINK:
        try:
            info = get_file_info_from_share_link(SOURCE_LINK)
            if info and info.get("download_url"):
                return info
        except Exception:
            # Fall through to folder listing if link resolution fails
            pass

    access_token = get_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    site_id = get_site_id(headers)
    drive_id = get_drive_id(site_id, headers)
    files = list_files(drive_id, headers)
    if not files:
        return None
    latest = max(files, key=lambda x: x["lastModifiedDateTime"])
    utc_time = latest["lastModifiedDateTime"]
    local_time = datetime.fromisoformat(utc_time.replace("Z", "+00:00")).astimezone()
    return {
        "name": latest["name"],
        "utc_time": utc_time,
        "local_time": local_time,
        "modified_by": latest.get("lastModifiedBy", {}).get("user", {}).get("displayName", "Unknown"),
        "download_url": latest.get("@microsoft.graph.downloadUrl", None),
    }


def download_latest_file():
    info = get_latest_file_info()
    if not info or not info["download_url"]:
        raise Exception("No downloadable file found.")
    resp = requests.get(info["download_url"], timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.content, info

def download_file_from_share_link(share_url: str):
    """Download file bytes for a specific sharing URL."""
    info = get_file_info_from_share_link(share_url)
    if not info or not info.get("download_url"):
        raise Exception("Unable to resolve or download the specified SharePoint file.")
    resp = requests.get(info["download_url"], timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.content, info
