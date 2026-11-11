"""Send a correctly-signed test message to the webhook.

Usage:
    python send_webhook.py                      # sends the sample Aisha message
    python send_webhook.py "Do you deliver to Dubai?"
    python send_webhook.py "..." --url https://your-app.onrender.com/webhook

The signature is the HMAC-SHA256 of the raw JSON body using WEBHOOK_SECRET.
"""
import argparse
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone

import httpx

SECRET = os.environ.get("WEBHOOK_SECRET", "verdant-demo-secret-2026")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "text",
        nargs="?",
        default="Hi, my order #4471 hasn't arrived yet. Can I change the delivery address?",
    )
    parser.add_argument("--url", default="http://localhost:8000/webhook")
    parser.add_argument("--name", default="Aisha Khan")
    parser.add_argument("--phone", default="+919800000001")
    args = parser.parse_args()

    payload = {
        "event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "type": "message.received",
        "brand_id": "verdant-co",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer": {"id": f"cust_{uuid.uuid4().hex[:4]}", "name": args.name, "phone": args.phone},
        "message": {"id": f"msg_{uuid.uuid4().hex[:5]}", "type": "text", "text": args.text},
    }

    # Sign the EXACT bytes we send.
    raw = json.dumps(payload).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()

    resp = httpx.post(
        args.url,
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": f"sha256={sig}"},
        timeout=60,
    )
    print(resp.status_code, resp.text)


if __name__ == "__main__":
    main()
