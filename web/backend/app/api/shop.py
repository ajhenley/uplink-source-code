from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.auth.deps import get_current_user
from app.models.player import Player
from app.models.gateway import Gateway
from app.models.databank import DataFile
from app.models.vlocation import VLocation
from app.game import constants as C

router = APIRouter(prefix="/api/shop", tags=["shop"])

class BuyRequest(BaseModel):
    session_id: str
    item_index: int


async def _resolve_gateway_computer_id(
    db: AsyncSession, player: Player
) -> int:
    """Resolve the gateway's Computer id via the player's localhost VLocation."""
    if not player.localhost_ip:
        raise HTTPException(400, "Player has no localhost IP")
    loc = (await db.execute(
        select(VLocation).where(
            VLocation.game_session_id == player.game_session_id,
            VLocation.ip == player.localhost_ip,
        )
    )).scalar_one_or_none()
    if loc is None or loc.computer_id is None:
        raise HTTPException(400, "Gateway computer not found")
    return loc.computer_id


@router.post("/buy-software")
async def buy_software(req: BuyRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Validate item index
    if req.item_index < 0 or req.item_index >= len(C.SOFTWARE_UPGRADES):
        raise HTTPException(400, "Invalid software index")

    sw = C.SOFTWARE_UPGRADES[req.item_index]
    name, sw_type, cost, size, version, description = sw

    # Get player
    player = (await db.execute(
        select(Player).where(Player.game_session_id == req.session_id)
    )).scalar_one_or_none()
    if not player:
        raise HTTPException(404, "Player not found")

    # Check balance
    if player.balance < cost:
        raise HTTPException(400, f"Insufficient funds. Need {cost}c, have {player.balance}c")

    # Resolve the gateway's actual computer_id
    gateway_computer_id = await _resolve_gateway_computer_id(db, player)

    # Check gateway memory
    if player.gateway_id:
        gateway = (await db.execute(
            select(Gateway).where(Gateway.id == player.gateway_id)
        )).scalar_one()

        # Sum current file sizes on the gateway computer
        used_memory = (await db.execute(
            select(func.coalesce(func.sum(DataFile.size), 0)).where(
                DataFile.computer_id == gateway_computer_id
            )
        )).scalar_one()

        if used_memory + size > gateway.memory_size:
            raise HTTPException(400, "Insufficient memory")

    # Deduct cost
    player.balance -= cost

    # Add software as a DataFile on the gateway computer
    software_file = DataFile(
        computer_id=gateway_computer_id,
        filename=description,  # e.g., "DECRYPTER V1.0"
        size=size,
        file_type=1,  # software type
        softwaretype=sw_type,
        data=str(version),
    )
    db.add(software_file)

    return {"success": True, "balance": player.balance, "item": description}

@router.post("/buy-hardware")
async def buy_hardware(req: BuyRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if req.item_index < 0 or req.item_index >= len(C.HARDWARE_UPGRADES):
        raise HTTPException(400, "Invalid hardware index")

    hw = C.HARDWARE_UPGRADES[req.item_index]
    name, hw_type, cost, _size, data_val, description = hw

    player = (await db.execute(
        select(Player).where(Player.game_session_id == req.session_id)
    )).scalar_one_or_none()
    if not player:
        raise HTTPException(404, "Player not found")

    if player.balance < cost:
        raise HTTPException(400, f"Insufficient funds. Need {cost}c, have {player.balance}c")

    if not player.gateway_id:
        raise HTTPException(400, "No gateway found")

    gateway = (await db.execute(
        select(Gateway).where(Gateway.id == player.gateway_id)
    )).scalar_one()

    # Validate the player isn't downgrading
    if hw_type == 1:  # CPU
        if data_val <= gateway.cpu_speed:
            raise HTTPException(400, f"Already have CPU speed {gateway.cpu_speed}, cannot downgrade to {data_val}")
    elif hw_type == 2:  # Modem
        if data_val <= gateway.modem_speed:
            raise HTTPException(400, f"Already have modem speed {gateway.modem_speed}, cannot downgrade to {data_val}")
    elif hw_type == 4:  # Memory
        if data_val <= gateway.memory_size:
            raise HTTPException(400, f"Already have memory size {gateway.memory_size}, cannot downgrade to {data_val}")
    elif hw_type == 5:  # Special
        if "Self Destruct" in name and gateway.has_self_destruct:
            raise HTTPException(400, "Already have Self Destruct installed")
        elif "Motion Sensor" in name and gateway.has_motion_sensor:
            raise HTTPException(400, "Already have Motion Sensor installed")

    # Apply hardware upgrade
    player.balance -= cost

    if hw_type == 1:  # CPU
        gateway.cpu_speed = data_val
    elif hw_type == 2:  # Modem
        gateway.modem_speed = data_val
    elif hw_type == 4:  # Memory
        gateway.memory_size = data_val
    elif hw_type == 5:  # Special (self-destruct, motion sensor)
        if "Self Destruct" in name:
            gateway.has_self_destruct = True
        elif "Motion Sensor" in name:
            gateway.has_motion_sensor = True

    return {"success": True, "balance": player.balance, "item": description}
