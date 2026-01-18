from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any, Dict, List

import socketio
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import AsyncSessionLocal, engine, get_session
from app.kafka_client import kafka_manager
from app.models import Base, Event
from app.sockets import sio

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Create the FastAPI app
fastapi_app = FastAPI(title=settings.app_name)


class IngestEventRequest(BaseModel):
    event_type: str = Field(..., examples=["user.signup", "device.reading"])
    payload: Dict[str, Any] = Field(default_factory=dict)


class IngestEventResponse(BaseModel):
    status: str


@fastapi_app.on_event("startup")
async def on_startup() -> None:
    """Initialize Postgres tables, Kafka connections, and the background consumer."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await kafka_manager.start()
    fastapi_app.state.consumer_task = asyncio.create_task(consume_and_persist())


@fastapi_app.on_event("shutdown")
async def on_shutdown() -> None:
    """Gracefully stop background tasks + Kafka."""
    task: asyncio.Task | None = getattr(fastapi_app.state, "consumer_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    await kafka_manager.stop()


@fastapi_app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@fastapi_app.post("/events", response_model=IngestEventResponse, status_code=202)
async def ingest_event(body: IngestEventRequest) -> IngestEventResponse:
    """Accept an event and publish it to Kafka."""
    event = {"event_type": body.event_type, "payload": body.payload}
    await kafka_manager.produce_event(event)
    return IngestEventResponse(status="queued")


@fastapi_app.get("/events")
async def list_events(session: AsyncSession = Depends(get_session)) -> List[Dict[str, Any]]:
    """Fetch last 50 events persisted to Postgres."""
    rows = (await session.execute(select(Event).order_by(Event.created_at.desc()).limit(50))).scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "payload": json.loads(e.payload),
            "created_at": e.created_at.isoformat(),
        }
        for e in rows
    ]


async def consume_and_persist() -> None:
    """Consume Kafka events, persist to Postgres, then broadcast to Socket.IO clients."""
    logger.info("Starting Kafka consumer loop")
    async for ev in kafka_manager.consume_events():
        try:
            await persist_event(ev)
            await sio.emit("new_event", ev)
        except Exception:
            logger.exception("Failed processing event")


async def persist_event(ev: Dict[str, Any]) -> None:
    """Persist an event record to Postgres."""
    async with AsyncSessionLocal() as session:
        event = Event(
            event_type=str(ev.get("event_type", "unknown")),
            payload=json.dumps(ev.get("payload", {})),
        )
        session.add(event)
        await session.commit()


# Wrap FastAPI with Socket.IO ASGI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
