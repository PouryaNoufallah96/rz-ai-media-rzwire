"""Google Apps Script proxy: sheet actions + the shared call helper."""
import requests
from config import SHEETS_ENABLED, SCRIPT_URL, DRIVE_FOLDER_URL


def call_apps_script(payload):
    if not SHEETS_ENABLED:
        raise ValueError('RZWire Google Sheets and Drive sync is disabled for local review')
    if not SCRIPT_URL or SCRIPT_URL.startswith('PASTE_'):
        raise ValueError('GOOGLE_APPS_SCRIPT_URL not configured in .env')
    r = requests.post(SCRIPT_URL, json=payload,
                      headers={'Content-Type': 'application/json'},
                      allow_redirects=True, timeout=(5, 15))
    r.raise_for_status()
    data = r.json()
    if not data.get('success'):
        raise ValueError(data.get('error', 'Apps Script returned failure'))
    return data

# ── Route handler ─────────────────────────────────────────────────────────────
def handle_sheets(action, body):
    payload = {'action': action, **body}
    if action == 'uploadImage' and 'driveFolder' not in payload and DRIVE_FOLDER_URL:
        payload['driveFolder'] = DRIVE_FOLDER_URL
    return call_apps_script(payload)
