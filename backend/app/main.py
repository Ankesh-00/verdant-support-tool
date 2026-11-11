"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from . import models
from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import agent, customer, webhook
from .security import hash_password

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("verdant")
settings = get_settings()


def _seed_agent() -> None:
    """Create the demo agent on first boot if it does not already exist."""
    with SessionLocal() as db:
        existing = db.scalar(
            select(models.Agent).where(
                models.Agent.username == settings.seed_agent_username
            )
        )
        if existing is None:
            db.add(
                models.Agent(
                    username=settings.seed_agent_username,
                    password_hash=hash_password(settings.seed_agent_password),
                    display_name="Support Agent",
                )
            )
            db.commit()
            logger.info("Seeded agent '%s'", settings.seed_agent_username)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # For this task we create tables on startup. A real deployment would use
    # Alembic migrations instead.
    Base.metadata.create_all(bind=engine)
    _seed_agent()
    yield


app = FastAPI(title="Verdant & Co Support Tool", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(customer.router)
app.include_router(agent.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "brand": settings.default_brand_id}
