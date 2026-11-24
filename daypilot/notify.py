"""ntfy push notifications (free, no account). Used only after the user confirms."""
import os
import urllib.request
from datetime import datetime


def send_push(title: str, message: str, when: datetime, click_url=None) -> str:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        raise ValueError("No phone push topic is set. Add NTFY_TOPIC to the .env file.")
    headers = {"Title": title, "X-Delay": str(int(when.timestamp()))}
    if click_url:
        headers["Click"] = click_url
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode(), headers=headers, method="POST")
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as exc:
        raise ValueError(f"The phone push could not be scheduled ({type(exc).__name__}). Check your connection and topic name.")
    return topic
