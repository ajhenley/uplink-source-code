import json
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth.jwt import decode_access_token
from app.database import async_session
from app.models.player import Player
from app.game import connection_manager as cm
from app.game import task_engine
from app.game import mission_engine
from app.ws import protocol as P


class SessionState:
    """Per-WebSocket connection state tracking the current screen context."""

    def __init__(self, user_id: int, game_session_id: str, player_id: int):
        self.user_id = user_id
        self.game_session_id = game_session_id
        self.player_id = player_id
        self.computer_id: int | None = None
        self.current_sub_page: int = 0

    def as_dict(self) -> dict:
        """Return the mutable portion of state used by handle_screen_action."""
        return {
            "computer_id": self.computer_id,
            "current_sub_page": self.current_sub_page,
        }

    def update_from(self, d: dict) -> None:
        """Apply changes that handle_screen_action wrote into the dict."""
        if "computer_id" in d:
            self.computer_id = d["computer_id"]
        if "current_sub_page" in d:
            self.current_sub_page = d["current_sub_page"]


class ConnectionManager:
    """Manages active WebSocket connections and their session states."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.session_states: dict[str, SessionState] = {}

    async def connect(
        self, websocket: WebSocket, session_id: str, state: SessionState
    ):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = state

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        self.session_states.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(message)

    def get_state(self, session_id: str) -> SessionState | None:
        return self.session_states.get(session_id)


manager = ConnectionManager()


async def websocket_handler(websocket: WebSocket):
    # ---- authenticate ----
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id: int = payload.get("user_id")
    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.close(code=4002, reason="Missing session_id")
        return

    # ---- look up player_id from the game session ----
    async with async_session() as db:
        result = await db.execute(
            select(Player).where(Player.game_session_id == session_id)
        )
        player = result.scalar_one_or_none()
        if player is None:
            await websocket.close(code=4003, reason="No player for this session")
            return
        player_id = player.id

    state = SessionState(
        user_id=user_id,
        game_session_id=session_id,
        player_id=player_id,
    )
    await manager.connect(websocket, session_id, state)

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            try:
                if msg_type == P.MSG_HEARTBEAT:
                    await websocket.send_json({"type": P.MSG_HEARTBEAT_ACK})

                elif msg_type == P.MSG_BOUNCE_ADD:
                    ip = message.get("ip")
                    if not ip:
                        await websocket.send_json(
                            {"type": P.MSG_ERROR, "detail": "ip is required"}
                        )
                        continue
                    async with async_session() as db:
                        chain = await cm.add_bounce(
                            db, session_id, player_id, ip
                        )
                        await db.commit()
                    await websocket.send_json(
                        {"type": P.MSG_BOUNCE_CHAIN_UPDATED, "nodes": chain}
                    )

                elif msg_type == P.MSG_BOUNCE_REMOVE:
                    position = message.get("position")
                    if position is None:
                        await websocket.send_json(
                            {"type": P.MSG_ERROR, "detail": "position is required"}
                        )
                        continue
                    async with async_session() as db:
                        chain = await cm.remove_bounce(
                            db, session_id, player_id, int(position)
                        )
                        await db.commit()
                    await websocket.send_json(
                        {"type": P.MSG_BOUNCE_CHAIN_UPDATED, "nodes": chain}
                    )

                elif msg_type == P.MSG_CONNECT:
                    async with async_session() as db:
                        result = await cm.connect(
                            db, session_id, player_id
                        )
                        await db.commit()
                    # Update local session state with connection info
                    state.computer_id = result["computer_id"]
                    state.current_sub_page = result["screen"]["screen_index"]
                    await websocket.send_json(
                        {
                            "type": P.MSG_CONNECTED,
                            "target_ip": result["target_ip"],
                            "screen": result["screen"],
                        }
                    )

                elif msg_type == P.MSG_DISCONNECT:
                    async with async_session() as db:
                        await cm.disconnect(db, session_id, player_id)
                        await db.commit()
                    state.computer_id = None
                    state.current_sub_page = 0
                    await websocket.send_json({"type": P.MSG_DISCONNECTED})

                elif msg_type == P.MSG_SCREEN_ACTION:
                    action = message.get("action")
                    action_data = {
                        k: v
                        for k, v in message.items()
                        if k not in ("type", "action")
                    }
                    state_dict = state.as_dict()
                    async with async_session() as db:
                        screen = await cm.handle_screen_action(
                            db, session_id, player_id,
                            action, action_data, state_dict,
                        )
                        await db.commit()
                    state.update_from(state_dict)
                    await websocket.send_json(
                        {"type": P.MSG_SCREEN_UPDATE, "screen": screen}
                    )

                elif msg_type == P.MSG_RUN_TOOL:
                    tool_name = message.get("tool_name")
                    tool_version = message.get("tool_version", 1)
                    target_ip = message.get("target_ip")
                    target_data = message.get("target_data", {})
                    async with async_session() as db:
                        result = await task_engine.start_task(
                            db, session_id, player_id,
                            tool_name, tool_version, target_ip, target_data,
                        )
                        await db.commit()
                    await websocket.send_json(
                        {"type": P.MSG_TASK_UPDATE, "tasks": [result]}
                    )

                elif msg_type == P.MSG_STOP_TOOL:
                    task_id = message.get("task_id")
                    async with async_session() as db:
                        result = await task_engine.stop_task(db, task_id)
                        await db.commit()
                    await websocket.send_json(
                        {"type": P.MSG_TASK_UPDATE, "tasks": [result]}
                    )

                elif msg_type == P.MSG_SET_SPEED:
                    speed = message.get("speed", 1)
                    from app.game.game_loop import game_loop
                    game_loop.speed_multiplier[session_id] = speed
                    await websocket.send_json(
                        {"type": P.MSG_SPEED_CHANGED, "speed": speed}
                    )

                elif msg_type == P.MSG_ACCEPT_MISSION:
                    mid = message.get("mission_id")
                    if mid is None:
                        await websocket.send_json(
                            {"type": P.MSG_ERROR, "detail": "mission_id is required"}
                        )
                        continue
                    async with async_session() as db:
                        mission_data = await mission_engine.accept_mission(
                            db, session_id, player_id, int(mid)
                        )
                        # Fetch updated available missions
                        player = (await db.execute(
                            select(Player).where(Player.id == player_id)
                        )).scalar_one()
                        available = await mission_engine.get_available_missions(
                            db, session_id, player.uplink_rating
                        )
                        await db.commit()
                    await websocket.send_json(
                        {"type": P.MSG_SCREEN_UPDATE, "screen": {
                            "screen_type": 4,  # BBS
                            "missions": available,
                        }}
                    )
                    await websocket.send_json(
                        {"type": "mission_accepted", "mission": mission_data}
                    )

                elif msg_type == P.MSG_COMPLETE_MISSION:
                    mid = message.get("mission_id")
                    if mid is None:
                        await websocket.send_json(
                            {"type": P.MSG_ERROR, "detail": "mission_id is required"}
                        )
                        continue
                    async with async_session() as db:
                        check = await mission_engine.check_mission_completion(
                            db, session_id, player_id, int(mid)
                        )
                        if check["completed"]:
                            result = await mission_engine.complete_mission(
                                db, session_id, player_id, int(mid)
                            )
                            await db.commit()
                            await websocket.send_json(
                                {"type": P.MSG_BALANCE_CHANGED,
                                 "balance": result["balance"],
                                 "payment": result["mission_payment"]}
                            )
                            await websocket.send_json(
                                {"type": P.MSG_RATING_CHANGED,
                                 "uplink_rating": result["uplink_rating"],
                                 "uplink_rating_level": result["uplink_rating_level"],
                                 "uplink_rating_name": result["uplink_rating_name"],
                                 "neuromancer_rating": result["neuromancer_rating"]}
                            )
                            await websocket.send_json(
                                {"type": "mission_completed",
                                 "mission_id": int(mid)}
                            )
                        else:
                            await db.commit()
                            await websocket.send_json(
                                {"type": P.MSG_ERROR,
                                 "detail": check["reason"]}
                            )

                else:
                    await websocket.send_json(
                        {
                            "type": P.MSG_ERROR,
                            "detail": f"Unknown message type: {msg_type}",
                        }
                    )

            except ValueError as exc:
                await websocket.send_json(
                    {"type": P.MSG_ERROR, "detail": str(exc)}
                )
            except Exception as exc:
                await websocket.send_json(
                    {"type": P.MSG_ERROR, "detail": f"Internal error: {exc}"}
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
