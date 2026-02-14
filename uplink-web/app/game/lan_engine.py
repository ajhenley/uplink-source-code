"""LAN hacking engine -- models local area networks within high-security computers.

Faithfully ported from the C++ LanComputer / LanMonitor / LanGenerator system.
Instead of remote Internet access, players navigate a tree-structured network
topology: Router -> Switches/Hubs -> Servers/Terminals.

Topology and per-session LAN state are stored in-memory, keyed by
(session_id, computer_id).  Topology is generated on first access.
"""
import logging
import random

from app.extensions import db
from app.models.computer import Computer
from app.game import constants as C

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LAN system type constants (mirrors LANSYSTEM_* from lancomputer.h)
# ---------------------------------------------------------------------------
LANSYSTEM_NONE = 0
LANSYSTEM_ROUTER = 1
LANSYSTEM_HUB = 2
LANSYSTEM_SWITCH = 3
LANSYSTEM_TERMINAL = 4
LANSYSTEM_MAINSERVER = 5
LANSYSTEM_MAILSERVER = 6
LANSYSTEM_FILESERVER = 7
LANSYSTEM_AUTHENTICATION = 8
LANSYSTEM_LOCK = 9
LANSYSTEM_ISOLATIONBRIDGE = 10
LANSYSTEM_MODEM = 11
LANSYSTEM_SESSIONKEYSERVER = 12
LANSYSTEM_RADIOTRANSMITTER = 13
LANSYSTEM_RADIORECEIVER = 14
LANSYSTEM_FAXPRINTER = 15
LANSYSTEM_LOGSERVER = 16

# Human-readable labels for each type
LANSYSTEM_NAMES = {
    LANSYSTEM_NONE: "none",
    LANSYSTEM_ROUTER: "router",
    LANSYSTEM_HUB: "hub",
    LANSYSTEM_SWITCH: "switch",
    LANSYSTEM_TERMINAL: "terminal",
    LANSYSTEM_MAINSERVER: "main_server",
    LANSYSTEM_MAILSERVER: "mail_server",
    LANSYSTEM_FILESERVER: "file_server",
    LANSYSTEM_AUTHENTICATION: "auth_server",
    LANSYSTEM_LOCK: "lock",
    LANSYSTEM_ISOLATIONBRIDGE: "isolation_bridge",
    LANSYSTEM_MODEM: "modem",
    LANSYSTEM_SESSIONKEYSERVER: "session_key_server",
    LANSYSTEM_RADIOTRANSMITTER: "radio_transmitter",
    LANSYSTEM_RADIORECEIVER: "radio_receiver",
    LANSYSTEM_FAXPRINTER: "fax_printer",
    LANSYSTEM_LOGSERVER: "log_server",
}

# Visibility levels (mirrors LANSYSTEMVISIBLE_*)
VISIBLE_NONE = 0
VISIBLE_AWARE = 1
VISIBLE_TYPE = 2
VISIBLE_FULL = 3

# Link visibility (mirrors LANLINKVISIBLE_*)
LINKVISIBLE_NONE = 0
LINKVISIBLE_FROMAWARE = 1
LINKVISIBLE_TOAWARE = 2
LINKVISIBLE_AWARE = 3

# Sys-admin states (mirrors SYSADMIN_*)
SYSADMIN_ASLEEP = 0
SYSADMIN_CURIOUS = 1
SYSADMIN_SEARCHING = 2
SYSADMIN_FOUNDYOU = 3

# Tool names required for each LAN action
REQUIRED_TOOLS = {
    "scan": "LAN_Scan",
    "probe": "LAN_Probe",
    "spoof": "LAN_Spoof",
    "force": "LAN_Force",
    "deploy_sensor": "Motionsensor",
}

# ---------------------------------------------------------------------------
# In-memory state: keyed by (session_id, computer_id)
# ---------------------------------------------------------------------------
_lan_states = {}


# ===================================================================
# Data structures
# ===================================================================

def _make_system(system_type, x, y, security=2, screen_index=-1,
                 data_screen_index=-1):
    """Create a LAN system (node) dict."""
    subnet = random.randint(0, C.LAN_SUBNETRANGE - 1)
    return {
        "type": system_type,
        "type_name": LANSYSTEM_NAMES.get(system_type, "unknown"),
        "x": x,
        "y": y,
        "visible": VISIBLE_TYPE if system_type == LANSYSTEM_ROUTER else VISIBLE_NONE,
        "subnet": subnet,
        "security": security,
        "screen_index": screen_index,
        "data_screen_index": data_screen_index,
        "data1": -1,
        "data2": -1,
        "data3": -1,
        "valid_subnets": [],
        "is_compromised": False,
    }


def _make_link(from_idx, from_x, from_y, to_idx, to_x, to_y, security=1):
    """Create a LAN link (edge) dict."""
    return {
        "from": from_idx,
        "to": to_idx,
        "from_x": from_x,
        "from_y": from_y,
        "to_x": to_x,
        "to_y": to_y,
        "port": random.randint(0, C.LAN_LINKPORTRANGE - 1),
        "security": security,
        "visible": LINKVISIBLE_NONE,
    }


def _make_state(topology):
    """Create a fresh per-session LAN state wrapping a topology."""
    # Find the router as the entry point
    current_system = -1
    for idx, sys in enumerate(topology["systems"]):
        if sys["type"] == LANSYSTEM_ROUTER:
            current_system = idx
            break

    return {
        "topology": topology,
        "current_system": current_system,
        "current_selected": current_system,
        "current_spoof": -1,
        "connection": [current_system] if current_system >= 0 else [],
        "sysadmin_state": SYSADMIN_ASLEEP,
        "sysadmin_current_system": -1,
        "sysadmin_timer": 0,
        "sysadmin_ticks_remaining": 0,
        "deployed_sensors": [],
    }


# ===================================================================
# Topology generation
# ===================================================================

def generate_lan_topology(computer_id, security_level=3):
    """Generate a LAN topology for a computer.  Returns topology dict.

    Difficulty drives the complexity of the generated network:
        0 - Simple: router + hub + a few terminals
        1 - Basic:  adds an auth/lock pair
        2 - Medium: two clusters with log server
        3 - Hard:   multiple clusters, isolation bridge, auth chains
        4 - Expert: full multi-cluster with radio links
    """
    difficulty = max(0, min(4, security_level))

    systems = []
    links = []

    def add_system(system_type, x, y, security=2, **kwargs):
        sys = _make_system(system_type, x, y, security)
        for k, v in kwargs.items():
            if k in sys:
                sys[k] = v
        idx = len(systems)
        systems.append(sys)
        return idx

    def add_link(from_idx, from_x, from_y, to_idx, to_x, to_y, security=1):
        lnk = _make_link(from_idx, from_x, from_y, to_idx, to_x, to_y, security)
        links.append(lnk)

    if difficulty == 0:
        _gen_level0(add_system, add_link)
    elif difficulty == 1:
        _gen_level1(add_system, add_link)
    elif difficulty == 2:
        _gen_level2(add_system, add_link)
    elif difficulty == 3:
        _gen_level3(add_system, add_link)
    else:
        _gen_level4(add_system, add_link)

    topology = {
        "computer_id": computer_id,
        "difficulty": difficulty,
        "systems": systems,
        "links": links,
    }
    return topology


def _gen_level0(add_sys, add_link):
    """Simple LAN: router -> hub -> 2-4 terminals."""
    router = add_sys(LANSYSTEM_ROUTER, 200, 40, 1)
    hub = add_sys(LANSYSTEM_HUB, 200, 140, 1)
    add_link(router, 0.5, 1.0, hub, 0.5, 0.0, 1)

    num_terminals = random.randint(2, 4)
    spacing = 120
    start_x = 200 - (num_terminals - 1) * spacing // 2
    for i in range(num_terminals):
        t = add_sys(LANSYSTEM_TERMINAL, start_x + i * spacing, 240, 1)
        frac = (i + 1) / (num_terminals + 1)
        add_link(hub, frac, 1.0, t, 0.5, 0.0, 1)

    # One file server off the hub
    fs = add_sys(LANSYSTEM_FILESERVER, 200, 340, 2)
    add_link(hub, 0.5, 1.0, fs, 0.5, 0.0, 1)


def _gen_level1(add_sys, add_link):
    """Basic LAN with auth/lock pair: router -> hub -> auth + lock -> server."""
    router = add_sys(LANSYSTEM_ROUTER, 200, 30, 1)
    hub = add_sys(LANSYSTEM_HUB, 200, 130, 1)
    add_link(router, 0.5, 1.0, hub, 0.5, 0.0, 1)

    # Terminal branch
    t1 = add_sys(LANSYSTEM_TERMINAL, 80, 230, 1)
    t2 = add_sys(LANSYSTEM_TERMINAL, 320, 230, 1)
    add_link(hub, 0.2, 1.0, t1, 0.5, 0.0, 1)
    add_link(hub, 0.8, 1.0, t2, 0.5, 0.0, 1)

    # Lock and auth
    lock = add_sys(LANSYSTEM_LOCK, 200, 230, 2, data1=1)
    auth = add_sys(LANSYSTEM_AUTHENTICATION, 80, 330, 2, data1=lock)
    add_link(hub, 0.5, 1.0, lock, 0.5, 0.0, 1)
    add_link(hub, 0.3, 1.0, auth, 0.5, 0.0, 1)

    # Main server behind lock
    server = add_sys(LANSYSTEM_MAINSERVER, 200, 370, 3)
    add_link(lock, 0.5, 1.0, server, 0.5, 0.0, 1)


def _gen_level2(add_sys, add_link):
    """Medium LAN with two sub-clusters, a log server, and auth chains."""
    router = add_sys(LANSYSTEM_ROUTER, 250, 20, 1)

    # Left cluster
    hub1 = add_sys(LANSYSTEM_HUB, 100, 120, 2)
    add_link(router, 0.3, 1.0, hub1, 0.5, 0.0, 1)

    t1 = add_sys(LANSYSTEM_TERMINAL, 20, 220, 1)
    t2 = add_sys(LANSYSTEM_TERMINAL, 180, 220, 1)
    add_link(hub1, 0.3, 1.0, t1, 0.5, 0.0, 1)
    add_link(hub1, 0.7, 1.0, t2, 0.5, 0.0, 1)

    log_srv = add_sys(LANSYSTEM_LOGSERVER, 100, 320, 3)
    add_link(hub1, 0.5, 1.0, log_srv, 0.5, 0.0, 1)

    # Right cluster
    hub2 = add_sys(LANSYSTEM_HUB, 400, 120, 2)
    add_link(router, 0.7, 1.0, hub2, 0.5, 0.0, 1)

    lock = add_sys(LANSYSTEM_LOCK, 400, 220, 2, data1=1)
    auth = add_sys(LANSYSTEM_AUTHENTICATION, 320, 320, 3, data1=lock)
    add_link(hub2, 0.5, 1.0, lock, 0.5, 0.0, 1)
    add_link(hub2, 0.3, 1.0, auth, 0.5, 0.0, 1)

    file_srv = add_sys(LANSYSTEM_FILESERVER, 400, 320, 3)
    add_link(lock, 0.5, 1.0, file_srv, 0.5, 0.0, 1)

    main_srv = add_sys(LANSYSTEM_MAINSERVER, 400, 420, 4)
    add_link(file_srv, 0.5, 1.0, main_srv, 0.5, 0.0, 1)


def _gen_level3(add_sys, add_link):
    """Hard LAN with isolation bridge, multiple auth chains, and modem."""
    router = add_sys(LANSYSTEM_ROUTER, 300, 20, 1)
    hub1 = add_sys(LANSYSTEM_HUB, 150, 120, 2)
    hub2 = add_sys(LANSYSTEM_HUB, 450, 120, 2)
    add_link(router, 0.3, 1.0, hub1, 0.5, 0.0, 1)
    add_link(router, 0.7, 1.0, hub2, 0.5, 0.0, 1)

    # Left branch: terminals and log server
    t1 = add_sys(LANSYSTEM_TERMINAL, 50, 220, 1)
    t2 = add_sys(LANSYSTEM_TERMINAL, 250, 220, 1)
    add_link(hub1, 0.3, 1.0, t1, 0.5, 0.0, 1)
    add_link(hub1, 0.7, 1.0, t2, 0.5, 0.0, 1)

    log_srv = add_sys(LANSYSTEM_LOGSERVER, 150, 320, 3)
    add_link(hub1, 0.5, 1.0, log_srv, 0.5, 0.0, 1)

    # Right branch: lock1 -> isolation bridge -> main server
    lock1 = add_sys(LANSYSTEM_LOCK, 350, 220, 2, data1=1)
    lock2 = add_sys(LANSYSTEM_LOCK, 550, 220, 3, data1=1)
    add_link(hub2, 0.3, 1.0, lock1, 0.5, 0.0, 1)
    add_link(hub2, 0.7, 1.0, lock2, 0.5, 0.0, 1)

    # Auth servers for both locks
    auth1 = add_sys(LANSYSTEM_AUTHENTICATION, 350, 320, 3, data1=lock1)
    auth2 = add_sys(LANSYSTEM_AUTHENTICATION, 550, 320, 4, data1=lock2)
    add_link(hub2, 0.4, 1.0, auth1, 0.5, 0.0, 1)
    add_link(hub2, 0.6, 1.0, auth2, 0.5, 0.0, 1)

    # Isolation bridge behind the locks
    iso_bridge = add_sys(LANSYSTEM_ISOLATIONBRIDGE, 450, 420, 4,
                         data1=lock1, data2=lock2)
    add_link(lock1, 0.5, 1.0, iso_bridge, 0.3, 0.0, 1)
    add_link(lock2, 0.5, 1.0, iso_bridge, 0.7, 0.0, 1)

    main_srv = add_sys(LANSYSTEM_MAINSERVER, 450, 520, 5)
    add_link(iso_bridge, 0.5, 1.0, main_srv, 0.5, 0.0, 1)

    # Modem for alternative entry
    modem = add_sys(LANSYSTEM_MODEM, 50, 420, 3)
    add_link(log_srv, 0.5, 1.0, modem, 0.5, 0.0, 1)


def _gen_level4(add_sys, add_link):
    """Expert LAN: three clusters with session key server and radio links."""
    router = add_sys(LANSYSTEM_ROUTER, 350, 20, 1)

    # --- Cluster A (left): terminals behind auth ---
    hub_a = add_sys(LANSYSTEM_HUB, 120, 120, 2)
    add_link(router, 0.2, 1.0, hub_a, 0.5, 0.0, 1)

    t1 = add_sys(LANSYSTEM_TERMINAL, 30, 220, 1)
    t2 = add_sys(LANSYSTEM_TERMINAL, 210, 220, 1)
    add_link(hub_a, 0.3, 1.0, t1, 0.5, 0.0, 1)
    add_link(hub_a, 0.7, 1.0, t2, 0.5, 0.0, 1)

    lock_a = add_sys(LANSYSTEM_LOCK, 120, 320, 2, data1=1)
    auth_a = add_sys(LANSYSTEM_AUTHENTICATION, 30, 320, 3, data1=lock_a)
    add_link(hub_a, 0.5, 1.0, lock_a, 0.5, 0.0, 1)
    add_link(hub_a, 0.2, 1.0, auth_a, 0.5, 0.0, 1)

    log_srv = add_sys(LANSYSTEM_LOGSERVER, 120, 420, 3)
    add_link(lock_a, 0.5, 1.0, log_srv, 0.5, 0.0, 1)

    # --- Cluster B (center): session key server + file server ---
    hub_b = add_sys(LANSYSTEM_HUB, 350, 120, 2)
    add_link(router, 0.5, 1.0, hub_b, 0.5, 0.0, 1)

    sess_key = add_sys(LANSYSTEM_SESSIONKEYSERVER, 350, 220, 3)
    add_link(hub_b, 0.5, 1.0, sess_key, 0.5, 0.0, 1)

    file_srv = add_sys(LANSYSTEM_FILESERVER, 350, 340, 4)
    add_link(sess_key, 0.5, 1.0, file_srv, 0.5, 0.0, 1)

    # --- Cluster C (right): isolation bridge guarding main server ---
    hub_c = add_sys(LANSYSTEM_HUB, 580, 120, 2)
    add_link(router, 0.8, 1.0, hub_c, 0.5, 0.0, 1)

    lock_c1 = add_sys(LANSYSTEM_LOCK, 500, 220, 3, data1=1)
    lock_c2 = add_sys(LANSYSTEM_LOCK, 660, 220, 3, data1=1)
    add_link(hub_c, 0.3, 1.0, lock_c1, 0.5, 0.0, 1)
    add_link(hub_c, 0.7, 1.0, lock_c2, 0.5, 0.0, 1)

    auth_c1 = add_sys(LANSYSTEM_AUTHENTICATION, 500, 320, 4, data1=lock_c1)
    auth_c2 = add_sys(LANSYSTEM_AUTHENTICATION, 660, 320, 4, data1=lock_c2)
    add_link(hub_c, 0.35, 1.0, auth_c1, 0.5, 0.0, 1)
    add_link(hub_c, 0.65, 1.0, auth_c2, 0.5, 0.0, 1)

    iso_bridge = add_sys(LANSYSTEM_ISOLATIONBRIDGE, 580, 420, 5,
                         data1=lock_c1, data2=lock_c2)
    add_link(lock_c1, 0.5, 1.0, iso_bridge, 0.3, 0.0, 1)
    add_link(lock_c2, 0.5, 1.0, iso_bridge, 0.7, 0.0, 1)

    main_srv = add_sys(LANSYSTEM_MAINSERVER, 580, 520, 5)
    add_link(iso_bridge, 0.5, 1.0, main_srv, 0.5, 0.0, 1)

    # Radio link between clusters A and C
    radio_tx = add_sys(LANSYSTEM_RADIOTRANSMITTER, 210, 420, 3)
    radio_rx = add_sys(LANSYSTEM_RADIORECEIVER, 500, 420, 3)
    freq = random.randint(C.RADIOTRANSMITTER_MINRANGE, C.RADIOTRANSMITTER_MAXRANGE)
    radio_tx["data1"] = freq
    # Receivers store freq in data1/data2 (ghz/mhz) -- we simplify
    radio_rx["data1"] = freq
    add_link(log_srv, 0.5, 1.0, radio_tx, 0.5, 0.0, 1)
    # Radio links are not wired -- player must discover the frequency

    # Modem as alternative back-door
    modem = add_sys(LANSYSTEM_MODEM, 350, 460, 3)
    add_link(file_srv, 0.5, 1.0, modem, 0.5, 0.0, 1)


# ===================================================================
# State management
# ===================================================================

def _state_key(session_id, computer_id):
    return (str(session_id), int(computer_id))


def _ensure_state(session_id, computer_id):
    """Return the LAN state for this session+computer, generating if needed."""
    key = _state_key(session_id, computer_id)
    if key not in _lan_states:
        computer = Computer.query.get(computer_id)
        if computer is None:
            raise ValueError(f"Computer {computer_id} not found")
        sec = int(computer.hack_difficulty / 100) if computer.hack_difficulty else 3
        sec = max(0, min(4, sec))
        topo = generate_lan_topology(computer_id, security_level=sec)
        _lan_states[key] = _make_state(topo)
    return _lan_states[key]


def get_lan_state(session_id, computer_id):
    """Get current LAN state for a connected computer.

    Returns a sanitised view suitable for sending to the client -- nodes the
    player cannot yet see are masked.
    """
    state = _ensure_state(session_id, computer_id)
    topo = state["topology"]

    # Build client-visible system list
    visible_systems = []
    for idx, sys in enumerate(topo["systems"]):
        entry = {"id": idx}
        if sys["visible"] >= VISIBLE_AWARE:
            entry["visible"] = sys["visible"]
            entry["x"] = sys["x"]
            entry["y"] = sys["y"]
            entry["is_compromised"] = sys["is_compromised"]
        if sys["visible"] >= VISIBLE_TYPE:
            entry["type"] = sys["type"]
            entry["type_name"] = sys["type_name"]
            entry["security"] = sys["security"]
        if sys["visible"] >= VISIBLE_FULL:
            entry["subnet"] = sys["subnet"]
            entry["data1"] = sys["data1"]
            entry["data2"] = sys["data2"]
            entry["data3"] = sys["data3"]
        if sys["visible"] < VISIBLE_AWARE:
            entry["visible"] = VISIBLE_NONE
        visible_systems.append(entry)

    # Build client-visible link list
    visible_links = []
    for lnk in topo["links"]:
        if lnk["visible"] >= LINKVISIBLE_AWARE:
            visible_links.append({
                "from": lnk["from"],
                "to": lnk["to"],
                "from_x": lnk["from_x"],
                "from_y": lnk["from_y"],
                "to_x": lnk["to_x"],
                "to_y": lnk["to_y"],
                "security": lnk["security"],
                "visible": lnk["visible"],
            })
        elif lnk["visible"] == LINKVISIBLE_FROMAWARE:
            visible_links.append({
                "from": lnk["from"],
                "to": -1,
                "visible": lnk["visible"],
            })
        elif lnk["visible"] == LINKVISIBLE_TOAWARE:
            visible_links.append({
                "from": -1,
                "to": lnk["to"],
                "visible": lnk["visible"],
            })

    return {
        "computer_id": topo["computer_id"],
        "difficulty": topo["difficulty"],
        "systems": visible_systems,
        "links": visible_links,
        "current_system": state["current_system"],
        "current_selected": state["current_selected"],
        "current_spoof": state["current_spoof"],
        "connection": list(state["connection"]),
        "sysadmin_state": state["sysadmin_state"],
        "deployed_sensors": list(state["deployed_sensors"]),
    }


def reset_lan_state(session_id, computer_id):
    """Clear the LAN state when a player disconnects from the computer."""
    key = _state_key(session_id, computer_id)
    _lan_states.pop(key, None)


# ===================================================================
# Actions
# ===================================================================

def lan_action(session_id, player_id, computer_id, action, node_id=None,
               tool_version=1, **kwargs):
    """Handle LAN actions: scan, probe, spoof, force, move, deploy_sensor.

    Parameters
    ----------
    session_id : str
        Current game session.
    player_id : int
        The acting player.
    computer_id : int
        The LAN computer being hacked.
    action : str
        One of "scan", "probe", "spoof", "force", "move", "deploy_sensor".
    node_id : int or None
        Target node index for the action (required for most actions).
    tool_version : int
        Version of the tool being used (affects effectiveness).
    **kwargs
        Additional action-specific parameters.

    Returns
    -------
    dict
        Result of the action, including updated state.
    """
    state = _ensure_state(session_id, computer_id)
    topo = state["topology"]

    if action == "scan":
        return _action_scan(state, topo, node_id, tool_version)
    elif action == "probe":
        return _action_probe(state, topo, node_id, tool_version)
    elif action == "spoof":
        return _action_spoof(state, topo, node_id, tool_version)
    elif action == "force":
        return _action_force(state, topo, node_id, tool_version)
    elif action == "move":
        return _action_move(state, topo, node_id)
    elif action == "deploy_sensor":
        return _action_deploy_sensor(state, topo, node_id)
    else:
        return {"success": False, "error": f"Unknown LAN action: {action}"}


def _action_scan(state, topo, node_id, tool_version):
    """Discover adjacent nodes and links from the current position.

    Scanning from the current system reveals links emanating from it and makes
    adjacent nodes at least VISIBLE_AWARE.  Higher tool versions reveal more
    details (VISIBLE_TYPE at v2+, VISIBLE_FULL at v3+).
    """
    current = state["current_system"]
    if current < 0:
        return {"success": False, "error": "Not positioned on any LAN system"}

    discovered_nodes = []
    discovered_links = []

    for lnk in topo["links"]:
        adjacent = -1
        if lnk["from"] == current:
            adjacent = lnk["to"]
        elif lnk["to"] == current:
            adjacent = lnk["from"]

        if adjacent < 0:
            continue

        # Reveal the link
        if lnk["visible"] < LINKVISIBLE_AWARE:
            lnk["visible"] = LINKVISIBLE_AWARE
            discovered_links.append({
                "from": lnk["from"],
                "to": lnk["to"],
            })

        # Reveal the adjacent system
        adj_sys = topo["systems"][adjacent]
        old_vis = adj_sys["visible"]

        if tool_version >= 3:
            target_vis = VISIBLE_FULL
        elif tool_version >= 2:
            target_vis = VISIBLE_TYPE
        else:
            target_vis = VISIBLE_AWARE

        if target_vis > adj_sys["visible"]:
            adj_sys["visible"] = target_vis

        if old_vis < adj_sys["visible"]:
            discovered_nodes.append(adjacent)

    return {
        "success": True,
        "action": "scan",
        "discovered_nodes": discovered_nodes,
        "discovered_links": discovered_links,
        "current_system": current,
    }


def _action_probe(state, topo, node_id, tool_version):
    """Get full details of a specific node.

    Requires the node to already be at least VISIBLE_AWARE.
    Probing raises visibility to VISIBLE_FULL.
    """
    if node_id is None:
        return {"success": False, "error": "probe requires a node_id"}

    if node_id < 0 or node_id >= len(topo["systems"]):
        return {"success": False, "error": f"Invalid node_id: {node_id}"}

    sys = topo["systems"][node_id]
    if sys["visible"] < VISIBLE_AWARE:
        return {"success": False, "error": "Node not yet discovered -- scan first"}

    # Increase visibility based on tool version
    if tool_version >= 2:
        sys["visible"] = VISIBLE_FULL
    else:
        if sys["visible"] < VISIBLE_TYPE:
            sys["visible"] = VISIBLE_TYPE

    return {
        "success": True,
        "action": "probe",
        "node_id": node_id,
        "type": sys["type"],
        "type_name": sys["type_name"],
        "security": sys["security"],
        "subnet": sys["subnet"],
        "visible": sys["visible"],
        "data1": sys["data1"],
        "data2": sys["data2"],
        "data3": sys["data3"],
    }


def _action_spoof(state, topo, node_id, tool_version):
    """Bypass an authentication server by spoofing credentials.

    On success, the auth server is compromised and any locks it controls
    are unlocked.
    """
    if node_id is None:
        return {"success": False, "error": "spoof requires a node_id"}

    if node_id < 0 or node_id >= len(topo["systems"]):
        return {"success": False, "error": f"Invalid node_id: {node_id}"}

    sys = topo["systems"][node_id]
    if sys["type"] != LANSYSTEM_AUTHENTICATION:
        return {"success": False, "error": "Can only spoof authentication servers"}

    if sys["visible"] < VISIBLE_TYPE:
        return {"success": False, "error": "Node not sufficiently scanned"}

    # Check difficulty vs tool version
    difficulty_roll = sys["security"] - tool_version
    if difficulty_roll > 0 and random.random() < 0.15 * difficulty_roll:
        # Spoofing failed -- alert sys-admin
        _alert_sysadmin(state)
        return {"success": False, "error": "Spoof failed -- sys-admin alerted"}

    sys["is_compromised"] = True

    # Set our spoof address to this auth server's subnet
    state["current_spoof"] = sys["subnet"]

    # Unlock any locks controlled by this auth server
    unlocked = []
    lock_idx = sys.get("data1", -1)
    if lock_idx >= 0 and lock_idx < len(topo["systems"]):
        lock_sys = topo["systems"][lock_idx]
        if lock_sys["type"] == LANSYSTEM_LOCK:
            lock_sys["data1"] = 0  # unlocked
            lock_sys["is_compromised"] = True
            unlocked.append(lock_idx)

    return {
        "success": True,
        "action": "spoof",
        "node_id": node_id,
        "spoofed_subnet": sys["subnet"],
        "unlocked_locks": unlocked,
    }


def _action_force(state, topo, node_id, tool_version):
    """Brute-force a lock node to open it.

    On success the lock is opened (data1 = 0).  Higher security locks are
    harder to force; low tool versions may fail and alert the sys-admin.
    """
    if node_id is None:
        return {"success": False, "error": "force requires a node_id"}

    if node_id < 0 or node_id >= len(topo["systems"]):
        return {"success": False, "error": f"Invalid node_id: {node_id}"}

    sys = topo["systems"][node_id]
    if sys["type"] != LANSYSTEM_LOCK:
        return {"success": False, "error": "Can only force lock nodes"}

    if sys["visible"] < VISIBLE_TYPE:
        return {"success": False, "error": "Node not sufficiently scanned"}

    if sys["data1"] == 0:
        return {"success": True, "action": "force", "node_id": node_id,
                "already_unlocked": True}

    # Check difficulty vs tool version
    difficulty_roll = sys["security"] - tool_version
    if difficulty_roll > 0 and random.random() < 0.2 * difficulty_roll:
        _alert_sysadmin(state)
        return {"success": False, "error": "Force failed -- sys-admin alerted"}

    sys["data1"] = 0  # unlocked
    sys["is_compromised"] = True

    # Forcing always wakes the sys-admin (noisy operation)
    _alert_sysadmin(state)

    return {
        "success": True,
        "action": "force",
        "node_id": node_id,
        "already_unlocked": False,
    }


def _action_move(state, topo, node_id):
    """Navigate to an adjacent node.

    The target node must be accessible: visible, linked via a known link,
    not a locked lock, and (for main servers) all required locks must be
    open.  This mirrors LanMonitor::IsAccessable and ExtendConnection.
    """
    if node_id is None:
        return {"success": False, "error": "move requires a node_id"}

    if node_id < 0 or node_id >= len(topo["systems"]):
        return {"success": False, "error": f"Invalid node_id: {node_id}"}

    accessible, reason = _is_accessible(state, topo, node_id)
    if not accessible:
        return {"success": False, "error": reason}

    # Verify adjacency via a visible link from current connection head
    connection = state["connection"]
    if not connection:
        return {"success": False, "error": "No active connection in LAN"}

    link_head = connection[-1]
    has_link = False
    for lnk in topo["links"]:
        if lnk["visible"] < LINKVISIBLE_AWARE:
            continue
        if ((lnk["from"] == link_head and lnk["to"] == node_id) or
                (lnk["to"] == link_head and lnk["from"] == node_id)):
            has_link = True
            break

    if not has_link:
        return {"success": False, "error": "No visible link to that node from current position"}

    # Extend the connection path
    connection.append(node_id)
    state["current_system"] = node_id
    state["current_selected"] = node_id

    # Ensure the target is at least TYPE visible now
    target = topo["systems"][node_id]
    if target["visible"] < VISIBLE_TYPE:
        target["visible"] = VISIBLE_TYPE

    # Arriving at sensitive systems can wake the sys-admin
    if target["type"] in (LANSYSTEM_MAINSERVER, LANSYSTEM_FILESERVER,
                          LANSYSTEM_LOGSERVER):
        _alert_sysadmin(state)

    return {
        "success": True,
        "action": "move",
        "node_id": node_id,
        "connection": list(connection),
        "current_system": node_id,
    }


def _action_deploy_sensor(state, topo, node_id):
    """Deploy a motion sensor on the current or specified node.

    Motion sensors detect the sys-admin approaching.
    """
    if node_id is None:
        node_id = state["current_system"]

    if node_id < 0 or node_id >= len(topo["systems"]):
        return {"success": False, "error": f"Invalid node_id: {node_id}"}

    if node_id in state["deployed_sensors"]:
        return {"success": False, "error": "Sensor already deployed on this node"}

    sys = topo["systems"][node_id]
    if sys["visible"] < VISIBLE_TYPE:
        return {"success": False, "error": "Node not sufficiently visible"}

    state["deployed_sensors"].append(node_id)

    return {
        "success": True,
        "action": "deploy_sensor",
        "node_id": node_id,
        "deployed_sensors": list(state["deployed_sensors"]),
    }


# ===================================================================
# Accessibility check (mirrors LanMonitor::IsAccessable)
# ===================================================================

def _is_accessible(state, topo, node_id):
    """Check whether the player can navigate to the given node.

    Returns (bool, reason_string).
    """
    sys = topo["systems"][node_id]

    # Must be visible at TYPE level or higher
    if sys["visible"] < VISIBLE_TYPE:
        return False, "Node not visible enough (scan or probe it first)"

    # Must have at least one known link to it (unless it is current)
    if node_id != state["current_system"]:
        has_known_link = False
        for lnk in topo["links"]:
            if lnk["visible"] < LINKVISIBLE_FROMAWARE:
                continue
            if lnk["to"] == node_id or lnk["from"] == node_id:
                has_known_link = True
                break
        if not has_known_link:
            return False, "No known links to this node"

    # Locked locks block passage
    if sys["type"] == LANSYSTEM_LOCK and sys["data1"] == 1:
        return False, "Lock is still locked -- force or spoof to open it"

    # Main servers require all referenced locks to be unlocked
    if sys["type"] == LANSYSTEM_MAINSERVER:
        for data_key in ("data1", "data2", "data3"):
            lock_idx = sys.get(data_key, -1)
            if lock_idx < 0 or lock_idx >= len(topo["systems"]):
                continue
            ref_sys = topo["systems"][lock_idx]
            if ref_sys["type"] == LANSYSTEM_LOCK and ref_sys["data1"] == 1:
                return False, f"Lock {lock_idx} must be opened first"

    # Isolation bridges require both gateway and critical locks open
    if sys["type"] == LANSYSTEM_ISOLATIONBRIDGE:
        for data_key in ("data1", "data2"):
            lock_idx = sys.get(data_key, -1)
            if lock_idx < 0 or lock_idx >= len(topo["systems"]):
                continue
            ref_sys = topo["systems"][lock_idx]
            if ref_sys["type"] == LANSYSTEM_LOCK and ref_sys["data1"] == 1:
                return False, f"Lock {lock_idx} must be opened for the isolation bridge"

    # Subnet restrictions (requires spoofed address)
    if sys.get("valid_subnets"):
        spoof = state["current_spoof"]
        if spoof < 0:
            return False, "This node requires a spoofed subnet address"
        if spoof not in sys["valid_subnets"]:
            return False, "Current spoof address not accepted by this node"

    return True, ""


# ===================================================================
# Sys-admin security
# ===================================================================

def _alert_sysadmin(state):
    """Wake or escalate the sys-admin.

    The sys-admin progresses through states:
    ASLEEP -> CURIOUS -> SEARCHING -> FOUNDYOU
    """
    if state["sysadmin_state"] < SYSADMIN_CURIOUS:
        state["sysadmin_state"] = SYSADMIN_CURIOUS
        # Give the player some ticks before searching begins
        state["sysadmin_ticks_remaining"] = random.randint(40, 80)
        log.debug("Sys-admin awakened to CURIOUS state")


def check_lan_security(session_id, computer_id):
    """Check if player's LAN activity has been detected.

    Called periodically by the game loop.  Advances the sys-admin through
    their detection states.

    Returns
    -------
    dict with keys:
        detected (bool): True if the player has been found.
        sysadmin_state (int): Current sys-admin state.
        warning (bool): True if the sys-admin is actively searching.
        sensor_alert (bool): True if a deployed sensor detected movement.
    """
    key = _state_key(session_id, computer_id)
    if key not in _lan_states:
        return {"detected": False, "sysadmin_state": SYSADMIN_ASLEEP,
                "warning": False, "sensor_alert": False}

    state = _lan_states[key]
    topo = state["topology"]
    sensor_alert = False

    if state["sysadmin_state"] == SYSADMIN_ASLEEP:
        # Check if the player is on a sensitive node
        current = state["current_system"]
        if current >= 0:
            sys = topo["systems"][current]
            if sys["type"] in (LANSYSTEM_MAINSERVER, LANSYSTEM_FILESERVER,
                               LANSYSTEM_LOGSERVER):
                _alert_sysadmin(state)

        return {
            "detected": False,
            "sysadmin_state": SYSADMIN_ASLEEP,
            "warning": False,
            "sensor_alert": False,
        }

    elif state["sysadmin_state"] == SYSADMIN_CURIOUS:
        state["sysadmin_ticks_remaining"] -= 1
        if state["sysadmin_ticks_remaining"] <= 0:
            state["sysadmin_state"] = SYSADMIN_SEARCHING
            # Sys-admin starts tracing from the router (connection[0])
            if state["connection"]:
                state["sysadmin_current_system"] = state["connection"][0]
            state["sysadmin_ticks_remaining"] = random.randint(30, 60)

        return {
            "detected": False,
            "sysadmin_state": SYSADMIN_CURIOUS,
            "warning": True,
            "sensor_alert": False,
        }

    elif state["sysadmin_state"] == SYSADMIN_SEARCHING:
        state["sysadmin_ticks_remaining"] -= 1

        # Check if a motion sensor detects the sys-admin
        if state["sysadmin_current_system"] in state["deployed_sensors"]:
            sensor_alert = True

        if state["sysadmin_current_system"] == state["current_system"]:
            # Found the player
            state["sysadmin_state"] = SYSADMIN_FOUNDYOU
            return {
                "detected": True,
                "sysadmin_state": SYSADMIN_FOUNDYOU,
                "warning": True,
                "sensor_alert": sensor_alert,
            }

        if state["sysadmin_ticks_remaining"] <= 0:
            # Advance the sys-admin along the player's connection path
            sa_node = state["sysadmin_current_system"]
            connection = state["connection"]

            node_index = -1
            for i, n in enumerate(connection):
                if n == sa_node:
                    node_index = i
                    break

            if node_index < 0 or node_index + 1 >= len(connection):
                # Lost trail -- go back to curious
                state["sysadmin_state"] = SYSADMIN_CURIOUS
                state["sysadmin_ticks_remaining"] = random.randint(40, 80)
            else:
                state["sysadmin_current_system"] = connection[node_index + 1]
                state["sysadmin_ticks_remaining"] = random.randint(30, 60)

        return {
            "detected": False,
            "sysadmin_state": SYSADMIN_SEARCHING,
            "warning": True,
            "sensor_alert": sensor_alert,
            "sysadmin_position": state["sysadmin_current_system"],
        }

    elif state["sysadmin_state"] == SYSADMIN_FOUNDYOU:
        return {
            "detected": True,
            "sysadmin_state": SYSADMIN_FOUNDYOU,
            "warning": True,
            "sensor_alert": False,
        }

    return {
        "detected": False,
        "sysadmin_state": state["sysadmin_state"],
        "warning": False,
        "sensor_alert": False,
    }


# ===================================================================
# Connection management helpers
# ===================================================================

def retract_connection(session_id, computer_id):
    """Remove the last node from the player's LAN connection path.

    Returns the updated connection list.
    """
    state = _ensure_state(session_id, computer_id)
    connection = state["connection"]

    if len(connection) > 1:
        connection.pop()
        state["current_system"] = connection[-1]
        state["current_selected"] = connection[-1]
    return {
        "connection": list(connection),
        "current_system": state["current_system"],
    }


def set_selected(session_id, computer_id, node_id):
    """Set the currently selected (highlighted) node without moving."""
    state = _ensure_state(session_id, computer_id)
    if node_id < 0 or node_id >= len(state["topology"]["systems"]):
        return {"success": False, "error": f"Invalid node_id: {node_id}"}
    state["current_selected"] = node_id
    return {"success": True, "current_selected": node_id}


# ===================================================================
# Cleanup
# ===================================================================

def cleanup_session(session_id):
    """Remove all LAN states for a given session (e.g. on disconnect)."""
    keys_to_remove = [k for k in _lan_states if k[0] == str(session_id)]
    for k in keys_to_remove:
        del _lan_states[k]
