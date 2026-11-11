"""Pydantic request/response models."""
from datetime import datetime

from pydantic import BaseModel, Field


# ------------------------------------------------------------- webhook in
class WebhookCustomer(BaseModel):
    id: str | None = None
    name: str
    phone: str


class WebhookMessage(BaseModel):
    id: str | None = None
    type: str = "text"
    text: str


class WebhookPayload(BaseModel):
    event_id: str | None = None
    type: str = "message.received"
    brand_id: str | None = None
    timestamp: datetime | None = None
    customer: WebhookCustomer
    message: WebhookMessage


# -------------------------------------------------- customer view (no auth)
class CustomerMessageIn(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=3)
    text: str = Field(min_length=1)


# ------------------------------------------------------------------- agent
class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    display_name: str


class ApproveIn(BaseModel):
    draft_id: str
    text: str = Field(min_length=1)


# ------------------------------------------------------------------- views
class MessageOut(BaseModel):
    id: str
    sender: str
    text: str
    created_at: datetime


class DraftOut(BaseModel):
    id: str
    text: str
    status: str
    error_detail: str | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    customer_name: str
    customer_phone: str
    last_message_preview: str
    last_activity_at: datetime
    pending_draft: bool


class ConversationDetail(BaseModel):
    id: str
    customer_name: str
    customer_phone: str
    messages: list[MessageOut]
    draft: DraftOut | None = None


class CustomerConversationOut(BaseModel):
    customer_name: str
    customer_phone: str
    messages: list[MessageOut]  # approved agent replies + customer messages only


class TestCustomer(BaseModel):
    name: str
    phone: str
