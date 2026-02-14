"""Store engine -- buying/selling hardware upgrades and software for the player gateway."""
import logging

from app.extensions import db
from app.models.gateway import Gateway
from app.models.player import Player
from app.models.data_file import DataFile
from app.models.vlocation import VLocation
from app.game import constants as C

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File-type constant for software stored on gateway
# ---------------------------------------------------------------------------
FILETYPE_SOFTWARE = 1

# ---------------------------------------------------------------------------
# Part-exchange multiplier (player gets this fraction back when upgrading)
# ---------------------------------------------------------------------------
PART_EXCHANGE = C.GATEWAY_PARTEXCHANGEVALUE  # 0.75


# ===================================================================
# Catalog helpers
# ===================================================================

def get_hardware_catalog():
    """Return available hardware upgrades grouped by category.

    Each entry is a dict with keys:
        name, hw_type, cost, size, value, description
    where *value* is the speed / capacity number attached to the upgrade.
    """
    catalog = {}
    for name, hw_type, cost, size, value, description in C.HARDWARE_UPGRADES:
        if hw_type == C.GATEWAYUPGRADETYPE_CPU:
            category = "cpu"
        elif hw_type == C.GATEWAYUPGRADETYPE_MODEM:
            category = "modem"
        elif hw_type == C.GATEWAYUPGRADETYPE_MEMORY:
            category = "memory"
        elif hw_type == C.GATEWAYUPGRADETYPE_SECURITY:
            category = "security"
        else:
            category = "other"

        catalog.setdefault(category, []).append({
            "name": name,
            "hw_type": hw_type,
            "cost": cost,
            "size": size,
            "value": value,
            "description": description,
        })

    # Sort each category by cost ascending so the UI can render tiers easily
    for items in catalog.values():
        items.sort(key=lambda i: i["cost"])

    return catalog


def get_software_catalog():
    """Return available software grouped by tool name.

    Each entry is a dict with keys:
        name, sw_type, cost, size, version, description
    """
    catalog = {}
    for name, sw_type, cost, size, version, description in C.SOFTWARE_UPGRADES:
        catalog.setdefault(name, []).append({
            "name": name,
            "sw_type": sw_type,
            "cost": cost,
            "size": size,
            "version": version,
            "description": description,
        })

    # Sort each tool's versions ascending
    for versions in catalog.values():
        versions.sort(key=lambda v: v["version"])

    return catalog


# ===================================================================
# Internal helpers
# ===================================================================

def _get_player_and_gateway(session_id, player_id):
    """Load Player and Gateway, raising ValueError on missing data."""
    player = Player.query.filter_by(
        id=player_id, game_session_id=session_id
    ).first()
    if player is None:
        raise ValueError(f"Player {player_id} not found in session {session_id}")
    if player.gateway_id is None:
        raise ValueError(f"Player {player_id} has no gateway")
    gateway = Gateway.query.get(player.gateway_id)
    if gateway is None:
        raise ValueError(f"Gateway {player.gateway_id} not found")
    return player, gateway


def _get_gateway_computer_id(session_id, player):
    """Resolve the player's localhost IP to the gateway Computer id."""
    if player.localhost_ip is None:
        return None
    loc = VLocation.query.filter_by(
        game_session_id=session_id, ip=player.localhost_ip
    ).first()
    if loc is None:
        return None
    return loc.computer_id


def _find_hw_entry(hw_type_const, value):
    """Find a HARDWARE_UPGRADES tuple matching type and value."""
    for entry in C.HARDWARE_UPGRADES:
        # entry: (name, hw_type, cost, size, value, description)
        if entry[1] == hw_type_const and entry[4] == value:
            return entry
    return None


def _find_current_hw_cost(hw_type_const, current_value):
    """Return the catalog cost of the hardware the player currently owns,
    or 0 if it is the base / free tier.
    """
    entry = _find_hw_entry(hw_type_const, current_value)
    if entry is not None:
        return entry[2]
    return 0


def _compute_upgrade_cost(hw_type_const, current_value, new_value):
    """Return net cost after part-exchange.  Negative means the player
    would be downgrading (not allowed).
    """
    new_entry = _find_hw_entry(hw_type_const, new_value)
    if new_entry is None:
        return None  # invalid selection
    new_cost = new_entry[2]
    current_cost = _find_current_hw_cost(hw_type_const, current_value)
    exchange_credit = int(current_cost * PART_EXCHANGE)
    return max(0, new_cost - exchange_credit)


# ===================================================================
# Hardware purchasing
# ===================================================================

def buy_hardware(session_id, player_id, hardware_type, level):
    """Buy a hardware upgrade.

    Parameters
    ----------
    session_id : str
        Game session id.
    player_id : int
        Player primary key.
    hardware_type : str
        One of "cpu", "memory", "modem", "self_destruct", "motion_sensor".
    level : int | float
        The target *value* for the upgrade.  For CPU this is the speed
        (e.g. 120), for modem the Gq/s rating, for memory the Gq capacity.
        For security items (self_destruct / motion_sensor) this is ignored.

    Returns
    -------
    dict with "success" bool and contextual info.
    """
    player, gateway = _get_player_and_gateway(session_id, player_id)

    if hardware_type == "cpu":
        return _buy_cpu(player, gateway, level)
    elif hardware_type == "modem":
        return _buy_modem(player, gateway, level)
    elif hardware_type == "memory":
        return _buy_memory(player, gateway, level)
    elif hardware_type == "self_destruct":
        return _buy_security_device(player, gateway, "self_destruct")
    elif hardware_type == "motion_sensor":
        return _buy_security_device(player, gateway, "motion_sensor")
    else:
        return {"success": False, "reason": f"Unknown hardware type: {hardware_type}"}


def _buy_cpu(player, gateway, target_speed):
    target_speed = int(target_speed)
    if target_speed <= gateway.cpu_speed:
        return {"success": False, "reason": "Target CPU is not an upgrade"}

    net_cost = _compute_upgrade_cost(
        C.GATEWAYUPGRADETYPE_CPU, gateway.cpu_speed, target_speed
    )
    if net_cost is None:
        return {"success": False, "reason": f"Invalid CPU speed: {target_speed}"}
    if player.balance < net_cost:
        return {
            "success": False,
            "reason": f"Insufficient funds (need {net_cost}c, have {player.balance}c)",
        }

    player.balance -= net_cost
    gateway.cpu_speed = target_speed
    db.session.flush()

    log.info("Player %s upgraded CPU to %d GHz (cost %dc)", player.id, target_speed, net_cost)
    return {
        "success": True,
        "hardware_type": "cpu",
        "new_value": target_speed,
        "cost": net_cost,
        "balance": player.balance,
    }


def _buy_modem(player, gateway, target_speed):
    target_speed = int(target_speed)
    if target_speed <= gateway.modem_speed:
        return {"success": False, "reason": "Target modem is not an upgrade"}

    net_cost = _compute_upgrade_cost(
        C.GATEWAYUPGRADETYPE_MODEM, gateway.modem_speed, target_speed
    )
    if net_cost is None:
        return {"success": False, "reason": f"Invalid modem speed: {target_speed}"}
    if player.balance < net_cost:
        return {
            "success": False,
            "reason": f"Insufficient funds (need {net_cost}c, have {player.balance}c)",
        }

    player.balance -= net_cost
    gateway.modem_speed = target_speed
    db.session.flush()

    log.info("Player %s upgraded modem to %d Gq/s (cost %dc)", player.id, target_speed, net_cost)
    return {
        "success": True,
        "hardware_type": "modem",
        "new_value": target_speed,
        "cost": net_cost,
        "balance": player.balance,
    }


def _buy_memory(player, gateway, target_size):
    target_size = int(target_size)
    if target_size <= gateway.memory_size:
        return {"success": False, "reason": "Target memory is not an upgrade"}

    net_cost = _compute_upgrade_cost(
        C.GATEWAYUPGRADETYPE_MEMORY, gateway.memory_size, target_size
    )
    if net_cost is None:
        return {"success": False, "reason": f"Invalid memory size: {target_size}"}
    if player.balance < net_cost:
        return {
            "success": False,
            "reason": f"Insufficient funds (need {net_cost}c, have {player.balance}c)",
        }

    player.balance -= net_cost
    gateway.memory_size = target_size
    db.session.flush()

    log.info("Player %s upgraded memory to %d Gq (cost %dc)", player.id, target_size, net_cost)
    return {
        "success": True,
        "hardware_type": "memory",
        "new_value": target_size,
        "cost": net_cost,
        "balance": player.balance,
    }


def _buy_security_device(player, gateway, device_type):
    """Buy Gateway Self Destruct or Gateway Motion Sensor."""
    if device_type == "self_destruct":
        if gateway.has_self_destruct:
            return {"success": False, "reason": "Self Destruct is already installed"}
        # Find the catalog entry
        entry = None
        for e in C.HARDWARE_UPGRADES:
            if e[0] == "Gateway Self Destruct":
                entry = e
                break
        if entry is None:
            return {"success": False, "reason": "Self Destruct not in catalog"}
        cost = entry[2]
        if player.balance < cost:
            return {
                "success": False,
                "reason": f"Insufficient funds (need {cost}c, have {player.balance}c)",
            }
        player.balance -= cost
        gateway.has_self_destruct = True
        db.session.flush()

        log.info("Player %s installed Gateway Self Destruct (cost %dc)", player.id, cost)
        return {
            "success": True,
            "hardware_type": "self_destruct",
            "new_value": True,
            "cost": cost,
            "balance": player.balance,
        }

    elif device_type == "motion_sensor":
        if gateway.has_motion_sensor:
            return {"success": False, "reason": "Motion Sensor is already installed"}
        entry = None
        for e in C.HARDWARE_UPGRADES:
            if e[0] == "Gateway Motion Sensor":
                entry = e
                break
        if entry is None:
            return {"success": False, "reason": "Motion Sensor not in catalog"}
        cost = entry[2]
        if player.balance < cost:
            return {
                "success": False,
                "reason": f"Insufficient funds (need {cost}c, have {player.balance}c)",
            }
        player.balance -= cost
        gateway.has_motion_sensor = True
        db.session.flush()

        log.info("Player %s installed Gateway Motion Sensor (cost %dc)", player.id, cost)
        return {
            "success": True,
            "hardware_type": "motion_sensor",
            "new_value": True,
            "cost": cost,
            "balance": player.balance,
        }

    return {"success": False, "reason": f"Unknown security device: {device_type}"}


# ===================================================================
# Software purchasing
# ===================================================================

def buy_software(session_id, player_id, tool_name, version):
    """Buy (or upgrade) a software tool and install it on the player's gateway.

    Parameters
    ----------
    session_id : str
    player_id : int
    tool_name : str
        Software name as it appears in SOFTWARE_UPGRADES (e.g. "Decrypter").
    version : int
        Target version number.

    Returns
    -------
    dict with "success" bool and contextual info.
    """
    player, gateway = _get_player_and_gateway(session_id, player_id)

    # Locate the catalog entry
    catalog_entry = None
    for name, sw_type, cost, size, ver, description in C.SOFTWARE_UPGRADES:
        if name == tool_name and ver == version:
            catalog_entry = {
                "name": name,
                "sw_type": sw_type,
                "cost": cost,
                "size": size,
                "version": ver,
                "description": description,
            }
            break

    if catalog_entry is None:
        return {"success": False, "reason": f"Software '{tool_name}' v{version} not found in catalog"}

    # Resolve gateway computer
    gateway_computer_id = _get_gateway_computer_id(session_id, player)
    if gateway_computer_id is None:
        return {"success": False, "reason": "Gateway computer not found"}

    # Check if the player already has this tool installed (any version)
    existing_file = DataFile.query.filter(
        DataFile.computer_id == gateway_computer_id,
        DataFile.softwaretype == catalog_entry["sw_type"],
        DataFile.filename.like(f"{tool_name}%"),
    ).first()

    if existing_file is not None:
        # Parse current version from filename (e.g. "Decrypter v3")
        existing_version = _parse_version_from_filename(existing_file.filename)
        if existing_version >= version:
            return {
                "success": False,
                "reason": f"Already have {tool_name} v{existing_version} (same or newer)",
            }

    # Check storage capacity -- compute used space on gateway
    all_gateway_files = DataFile.query.filter_by(computer_id=gateway_computer_id).all()
    used_space = sum(f.size for f in all_gateway_files)
    new_size = catalog_entry["size"]

    # If upgrading, the old file will be replaced, so free its space
    if existing_file is not None:
        used_space -= existing_file.size

    if used_space + new_size > gateway.memory_size:
        return {
            "success": False,
            "reason": (
                f"Not enough memory (need {new_size} Gq, "
                f"available {gateway.memory_size - used_space} Gq)"
            ),
        }

    # Check funds -- give partial refund when upgrading
    cost = catalog_entry["cost"]
    if existing_file is not None:
        old_catalog_cost = _find_software_cost(tool_name, _parse_version_from_filename(existing_file.filename))
        refund = int(old_catalog_cost * PART_EXCHANGE)
        cost = max(0, cost - refund)

    if player.balance < cost:
        return {
            "success": False,
            "reason": f"Insufficient funds (need {cost}c, have {player.balance}c)",
        }

    # Perform the purchase
    player.balance -= cost

    if existing_file is not None:
        # Upgrade in place
        existing_file.filename = f"{tool_name} v{version}"
        existing_file.size = new_size
        existing_file.data = catalog_entry["description"]
    else:
        # Install new
        new_file = DataFile(
            computer_id=gateway_computer_id,
            filename=f"{tool_name} v{version}",
            size=new_size,
            file_type=FILETYPE_SOFTWARE,
            softwaretype=catalog_entry["sw_type"],
            data=catalog_entry["description"],
            owner=player.handle,
        )
        db.session.add(new_file)

    db.session.flush()

    log.info(
        "Player %s bought %s v%d (cost %dc)",
        player.id, tool_name, version, cost,
    )
    return {
        "success": True,
        "tool_name": tool_name,
        "version": version,
        "cost": cost,
        "balance": player.balance,
    }


def _parse_version_from_filename(filename):
    """Extract version number from a filename like 'Decrypter v3'.
    Returns 1 if no version suffix is found.
    """
    parts = filename.rsplit(" v", 1)
    if len(parts) == 2:
        try:
            return int(parts[1])
        except (ValueError, TypeError):
            pass
    return 1


def _find_software_cost(tool_name, version):
    """Return catalog cost of a specific software version, or 0."""
    for name, _sw_type, cost, _size, ver, _desc in C.SOFTWARE_UPGRADES:
        if name == tool_name and ver == version:
            return cost
    return 0


# ===================================================================
# Query helpers
# ===================================================================

def get_player_software(session_id, player_id):
    """Return a list of software installed on the player's gateway.

    Each item is a dict with keys:
        id, filename, size, file_type, softwaretype, encrypted_level, data
    """
    player = Player.query.filter_by(
        id=player_id, game_session_id=session_id
    ).first()
    if player is None:
        return []

    gateway_computer_id = _get_gateway_computer_id(session_id, player)
    if gateway_computer_id is None:
        return []

    files = DataFile.query.filter_by(computer_id=gateway_computer_id).all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "size": f.size,
            "file_type": f.file_type,
            "softwaretype": f.softwaretype,
            "encrypted_level": f.encrypted_level,
            "data": f.data,
        }
        for f in files
    ]


def get_gateway_info(session_id, player_id):
    """Return full hardware details for the player's gateway.

    Returns a dict with gateway specs plus computed fields like
    used/free memory and the catalog entries for potential upgrades.
    """
    player, gateway = _get_player_and_gateway(session_id, player_id)

    gateway_computer_id = _get_gateway_computer_id(session_id, player)
    used_memory = 0
    if gateway_computer_id is not None:
        files = DataFile.query.filter_by(computer_id=gateway_computer_id).all()
        used_memory = sum(f.size for f in files)

    return {
        "id": gateway.id,
        "name": gateway.name,
        "cpu_speed": gateway.cpu_speed,
        "modem_speed": gateway.modem_speed,
        "memory_size": gateway.memory_size,
        "memory_used": used_memory,
        "memory_free": gateway.memory_size - used_memory,
        "has_self_destruct": gateway.has_self_destruct,
        "has_motion_sensor": gateway.has_motion_sensor,
        "balance": player.balance,
    }
