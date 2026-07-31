"""In-process pub/sub for document ingestion progress.

Uses module-level dicts — sufficient for single-process (Render free-tier) deployment.
No Redis/external broker needed at this scale.

Two responsibilities:
1. Pub/sub: fan out progress events to asyncio.Queue subscribers per document_id
2. Task registry: track background asyncio.Tasks so they can be cancelled
"""

import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)

# --- Pub/Sub ---
# document_id → set of asyncio.Queue subscribers
_subscribers: dict[uuid.UUID, set[asyncio.Queue]] = {}

# --- Task Registry ---
# document_id → the asyncio.Task running ingest_document()
_ingestion_tasks: dict[uuid.UUID, asyncio.Task] = {}


def subscribe(document_id: uuid.UUID) -> asyncio.Queue:
    """Add a subscriber queue for a document's progress events."""
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(document_id, set()).add(queue)
    return queue


def unsubscribe(document_id: uuid.UUID, queue: asyncio.Queue) -> None:
    """Remove a subscriber queue. Clean up empty sets."""
    subs = _subscribers.get(document_id)
    if subs:
        subs.discard(queue)
        if not subs:
            del _subscribers[document_id]


async def publish(document_id: uuid.UUID, event: dict) -> None:
    """Fan out an event to all subscribers for a document."""
    for queue in _subscribers.get(document_id, set()).copy():
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Subscriber queue full for doc %s, dropping event", document_id)


def register_task(document_id: uuid.UUID, task: asyncio.Task) -> None:
    """Register a background ingestion task for cancellation support."""
    _ingestion_tasks[document_id] = task


def get_task(document_id: uuid.UUID) -> asyncio.Task | None:
    """Get the task for a document (for cancel checks in ws_documents.py)."""
    return _ingestion_tasks.get(document_id)


def cancel_task(document_id: uuid.UUID) -> bool:
    """Cancel a running ingestion task. Returns True if a task was found and cancelled."""
    task = _ingestion_tasks.get(document_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


def cleanup_task(document_id: uuid.UUID) -> None:
    """Remove a completed/cancelled task from the registry."""
    _ingestion_tasks.pop(document_id, None)
