from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.outbox import OutboxEvent
from app.services.outbox import publish_pending_events


@pytest.mark.asyncio
async def test_publish_pending_events_marks_published() -> None:
    event = OutboxEvent(
        id=uuid4(),
        event_type="payment.created",
        payload={"payment_id": str(uuid4())},
        created_at=datetime.now(UTC),
        published_at=None,
    )
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=[event])
    session.commit = AsyncMock()

    broker = MagicMock()
    broker.publish = AsyncMock()

    published = await publish_pending_events(session, broker)

    assert published == 1
    assert event.published_at is not None
    broker.publish.assert_awaited()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_publish_pending_events_noop_when_empty() -> None:
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=[])
    broker = SimpleNamespace(publish=AsyncMock())

    published = await publish_pending_events(session, broker)

    assert published == 0
    session.commit.assert_not_called()
