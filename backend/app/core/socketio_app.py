"""
GestureMed AI — Socket.IO Real-time Server

Handles:
- Consultation room management
- WebRTC signaling (offer/answer/ICE candidates)
- Gesture event broadcasting
- Annotation sync
- Live notifications
"""
import logging
from datetime import datetime
from typing import Dict, Set

import socketio
from jose import jwt, JWTError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Socket.IO Setup ────────────────────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# ── In-Memory Room State ───────────────────────────────────────────────────────
# Production: move to Redis with pub/sub
active_rooms: Dict[str, Set[str]] = {}       # room_id -> {socket_ids}
socket_to_user: Dict[str, dict] = {}          # socket_id -> {user_id, role, room_id}
room_annotations: Dict[str, list] = {}        # room_id -> [annotation dicts]


def verify_socket_token(token: str) -> dict:
    """Verify JWT from socket handshake."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return {}


# ── Connection ─────────────────────────────────────────────────────────────────

@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token", "")
    payload = verify_socket_token(token)

    if not payload or payload.get("type") != "access":
        logger.warning(f"Rejected socket connection: invalid token sid={sid}")
        return False  # reject

    socket_to_user[sid] = {
        "user_id": payload["sub"],
        "role": payload.get("role"),
        "room_id": None,
    }
    logger.info(f"Socket connected: sid={sid} user={payload['sub']}")


@sio.event
async def disconnect(sid):
    user_info = socket_to_user.pop(sid, {})
    room_id = user_info.get("room_id")

    if room_id and room_id in active_rooms:
        active_rooms[room_id].discard(sid)
        await sio.leave_room(sid, room_id)
        await sio.emit("user_left", {
            "user_id": user_info.get("user_id"),
            "role": user_info.get("role"),
        }, room=room_id)

        if not active_rooms[room_id]:
            del active_rooms[room_id]

    logger.info(f"Socket disconnected: sid={sid}")


# ── Room Management ────────────────────────────────────────────────────────────

@sio.event
async def join_room(sid, data):
    """Patient or doctor joins a consultation room."""
    room_id = data.get("room_id")
    if not room_id:
        return {"error": "room_id required"}

    user_info = socket_to_user.get(sid, {})
    if not user_info:
        return {"error": "not authenticated"}

    # Join the Socket.IO room
    await sio.enter_room(sid, room_id)
    if room_id not in active_rooms:
        active_rooms[room_id] = set()
    active_rooms[room_id].add(sid)
    socket_to_user[sid]["room_id"] = room_id

    # Send existing annotations to new joiner
    existing_annotations = room_annotations.get(room_id, [])

    # Notify others
    await sio.emit("user_joined", {
        "user_id": user_info["user_id"],
        "role": user_info["role"],
        "participant_count": len(active_rooms[room_id]),
    }, room=room_id, skip_sid=sid)

    logger.info(f"User {user_info['user_id']} joined room {room_id}")
    return {
        "status": "joined",
        "room_id": room_id,
        "participants": len(active_rooms[room_id]),
        "existing_annotations": existing_annotations,
    }


@sio.event
async def leave_room(sid, data):
    room_id = data.get("room_id")
    if room_id:
        await sio.leave_room(sid, room_id)
        if room_id in active_rooms:
            active_rooms[room_id].discard(sid)


# ── WebRTC Signaling ───────────────────────────────────────────────────────────

@sio.event
async def webrtc_offer(sid, data):
    """Forward WebRTC offer to the other participant in the room."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    if room_id:
        await sio.emit("webrtc_offer", {
            "offer": data.get("offer"),
            "from_sid": sid,
        }, room=room_id, skip_sid=sid)


@sio.event
async def webrtc_answer(sid, data):
    """Forward WebRTC answer."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    if room_id:
        await sio.emit("webrtc_answer", {
            "answer": data.get("answer"),
            "from_sid": sid,
        }, room=room_id, skip_sid=sid)


@sio.event
async def ice_candidate(sid, data):
    """Forward ICE candidate."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    if room_id:
        await sio.emit("ice_candidate", {
            "candidate": data.get("candidate"),
            "from_sid": sid,
        }, room=room_id, skip_sid=sid)


# ── Gesture Events ─────────────────────────────────────────────────────────────

@sio.event
async def gesture_event(sid, data):
    """Broadcast gesture recognition event to consultation room."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    user_info = socket_to_user.get(sid, {})

    if not room_id:
        return

    event_payload = {
        "gesture": data.get("gesture"),
        "confidence": data.get("confidence"),
        "action": data.get("action"),
        "metadata": data.get("metadata", {}),
        "user_id": user_info.get("user_id"),
        "role": user_info.get("role"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    await sio.emit("gesture_received", event_payload, room=room_id, skip_sid=sid)


# ── Annotations ────────────────────────────────────────────────────────────────

@sio.event
async def add_annotation(sid, data):
    """Sync body annotation to all room participants."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    user_info = socket_to_user.get(sid, {})

    if not room_id:
        return

    annotation = {
        "id": data.get("id"),
        "type": data.get("type", "point"),
        "coordinates": data.get("coordinates"),
        "body_region": data.get("body_region"),
        "note": data.get("note"),
        "color": data.get("color", "#FF6B6B"),
        "created_by": user_info.get("user_id"),
        "role": user_info.get("role"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Persist in-memory
    if room_id not in room_annotations:
        room_annotations[room_id] = []
    room_annotations[room_id].append(annotation)

    # Broadcast
    await sio.emit("annotation_added", annotation, room=room_id, skip_sid=sid)


@sio.event
async def clear_annotations(sid, data):
    room_id = socket_to_user.get(sid, {}).get("room_id")
    if room_id:
        room_annotations[room_id] = []
        await sio.emit("annotations_cleared", {}, room=room_id)


@sio.event
async def remove_annotation(sid, data):
    room_id = socket_to_user.get(sid, {}).get("room_id")
    annotation_id = data.get("annotation_id")
    if room_id and annotation_id:
        room_annotations[room_id] = [
            a for a in room_annotations.get(room_id, [])
            if a.get("id") != annotation_id
        ]
        await sio.emit("annotation_removed", {"annotation_id": annotation_id}, room=room_id)


# ── Chat / Notes ───────────────────────────────────────────────────────────────

@sio.event
async def send_note(sid, data):
    """Real-time doctor notes visible to patient."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    user_info = socket_to_user.get(sid, {})

    if room_id:
        await sio.emit("note_received", {
            "text": data.get("text"),
            "from": user_info.get("role"),
            "timestamp": datetime.utcnow().isoformat(),
        }, room=room_id)


# ── Pain / Patient Events ──────────────────────────────────────────────────────

@sio.event
async def patient_action(sid, data):
    """Patient gesture action (call nurse, pain level, etc.)."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    if room_id:
        await sio.emit("patient_action_received", {
            "action": data.get("action"),
            "pain_level": data.get("pain_level"),
            "message": data.get("message"),
            "timestamp": datetime.utcnow().isoformat(),
        }, room=room_id, skip_sid=sid)


# ── Consultation Control ───────────────────────────────────────────────────────

@sio.event
async def gesture_frame(sid, data):
    """
    Receive a base64-encoded video frame from client,
    run MediaPipe gesture detection, and broadcast results.
    Called per-frame during active consultation.
    """
    room_id = socket_to_user.get(sid, {}).get("room_id")
    user_info = socket_to_user.get(sid, {})

    if not room_id or not data.get("frame"):
        return

    try:
        from app.services.gesture_engine.tracker import process_gesture_frame_from_socket
        consultation_id = data.get("consultation_id", "unknown")
        result = await process_gesture_frame_from_socket(
            consultation_id=consultation_id,
            user_id=user_info.get("user_id", "unknown"),
            user_role=user_info.get("role", "PATIENT"),
            frame_b64=data["frame"],
        )

        # Broadcast gesture result to room
        if result.get("gesture") and result["gesture"] != "NONE":
            await sio.emit("gesture_received", {
                **result,
                "user_id": user_info.get("user_id"),
                "role": user_info.get("role"),
                "timestamp": datetime.utcnow().isoformat(),
            }, room=room_id, skip_sid=sid)

            # If an action was triggered, broadcast it separately
            if result.get("action"):
                await sio.emit("patient_action_received" if user_info.get("role") == "PATIENT" else "doctor_action_received", {
                    "action": result["action"]["type"],
                    "message": result["action"]["message"],
                    "level": result["action"]["level"],
                    "metadata": result["action"]["metadata"],
                    "timestamp": datetime.utcnow().isoformat(),
                }, room=room_id)

    except Exception as e:
        logger.error(f"gesture_frame processing error: {e}")


@sio.event
async def end_consultation(sid, data):
    """Doctor ends the consultation — triggers AI report generation."""
    room_id = socket_to_user.get(sid, {}).get("room_id")
    user_info = socket_to_user.get(sid, {})

    if room_id and user_info.get("role") in ("DOCTOR", "ADMIN"):
        await sio.emit("consultation_ended", {
            "ended_by": user_info.get("user_id"),
            "consultation_id": data.get("consultation_id"),
            "timestamp": datetime.utcnow().isoformat(),
        }, room=room_id)
