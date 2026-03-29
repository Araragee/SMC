from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
import jwt
import json
from datetime import datetime
from typing import Dict, List as TList

from .. import models, schemas
from ..database import get_db, SessionLocal
from ..dependencies import (
    get_current_active_user,
    SECRET_KEY,
    ALGORITHM
)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, TList[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, payload: dict):
        dead = []
        for ws in list(self.active_connections.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_to_conversation(self, db, conversation_id: int, payload: dict, exclude_user_id: int = None):
        participants = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conversation_id
        ).all()
        for p in participants:
            if p.user_id == exclude_user_id:
                continue
            await self.send_to_user(p.user_id, payload)


ws_manager = ConnectionManager()

def _msg_dict(msg: models.Message) -> dict:
    return {
        "id":              msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id":       msg.sender_id,
        "sender_name":     msg.sender.name if msg.sender else None,
        "body":            msg.body if not msg.is_deleted else "[deleted]",
        "created_at":      msg.created_at.isoformat(),
        "is_deleted":      msg.is_deleted,
    }

def _unread_count(db, conversation_id: int, participant: models.ConversationParticipant) -> int:
    q = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id,
        models.Message.is_deleted == False,
    )
    if participant.last_read_at:
        q = q.filter(models.Message.created_at > participant.last_read_at)
    return q.count()

def _build_conversation_out(db, conv: models.Conversation, current_user_id: int) -> dict:
    participants = []
    for p in conv.participants:
        participants.append({
            "user_id":      p.user_id,
            "joined_at":    p.joined_at.isoformat(),
            "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None,
            "name":         p.user.name if p.user else None,
        })

    last_msg = db.query(models.Message).filter(
        models.Message.conversation_id == conv.id,
        models.Message.is_deleted == False,
    ).order_by(models.Message.created_at.desc()).first()

    my_part = next((p for p in conv.participants if p.user_id == current_user_id), None)
    unread = _unread_count(db, conv.id, my_part) if my_part else 0

    return {
        "id":           conv.id,
        "type":         conv.type,
        "name":         conv.name,
        "created_at":   conv.created_at.isoformat(),
        "participants": participants,
        "last_message": _msg_dict(last_msg) if last_msg else None,
        "unread_count": unread,
    }

async def _ws_handle_send_message(sender_id: int, data: dict, db):
    conv_id = int(data.get("conversation_id", 0))
    body = str(data.get("body", "")).strip()
    if not body:
        return
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == sender_id,
    ).first()
    if not part:
        return
    msg = models.Message(conversation_id=conv_id, sender_id=sender_id, body=body)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    payload = {"type": "new_message", "message": _msg_dict(msg)}
    await ws_manager.broadcast_to_conversation(db, conv_id, payload)
    for p in db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id != sender_id,
    ).all():
        count = _unread_count(db, conv_id, p)
        await ws_manager.send_to_user(p.user_id, {
            "type": "unread_update", "conversation_id": conv_id, "count": count,
        })

async def _ws_handle_mark_read(user_id: int, data: dict, db):
    conv_id = int(data.get("conversation_id", 0))
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == user_id,
    ).first()
    if not part:
        return
    part.last_read_at = datetime.utcnow()
    db.commit()
    await ws_manager.send_to_user(user_id, {
        "type": "unread_update", "conversation_id": conv_id, "count": 0,
    })

async def _ws_handle_typing(user_id: int, data: dict, db):
    conv_id = int(data.get("conversation_id", 0))
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == user_id,
    ).first()
    if not part:
        return
    await ws_manager.broadcast_to_conversation(db, conv_id, {
        "type": "typing", "conversation_id": conv_id, "user_id": user_id,
    }, exclude_user_id=user_id)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(user_id: int, websocket: WebSocket, token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id: int = payload.get("user_id")
        if token_user_id != user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user_id, websocket)
    db = SessionLocal()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue
            msg_type = data.get("type")
            if msg_type == "send_message":
                await _ws_handle_send_message(user_id, data, db)
            elif msg_type == "mark_read":
                await _ws_handle_mark_read(user_id, data, db)
            elif msg_type == "typing":
                await _ws_handle_typing(user_id, data, db)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user_id, websocket)
        db.close()

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    memberships = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id == current_user.id
    ).all()
    results = []
    for m in memberships:
        conv = db.query(models.Conversation).filter(models.Conversation.id == m.conversation_id).first()
        if conv:
            results.append(_build_conversation_out(db, conv, current_user.id))
    results.sort(key=lambda c: c["last_message"]["created_at"] if c["last_message"] else c["created_at"], reverse=True)
    return results

@router.post("/conversations/dm")
def create_or_get_dm(
    body: schemas.CreateDMRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    other_user = db.query(models.User).filter(models.User.id == body.other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    my_convs = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id == current_user.id
    ).all()
    for m in my_convs:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == m.conversation_id,
            models.Conversation.type == "dm",
        ).first()
        if not conv:
            continue
        if len(conv.participants) == 2:
            ids = {p.user_id for p in conv.participants}
            if ids == {current_user.id, body.other_user_id}:
                return _build_conversation_out(db, conv, current_user.id)
    conv = models.Conversation(type="dm")
    db.add(conv)
    db.flush()
    db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=current_user.id))
    db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=body.other_user_id))
    db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)

@router.post("/conversations/group")
def create_group(
    body: schemas.CreateGroupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    conv = models.Conversation(type="group", name=body.name)
    db.add(conv)
    db.flush()
    seen = set()
    for uid in [current_user.id] + body.participant_ids:
        if uid not in seen:
            seen.add(uid)
            db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=uid))
    db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)

@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    cursor: int = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    if not is_admin:
        part = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.user_id == current_user.id,
        ).first()
        if not part:
            raise HTTPException(status_code=403, detail="Not a participant")
    q = db.query(models.Message).filter(models.Message.conversation_id == conversation_id)
    if cursor:
        q = q.filter(models.Message.id < cursor)
    msgs = q.order_by(models.Message.id.desc()).limit(limit).all()
    msgs_asc = list(reversed(msgs))
    next_cursor = msgs_asc[0].id if len(msgs) == limit else None
    return {
        "messages": [_msg_dict(m) for m in msgs_asc],
        "next_cursor": next_cursor,
    }

@router.post("/conversations/{conversation_id}/messages")
async def send_message_rest(
    conversation_id: int,
    body: schemas.CreateMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == current_user.id,
    ).first()
    if not part:
        raise HTTPException(status_code=403, detail="Not a participant")

    msg = models.Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=body.body
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    payload = {"type": "new_message", "message": _msg_dict(msg)}
    await ws_manager.broadcast_to_conversation(db, conversation_id, payload)

    for p in db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id != current_user.id,
    ).all():
        count = _unread_count(db, conversation_id, p)
        await ws_manager.send_to_user(p.user_id, {
            "type": "unread_update", "conversation_id": conversation_id, "count": count,
        })

    return _msg_dict(msg)

@router.get("/sessions/{session_id}/thread")
def get_or_create_session_thread(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    if not is_admin and current_user.id not in (session.teacher_id, session.student_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    thread = db.query(models.SessionThread).filter(models.SessionThread.session_id == session_id).first()
    if thread:
        conv = db.query(models.Conversation).filter(models.Conversation.id == thread.conversation_id).first()
        return _build_conversation_out(db, conv, current_user.id)
    teacher = db.query(models.User).filter(models.User.id == session.teacher_id).first()
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    label = f"Session #{session.id}: {teacher.name if teacher else '?'} + {student.name if student else '?'}"
    conv = models.Conversation(type="session_thread", name=label)
    db.add(conv)
    db.flush()
    seen = set()
    for uid in [session.teacher_id, session.student_id]:
        if uid and uid not in seen:
            seen.add(uid)
            db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=uid))
    db.add(models.SessionThread(session_id=session_id, conversation_id=conv.id))
    db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)

@router.post("/conversations/{conversation_id}/participants")
def add_participant(
    conversation_id: int,
    body: schemas.AddParticipantRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv or conv.type != "group":
        raise HTTPException(status_code=400, detail="Only group conversations can have participants added")
    caller_part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == current_user.id,
    ).first()
    if not caller_part:
        raise HTTPException(status_code=403, detail="Not a participant")
    existing = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == body.user_id,
    ).first()
    if not existing:
        db.add(models.ConversationParticipant(conversation_id=conversation_id, user_id=body.user_id))
        db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)

@router.patch("/conversations/{conversation_id}/read")
def mark_conversation_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == current_user.id,
    ).first()
    if not part:
        raise HTTPException(status_code=403, detail="Not a participant")
    part.last_read_at = datetime.utcnow()
    db.commit()
    return {"unread_count": 0}
