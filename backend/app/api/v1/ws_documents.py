"""WebSocket endpoint for real-time document ingestion progress.

Two concurrent coroutines:
- forward_progress: reads from the pub/sub queue, pushes events to the client
- listen_for_cancel: reads from the client, handles cancel messages

Disconnect = Cancel: the cancel logic lives in `finally`, so it fires whether
the socket closed because the tab navigated away, the network dropped, or the
user sent an explicit cancel message.
"""

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import async_session_maker
from app.models.document import Document
from app.services.progress_bus import subscribe, unsubscribe, get_task

router = APIRouter()


@router.websocket("/ws/documents/{document_id}")
async def document_status_ws(websocket: WebSocket, document_id: uuid.UUID):
    await websocket.accept()
    queue = subscribe(document_id)
    completed_normally = False  # Track whether ingestion hit a terminal state
    try:
        # Race-condition guard: check if ingestion already finished before WS connected
        async with async_session_maker() as session:
            doc = await session.get(Document, document_id)
        if doc and doc.status in ("ready", "error", "partial", "cancelled"):
            await websocket.send_json({
                "phase": "complete",
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "total_chunks": (doc.doc_metadata or {}).get("total_chunks", doc.chunk_count),
            })
            completed_normally = True
            await websocket.close()
            return

        # Two concurrent jobs:
        # 1. forward_progress: read from queue, send to client
        # 2. listen_for_cancel: read from client, handle cancel messages

        async def forward_progress():
            while True:
                event = await queue.get()
                await websocket.send_json(event)
                if event.get("phase") == "complete":
                    return  # Terminal — stop forwarding

        async def listen_for_cancel():
            while True:
                msg = await websocket.receive_json()
                if msg.get("action") == "cancel":
                    return  # Falls through to the finally cancel logic

        t_forward = asyncio.create_task(forward_progress())
        t_listen = asyncio.create_task(listen_for_cancel())

        # Run both; when either finishes, cancel the other
        done, pending = await asyncio.wait(
            [t_forward, t_listen],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, WebSocketDisconnect):
                pass

        # Check if forward_progress completed because ingestion finished
        for t in done:
            exc = t.exception() if not t.cancelled() else None
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc
            # If forward_progress finished (not listen_for_cancel), ingestion completed normally
            if t is t_forward and not t.cancelled() and not exc:
                completed_normally = True

        await websocket.close()

    except WebSocketDisconnect:
        pass  # Client navigated away — falls through to finally
    finally:
        unsubscribe(document_id, queue)
        # Disconnect OR explicit cancel OR normal completion all land here.
        # Cancel the ingestion task UNLESS it already finished.
        if not completed_normally:
            async with async_session_maker() as session:
                doc = await session.get(Document, document_id)
            if doc and doc.status == "processing":
                task = get_task(document_id)
                if task and not task.done():
                    task.cancel()
