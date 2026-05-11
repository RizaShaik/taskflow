"""
app/websocket/events.py
------------------------
Complete WebSocket event system for FlowDesk.

Event flow:
    1. Browser loads dashboard → JavaScript connects via Socket.IO
    2. Server receives 'connect' → puts client in 'tasks_room'
    3. User creates/updates/deletes a task via REST API
    4. REST route calls emit_task_event() after saving to DB
    5. Server broadcasts event to every client in 'tasks_room'
    6. Every browser's JavaScript receives the event
    7. Browser updates the DOM — no page reload needed

Events emitted BY SERVER to clients:
    connected       → confirms connection established
    task_created    → a new task was added
    task_updated    → an existing task was changed
    task_deleted    → a task was removed (payload: {"id": task_id})
    pong_client     → response to a ping from the browser

Events received FROM clients:
    connect         → browser opened a WebSocket connection
    disconnect      → browser closed or lost connection
    ping_server     → browser checking if connection is alive
"""

import logging
from flask_socketio import emit, join_room, leave_room
from app import socketio

logger = logging.getLogger(__name__)

# Single shared room — every authenticated user's browser joins this.
# In a multi-user production system you'd use per-user rooms
# (room=f"user_{user_id}") so users only see their own updates.
# For this project, one shared room keeps things simple and visible.
TASK_ROOM = "tasks_room"


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@socketio.on("connect")
def handle_connect():
    """
    Fires automatically when a browser establishes a WebSocket connection.

    What happens here:
        1. join_room() registers this client in the shared task room.
           After this, any emit(..., room=TASK_ROOM) reaches this client.
        2. We emit 'connected' back to THIS client only (no room= means
           the event goes only to the socket that just connected).

    The 'connected' event lets the browser know the handshake succeeded
    and triggers the green status dot in the UI.

    Note: Flask-SocketIO calls this automatically — you never call it manually.
    """
    join_room(TASK_ROOM)
    logger.info(
        "WebSocket client connected → joined '%s' | total clients in room: %s",
        TASK_ROOM,
        "n/a"   # Getting room size requires extra setup — not needed here
    )

    # emit() with no room= sends only to the connecting client
    emit("connected", {
        "message": "Connected to FlowDesk real-time channel.",
        "room":    TASK_ROOM,
    })


@socketio.on("disconnect")
def handle_disconnect():
    """
    Fires when a browser closes the tab, navigates away, or loses connection.

    leave_room() cleans up — removes this client from the task room.
    Flask-SocketIO also does this automatically on disconnect, but
    calling it explicitly is clearer and more maintainable.

    After this fires, this client will no longer receive room broadcasts.
    """
    leave_room(TASK_ROOM)
    logger.info("WebSocket client disconnected from '%s'", TASK_ROOM)


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT-INITIATED EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@socketio.on("ping_server")
def handle_ping(data):
    """
    Responds to a ping from the browser.

    The browser can send this periodically to verify the connection
    is still alive and the server is responding.

    Args:
        data: Optional dict from the browser (we ignore it here).

    The browser listens for 'pong_client' and uses it to update
    the connection status indicator.
    """
    logger.debug("Ping received from client")

    # emit() with no room= replies only to the client that pinged
    emit("pong_client", {
        "status":  "alive",
        "message": "Server is running.",
    })


# ══════════════════════════════════════════════════════════════════════════════
# BROADCAST HELPER — called by REST routes
# ══════════════════════════════════════════════════════════════════════════════

def emit_task_event(event_name: str, payload: dict) -> None:
    """
    Broadcast a task lifecycle event to all connected clients.

    Called from REST route handlers AFTER a successful DB write:
        create_task() → emit_task_event("task_created", task.to_dict())
        update_task() → emit_task_event("task_updated", task.to_dict())
        delete_task() → emit_task_event("task_deleted", {"id": task_id})

    Args:
        event_name: The event string the browser listens for.
                    One of: 'task_created', 'task_updated', 'task_deleted'
        payload:    The data to send.
                    For create/update: full task dict from task.to_dict()
                    For delete: just {"id": task_id}

    Why room=TASK_ROOM?
        Broadcasting to a room targets only clients who joined it.
        Without room=, the event would go to ALL connected sockets
        globally — including any sockets from other pages/features
        you might add later.

    Why socketio.emit() instead of just emit()?
        The plain emit() function only works inside a Socket.IO
        event handler (inside a @socketio.on() function).
        socketio.emit() works from ANYWHERE — including REST routes.
        This distinction is important and commonly misunderstood.
    """
    socketio.emit(event_name, payload, room=TASK_ROOM)
    logger.debug(
        "Broadcast '%s' to room '%s': %s",
        event_name, TASK_ROOM, payload
    )