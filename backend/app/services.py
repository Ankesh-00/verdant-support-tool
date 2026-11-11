"""Core domain logic shared by the webhook and the Customer view.

`process_incoming_message` is the single path every customer message flows
through, so a message typed in the Customer view is handled byte-for-byte like
one delivered to the webhook: same customer/conversation resolution, same save,
same AI draft.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .llm import DraftError, generate_draft

logger = logging.getLogger("verdant.services")
settings = get_settings()

_HISTORY_LIMIT = 10  # recent turns handed to the model for context


def _get_or_create_customer(
    db: Session, *, name: str, phone: str, external_id: str | None, brand_id: str
) -> models.Customer:
    customer = db.scalar(select(models.Customer).where(models.Customer.phone == phone))
    if customer is None:
        customer = models.Customer(
            name=name, phone=phone, external_id=external_id, brand_id=brand_id
        )
        db.add(customer)
        db.flush()
    else:
        # Keep the latest display name / external id we have seen.
        if name:
            customer.name = name
        if external_id and not customer.external_id:
            customer.external_id = external_id
    return customer


def _get_or_create_open_conversation(
    db: Session, customer: models.Customer, brand_id: str
) -> models.Conversation:
    convo = db.scalar(
        select(models.Conversation).where(
            models.Conversation.customer_id == customer.id,
            models.Conversation.status == "open",
        )
    )
    if convo is None:
        convo = models.Conversation(customer_id=customer.id, brand_id=brand_id)
        db.add(convo)
        db.flush()
    return convo


def process_incoming_message(
    db: Session,
    *,
    name: str,
    phone: str,
    text: str,
    brand_id: str | None = None,
    external_customer_id: str | None = None,
    external_message_id: str | None = None,
    event_id: str | None = None,
) -> models.Message:
    """Save a customer message and generate an AI draft for it.

    Idempotent on `event_id`: a retried webhook with the same event is ignored
    and the already-stored message is returned.
    """
    brand_id = brand_id or settings.default_brand_id

    # Idempotency: providers retry webhooks. Don't double-store / double-draft.
    if event_id:
        existing = db.scalar(
            select(models.Message).where(models.Message.event_id == event_id)
        )
        if existing is not None:
            logger.info("Duplicate webhook event_id=%s ignored", event_id)
            return existing

    customer = _get_or_create_customer(
        db, name=name, phone=phone, external_id=external_customer_id, brand_id=brand_id
    )
    convo = _get_or_create_open_conversation(db, customer, brand_id)

    now = datetime.now(timezone.utc)
    message = models.Message(
        conversation_id=convo.id,
        sender="customer",
        text=text,
        external_id=external_message_id,
        event_id=event_id,
        created_at=now,
    )
    db.add(message)
    convo.last_activity_at = now
    db.flush()

    _create_draft(db, convo, message)

    db.commit()
    db.refresh(message)
    return message


def _create_draft(
    db: Session, convo: models.Conversation, message: models.Message
) -> models.Draft:
    """Best-effort AI draft. A failure is recorded, never fatal to the webhook."""
    history = [
        {"sender": m.sender, "text": m.text}
        for m in convo.messages
        if m.id != message.id
    ][-_HISTORY_LIMIT:]

    draft = models.Draft(conversation_id=convo.id, message_id=message.id)
    try:
        result = generate_draft(message.text, history=history)
        draft.text = result.text
        draft.model = result.model
        draft.status = "pending"
    except DraftError as exc:
        logger.exception("Draft generation failed for message=%s", message.id)
        draft.text = (
            "Thanks for your message. One of our team will reply to you shortly."
        )
        draft.status = "failed"
        draft.error_detail = str(exc)
    db.add(draft)
    db.flush()
    return draft
