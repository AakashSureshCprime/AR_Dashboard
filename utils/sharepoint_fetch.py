import msal
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TENANT_ID = os.getenv('SP_TENANT_ID')
CLIENT_ID = os.getenv('SP_CLIENT_ID')
CLIENT_SECRET = os.getenv('SP_CLIENT_SECRET')
SHAREPOINT_SITE = os.getenv('SHAREPOINT_SITE')
SITE_PATH = '/sites/FIN_AccountsReceivable'
FOLDER_PATH = '/2026/AR_Tech_Source File'

def get_token():
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET
    )
    token = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in token:
        raise Exception(f"Failed to get token: {token}")
    return token["access_token"]

def get_site_id(headers):
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE}:{SITE_PATH}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["id"]

def get_drive_id(site_id, headers):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["value"][0]["id"]

def list_files(drive_id, headers):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{FOLDER_PATH}:/children"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["value"]

def get_latest_file_info():
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
        "download_url": latest.get("@microsoft.graph.downloadUrl", None)
    }

def download_latest_file():
    info = get_latest_file_info()
    if not info or not info["download_url"]:
        raise Exception("No downloadable file found.")
    resp = requests.get(info["download_url"])
    resp.raise_for_status()
    return resp.content, info