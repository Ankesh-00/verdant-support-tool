"""Draft generation with Groq.

Design notes
------------
* The whole (small) knowledge base is placed in the system prompt. The model is
  told to answer ONLY from it and to escalate when the answer is not there —
  this is the behaviour the brief specifically probes ("Do you deliver to
  Dubai?", the allergy message).
* We pass the recent conversation as chat turns so follow-ups read naturally.
* Any failure (no key, network, rate limit) raises `DraftError`; the caller
  records a `failed` draft instead of losing the message. The agent then sees a
  clear fallback rather than a blank box.
"""
from __future__ import annotations

from dataclasses import dataclass

from groq import Groq

from .config import get_settings
from .knowledge_base import BRAND_NAME, KNOWLEDGE_BASE

settings = get_settings()


class DraftError(Exception):
    """Raised when a draft could not be generated."""


@dataclass
class DraftResult:
    text: str
    model: str


SYSTEM_PROMPT = f"""\
You are a customer-support assistant for {BRAND_NAME}, an online skincare brand \
in India. You write a suggested reply that a human agent will review before it \
is sent. Write the reply itself only — no preamble, no "Here is a draft".

Use ONLY the policies below as your source of truth. Do not invent policies, \
prices, dates, or order details.

POLICIES
{KNOWLEDGE_BASE}

Rules:
- Keep it short (2-4 sentences), warm, and plain. The agent should be able to \
send it with little or no editing.
- If the customer asks something the policies do not cover (for example \
delivery outside India), do not guess. Say we are not able to confirm that and \
that a team member will follow up.
- You do not have access to order systems, tracking, or account data. For a \
specific order ("where is #4471") explain the relevant policy and say the team \
will check the specific order; never invent a status or date.
- For anything about a health or allergic reaction, do not give medical advice. \
Advise the customer to stop using the product and consult a doctor, and say our \
team will help with a return or refund.
- Refer to prices in rupees. Never promise anything beyond the policies.
"""


def _client() -> Groq:
    if not settings.groq_api_key:
        raise DraftError("GROQ_API_KEY is not configured")
    return Groq(api_key=settings.groq_api_key)


def generate_draft(
    customer_message: str,
    history: list[dict] | None = None,
) -> DraftResult:
    """Generate a draft reply for `customer_message`.

    `history` is an optional list of prior turns, each {"sender", "text"},
    oldest first, excluding the current message.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history or []:
        role = "assistant" if turn["sender"] == "agent" else "user"
        messages.append({"role": role, "content": turn["text"]})
    messages.append({"role": "user", "content": customer_message})

    try:
        completion = _client().chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.3,
            max_tokens=320,
        )
    except DraftError:
        raise
    except Exception as exc:  # groq/network/rate-limit errors
        raise DraftError(f"{type(exc).__name__}: {exc}") from exc

    text = (completion.choices[0].message.content or "").strip()
    if not text:
        raise DraftError("Model returned an empty reply")
    return DraftResult(text=text, model=settings.groq_model)
