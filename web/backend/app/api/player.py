"""REST API endpoints for player messages, missions, and gateway."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.auth.deps import get_current_user
from app.models.user_account import UserAccount
from app.models.game_session import GameSession
from app.models.player import Player
from app.models.message import Message
from app.models.mission import Mission
from app.models.gateway import Gateway
from app.models.vlocation import VLocation
from app.models.databank import DataFile
from app.game import mission_engine
from app.game import constants as C

router = APIRouter(prefix="/api/player", tags=["player"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_player(
    db: AsyncSession, session_id: str, user: UserAccount
) -> Player:
    """Validate the session belongs to the user and return the Player."""
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")

    player = (
        await db.execute(
            select(Player).where(Player.game_session_id == session_id)
        )
    ).scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


async def _get_gateway_computer_id(
    db: AsyncSession, session_id: str, player: Player
) -> int:
    """Resolve the Computer id for the player's gateway via their localhost VLocation."""
    if not player.localhost_ip:
        raise HTTPException(status_code=400, detail="Player has no localhost IP")
    loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.ip == player.localhost_ip,
            )
        )
    ).scalar_one_or_none()
    if loc is None or loc.computer_id is None:
        raise HTTPException(status_code=400, detail="Gateway computer not found")
    return loc.computer_id


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.get("/{session_id}/messages")
async def get_messages(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all messages for the player, ordered by created_at_tick desc."""
    player = await _get_player(db, session_id, user)

    messages = (
        await db.execute(
            select(Message)
            .where(
                Message.game_session_id == session_id,
                Message.player_id == player.id,
            )
            .order_by(Message.created_at_tick.desc())
        )
    ).scalars().all()

    return [
        {
            "id": m.id,
            "from_name": m.from_name,
            "subject": m.subject,
            "body": m.body,
            "is_read": m.is_read,
            "created_at_tick": m.created_at_tick,
        }
        for m in messages
    ]


@router.post("/{session_id}/messages/{message_id}/read")
async def mark_message_read(
    session_id: str,
    message_id: int,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a message as read."""
    player = await _get_player(db, session_id, user)

    message = (
        await db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.game_session_id == session_id,
                Message.player_id == player.id,
            )
        )
    ).scalar_one_or_none()

    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    message.is_read = True
    return {"success": True}


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

@router.get("/{session_id}/missions")
async def get_accepted_missions(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return accepted (but not completed) missions for the player."""
    player = await _get_player(db, session_id, user)

    missions = (
        await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.is_accepted == True,
                Mission.accepted_by == str(player.id),
                Mission.is_completed == False,
            ).order_by(Mission.payment.desc())
        )
    ).scalars().all()

    return [
        {
            "id": m.id,
            "mission_type": m.mission_type,
            "description": m.description,
            "employer_name": m.employer_name,
            "payment": m.payment,
            "difficulty": m.difficulty,
            "min_rating": m.min_rating,
            "target_computer_ip": m.target_computer_ip,
            "is_accepted": m.is_accepted,
            "is_completed": m.is_completed,
            "due_at_tick": m.due_at_tick,
        }
        for m in missions
    ]


@router.post("/{session_id}/missions/{mission_id}/accept")
async def accept_mission(
    session_id: str,
    mission_id: int,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a mission from the BBS."""
    player = await _get_player(db, session_id, user)

    try:
        result = await mission_engine.accept_mission(
            db, session_id, player.id, mission_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result


@router.post("/{session_id}/missions/{mission_id}/complete")
async def complete_mission(
    session_id: str,
    mission_id: int,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check and complete a mission, crediting payment and updating ratings."""
    player = await _get_player(db, session_id, user)

    try:
        check_result = await mission_engine.check_mission_completion(
            db, session_id, player.id, mission_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not check_result["completed"]:
        return {
            "success": False,
            "reason": check_result["reason"],
        }

    try:
        completion_result = await mission_engine.complete_mission(
            db, session_id, player.id, mission_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        **completion_result,
    }


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

@router.get("/{session_id}/gateway")
async def get_gateway(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the player's gateway info, files on it, and memory usage."""
    player = await _get_player(db, session_id, user)

    if not player.gateway_id:
        raise HTTPException(status_code=404, detail="No gateway found")

    gateway = (
        await db.execute(
            select(Gateway).where(Gateway.id == player.gateway_id)
        )
    ).scalar_one_or_none()
    if gateway is None:
        raise HTTPException(status_code=404, detail="Gateway not found")

    gateway_computer_id = await _get_gateway_computer_id(db, session_id, player)

    files = (
        await db.execute(
            select(DataFile).where(DataFile.computer_id == gateway_computer_id)
        )
    ).scalars().all()

    memory_used = sum(f.size for f in files)

    return {
        "gateway": {
            "name": gateway.name,
            "cpu_speed": gateway.cpu_speed,
            "modem_speed": gateway.modem_speed,
            "memory_size": gateway.memory_size,
            "has_self_destruct": gateway.has_self_destruct,
            "has_motion_sensor": gateway.has_motion_sensor,
        },
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "size": f.size,
                "file_type": f.file_type,
                "softwaretype": f.softwaretype,
            }
            for f in files
        ],
        "memory_used": memory_used,
        "memory_total": gateway.memory_size,
    }


# ---------------------------------------------------------------------------
# Gateway file deletion
# ---------------------------------------------------------------------------

@router.delete("/{session_id}/gateway/files/{file_id}")
async def delete_gateway_file(
    session_id: str,
    file_id: int,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file from the player's gateway."""
    player = await _get_player(db, session_id, user)
    gateway_computer_id = await _get_gateway_computer_id(db, session_id, player)

    data_file = (
        await db.execute(
            select(DataFile).where(
                DataFile.id == file_id,
                DataFile.computer_id == gateway_computer_id,
            )
        )
    ).scalar_one_or_none()
    if data_file is None:
        raise HTTPException(status_code=404, detail="File not found on gateway")

    await db.delete(data_file)
    return {"success": True}


# ---------------------------------------------------------------------------
# Software list
# ---------------------------------------------------------------------------

@router.get("/{session_id}/software")
async def get_software_list(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return installed software on the player's gateway."""
    player = await _get_player(db, session_id, user)
    gateway_computer_id = await _get_gateway_computer_id(db, session_id, player)

    files = (
        await db.execute(
            select(DataFile).where(
                DataFile.computer_id == gateway_computer_id,
                DataFile.file_type == 1,  # software
            )
        )
    ).scalars().all()

    return [
        {
            "id": f.id,
            "filename": f.filename,
            "softwaretype": f.softwaretype,
            "version": int(f.data) if f.data and f.data.isdigit() else 1,
        }
        for f in files
    ]
