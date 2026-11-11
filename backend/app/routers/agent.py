"""Agent view endpoints — all require a signed-in agent except /login."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..schemas import (
    ApproveIn,
    ConversationDetail,
    ConversationSummary,
    DraftOut,
    LoginIn,
    LoginOut,
    MessageOut,
)
from ..security import create_agent_token, require_agent, verify_password

logger = logging.getLogger("verdant.agent")
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    agent = db.scalar(
        select(models.Agent).where(models.Agent.username == body.username)
    )
    if agent is None or not verify_password(body.password, agent.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_agent_token(agent.id, agent.username)
    return LoginOut(token=token, display_name=agent.display_name)


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    dependencies=[Depends(require_agent)],
)
def list_conversations(db: Session = Depends(get_db)):
    convos = db.scalars(
        select(models.Conversation).order_by(
            models.Conversation.last_activity_at.desc()
        )
    ).all()

    out: list[ConversationSummary] = []
    for c in convos:
        last = c.messages[-1] if c.messages else None
        pending = db.scalar(
            select(models.Draft).where(
                models.Draft.conversation_id == c.id,
                models.Draft.status == "pending",
            )
        )
        out.append(
            ConversationSummary(
                id=c.id,
                customer_name=c.customer.name,
                customer_phone=c.customer.phone,
                last_message_preview=(last.text[:120] if last else ""),
                last_activity_at=c.last_activity_at,
                pending_draft=pending is not None,
            )
        )
    return out


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    dependencies=[Depends(require_agent)],
)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    convo = db.get(models.Conversation, conversation_id)
    if convo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    # The draft to surface is the latest one that is still pending/failed.
    draft = db.scalar(
        select(models.Draft)
        .where(
            models.Draft.conversation_id == convo.id,
            models.Draft.status.in_(("pending", "failed")),
        )
        .order_by(models.Draft.created_at.desc())
    )
    return ConversationDetail(
        id=convo.id,
        customer_name=convo.customer.name,
        customer_phone=convo.customer.phone,
        messages=[
            MessageOut(id=m.id, sender=m.sender, text=m.text, created_at=m.created_at)
            for m in convo.messages
        ],
        draft=(
            DraftOut(
                id=draft.id,
                text=draft.text,
                status=draft.status,
                error_detail=draft.error_detail,
                created_at=draft.created_at,
            )
            if draft
            else None
        ),
    )


@router.post(
    "/conversations/{conversation_id}/approve",
    response_model=ConversationDetail,
    dependencies=[Depends(require_agent)],
)
def approve(conversation_id: str, body: ApproveIn, db: Session = Depends(get_db)):
    convo = db.get(models.Conversation, conversation_id)
    if convo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    draft = db.get(models.Draft, body.draft_id)
    if draft is None or draft.conversation_id != conversation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Draft not found")
    if draft.status == "used":
        raise HTTPException(status.HTTP_409_CONFLICT, "Draft already approved")

    text = body.text.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Reply is empty")

    now = datetime.now(timezone.utc)
    reply = models.Message(
        conversation_id=convo.id, sender="agent", text=text
    )
    db.add(reply)
    draft.status = "used"
    draft.used_at = now
    convo.last_activity_at = now
    db.commit()

    # Return the refreshed conversation (now with the approved reply, no draft).
    return get_conversation(conversation_id, db)
