"""Customer view endpoints (no auth) — the test side of the conversation.

A message sent here is processed through the exact same service as the webhook.
The customer only ever sees their own messages and the agent's APPROVED replies;
drafts are never exposed.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, services
from ..config import get_settings
from ..database import get_db
from ..schemas import (
    CustomerConversationOut,
    CustomerMessageIn,
    MessageOut,
    TestCustomer,
)

router = APIRouter(prefix="/api/customer", tags=["customer"])
settings = get_settings()

# A few ready-made customers for the Customer view dropdown.
TEST_CUSTOMERS = [
    TestCustomer(name="Aisha Khan", phone="+919800000001"),
    TestCustomer(name="Rohan Mehta", phone="+919800000002"),
    TestCustomer(name="Priya Nair", phone="+919800000003"),
]


@router.get("/test-customers", response_model=list[TestCustomer])
def test_customers() -> list[TestCustomer]:
    return TEST_CUSTOMERS


@router.post("/message")
def send_message(body: CustomerMessageIn, db: Session = Depends(get_db)):
    """Same handling as a webhook delivery."""
    message = services.process_incoming_message(
        db,
        name=body.name.strip(),
        phone=body.phone.strip(),
        text=body.text.strip(),
        brand_id=settings.default_brand_id,
    )
    return {"status": "ok", "message_id": message.id}


@router.get("/conversation", response_model=CustomerConversationOut)
def get_conversation(phone: str, db: Session = Depends(get_db)):
    """The customer's own view: their messages + approved agent replies only."""
    customer = db.scalar(
        select(models.Customer).where(models.Customer.phone == phone.strip())
    )
    if customer is None:
        return CustomerConversationOut(
            customer_name="", customer_phone=phone, messages=[]
        )

    convo = db.scalar(
        select(models.Conversation)
        .where(models.Conversation.customer_id == customer.id)
        .order_by(models.Conversation.created_at.desc())
    )
    messages: list[MessageOut] = []
    if convo is not None:
        messages = [
            MessageOut(
                id=m.id, sender=m.sender, text=m.text, created_at=m.created_at
            )
            for m in convo.messages  # customer + agent(approved) only; no drafts
        ]
    return CustomerConversationOut(
        customer_name=customer.name,
        customer_phone=customer.phone,
        messages=messages,
    )
