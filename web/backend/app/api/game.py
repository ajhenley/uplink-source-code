import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.deps import get_current_user
from app.models.user_account import UserAccount
from app.models.game_session import GameSession
from app.models.player import Player

router = APIRouter(prefix="/api/game", tags=["game"])

class NewGameRequest(BaseModel):
    player_name: str
    handle: str

class GameSessionResponse(BaseModel):
    id: str
    name: str
    game_time_ticks: int
    is_active: bool

    class Config:
        from_attributes = True

class NewGameResponse(BaseModel):
    session: GameSessionResponse
    player_id: int

@router.post("/new", response_model=NewGameResponse)
async def new_game(
    req: NewGameRequest,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.game.world_generator import generate_world

    session_id = str(uuid.uuid4())
    session = GameSession(
        id=session_id,
        user_id=user.id,
        name=f"{req.handle}'s Game",
    )
    db.add(session)
    await db.flush()

    player = await generate_world(db, session_id, req.player_name, req.handle)
    await db.commit()

    return NewGameResponse(
        session=GameSessionResponse.model_validate(session),
        player_id=player.id,
    )

@router.get("/list", response_model=list[GameSessionResponse])
async def list_games(
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GameSession).where(GameSession.user_id == user.id).order_by(GameSession.created_at.desc())
    )
    return [GameSessionResponse.model_validate(s) for s in result.scalars().all()]

@router.get("/{session_id}/world")
async def get_world_data(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.vlocation import VLocation
    from app.models.company import Company

    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")

    locations_result = await db.execute(
        select(VLocation).where(VLocation.game_session_id == session_id, VLocation.listed == True)
    )
    locations = locations_result.scalars().all()

    companies_result = await db.execute(
        select(Company).where(Company.game_session_id == session_id)
    )
    companies = companies_result.scalars().all()

    return {
        "locations": [
            {"ip": loc.ip, "x": loc.x, "y": loc.y}
            for loc in locations
        ],
        "companies": [
            {"name": c.name, "size": c.size}
            for c in companies
        ],
    }

@router.get("/{session_id}/player")
async def get_player(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")

    result = await db.execute(
        select(Player).where(Player.game_session_id == session_id)
    )
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return {
        "id": player.id,
        "name": player.name,
        "handle": player.handle,
        "balance": player.balance,
        "uplink_rating": player.uplink_rating,
        "neuromancer_rating": player.neuromancer_rating,
        "credit_rating": player.credit_rating,
    }


@router.post("/{session_id}/save")
async def save_game(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save current game state. Since we use DB-backed state, this just
    updates the timestamp and marks the session as saved."""
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")
    # Just update the timestamp (state is already in DB)
    session.updated_at = func.now()
    await db.flush()
    return {"status": "saved", "game_time_ticks": session.game_time_ticks}


@router.get("/{session_id}/load")
async def load_game(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load game session data for resuming."""
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")
    player = (await db.execute(
        select(Player).where(Player.game_session_id == session_id)
    )).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return {
        "session": GameSessionResponse.model_validate(session),
        "player_id": player.id,
    }


@router.delete("/{session_id}")
async def delete_game(
    session_id: str,
    user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a game session."""
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")
    session.is_active = False
    await db.flush()
    return {"status": "deleted"}
