"""Inbound webhook endpoint — the chat provider delivers messages here."""
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..schemas import WebhookPayload
from ..security import verify_webhook_signature

logger = logging.getLogger("verdant.webhook")
router = APIRouter(tags=["webhook"])


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    db: Session = Depends(get_db),
):
    # Read the RAW body first — the HMAC is over the exact bytes received,
    # so we must not let JSON re-serialisation change them.
    raw = await request.body()

    if not verify_webhook_signature(raw, x_signature):
        logger.warning("Rejected webhook with bad/missing signature")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    try:
        payload = WebhookPayload.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Bad payload: {exc}")

    if payload.message.type != "text":
        # Out of scope for this task; acknowledge so the provider stops retrying.
        return {"status": "ignored", "reason": "non-text message"}

    message = services.process_incoming_message(
        db,
        name=payload.customer.name,
        phone=payload.customer.phone,
        text=payload.message.text,
        brand_id=payload.brand_id,
        external_customer_id=payload.customer.id,
        external_message_id=payload.message.id,
        event_id=payload.event_id,
    )
    return {"status": "ok", "message_id": message.id}
