import json
import os
import requests
from typing import Any, Dict

def send_telegram(details: Dict[str, Any]) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    msg = (
        "✅ VFS slot detected!\n\n"
        f"Earliest date: {details.get('earliestDate')}\n"
        f"Slots: {details.get('earliestSlotLists')}\n"
    )

    # Add small JSON (keep it short for Telegram)
    msg += "\nRaw:\n" + json.dumps(details, ensure_ascii=False, indent=2)[:3000]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=20)
    r.raise_for_status()
