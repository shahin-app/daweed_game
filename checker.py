import json
import os
import random
import time
from typing import Any, Dict, Optional, Tuple

from curl_cffi import requests
from notify_telegram import send_telegram

STATE_FILE = "state.json"

def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"last_seen_earliestDate": None, "last_status": None}
    except Exception:
        # If state gets corrupted, reset safely
        return {"last_seen_earliestDate": None, "last_status": None}

def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def build_headers() -> Dict[str, str]:
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": os.environ.get("VFS_ACCEPT_LANGUAGE", "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7"),
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://visa.vfsglobal.com",
        "referer": "https://visa.vfsglobal.com/",
        "user-agent": os.environ["VFS_USER_AGENT"],
        "authorize": os.environ["VFS_AUTHORIZE"],
        "cookie": os.environ["VFS_COOKIE"],
    }


def parse_response(data: Any) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Your example response (slot available):
    {
      "earliestDate": "04/10/2026 00:00:00",
      "earliestSlotLists": [...],
      "error": null
    }

    We consider "slot available" if earliestDate is a non-empty string
    OR earliestSlotLists is a non-empty list.
    """
    if not isinstance(data, dict):
        return False, None, {"unexpected_response": data}

    earliest_date = data.get("earliestDate")
    slot_list = data.get("earliestSlotLists")

    has_slot = False
    if isinstance(earliest_date, str) and earliest_date.strip():
        has_slot = True
    if isinstance(slot_list, list) and len(slot_list) > 0:
        has_slot = True

    return has_slot, earliest_date if isinstance(earliest_date, str) else None, data

def main() -> None:
    url = os.environ["VFS_URL"]
    payload = json.loads(os.environ["VFS_PAYLOAD_JSON"])

    # Polite jitter so you don't always hit on the exact schedule second
    time.sleep(random.uniform(1.0, 6.0))

    headers = build_headers()

    try:
        r = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=25,
            impersonate="chrome"  # key line
        )

    except Exception as e:
        print(f"Request failed: {e}")
        return

    # If token expired / blocked
    if r.status_code in (401, 403):
        print(f"Auth blocked/expired: HTTP {r.status_code}")
        print(r.text[:500])
        return

    if not r.ok:
        print(f"HTTP error: {r.status_code}")
        print(r.text[:500])
        return

    try:
        data = r.json()
    except Exception:
        print("Non-JSON response:")
        print(r.text[:500])
        return

    has_slot, earliest_date, details = parse_response(data)

    state = load_state()
    last_seen = state.get("last_seen_earliestDate")
    last_status = state.get("last_status")

    # Notify conditions:
    # 1) first time we see a slot
    # 2) earliest date changed (useful if date updates)
    should_notify = False
    if has_slot and last_status != "AVAILABLE":
        should_notify = True
    elif has_slot and earliest_date and earliest_date != last_seen:
        should_notify = True

    if should_notify:
        send_telegram(details)

    # Update state
    state["last_status"] = "AVAILABLE" if has_slot else "NOT_AVAILABLE"
    state["last_seen_earliestDate"] = earliest_date if has_slot else None
    save_state(state)

    print(f"Status: {state['last_status']}; earliestDate={state['last_seen_earliestDate']}")

if __name__ == "__main__":
    main()
