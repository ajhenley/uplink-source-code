"""Game constants: well-known IPs, pools, trace speeds, balance."""

# Well-known IPs
IP_UPLINK_PAS = "234.773.0.666"
IP_UPLINK_TEST = "128.185.0.4"
IP_INTERNIC = "458.615.48.651"
IP_CRIMINAL_DB = "176.333.12.100"
IP_SOCIAL_SECURITY = "187.242.55.203"
IP_ACADEMIC_DB = "201.618.73.312"

# Starting balance (credits)
STARTING_BALANCE = 3000

# Trace speeds (seconds per link, -1 = no trace)
TRACE_NONE = -1
TRACE_SLOW = 30
TRACE_MEDIUM = 15
TRACE_FAST = 8
TRACE_INSTANT = 3

# Trace actions
ACTION_DISCONNECT = "DISCONNECT"
ACTION_DISCONNECT_FINE = "DISCONNECT,FINE"
ACTION_DISCONNECT_FINE_ARREST = "DISCONNECT,FINE,ARREST"

# Company name pools
COMPANY_NAMES = [
    "ARC Technologies", "Protovision Networks", "OmniCorp Systems",
    "DataVault Inc", "NexGen Computing", "CyberDyne Industries",
    "Sentinel Security", "Meridian Group", "Axiom Research",
    "Pinnacle Software", "Quantum Solutions", "Helix Dynamics",
    "Vanguard Analytics", "Echo Systems", "Paragon Digital",
    "Apex Microsystems", "Cerberus Corp", "Orion Dataworks",
    "Nebula Technologies", "Zenith Computing",
]

# Company types
TYPE_COMMERCIAL = "COMMERCIAL"
TYPE_FINANCIAL = "FINANCIAL"
TYPE_GOVERNMENT = "GOVERNMENT"
TYPE_ACADEMIC = "ACADEMIC"

# Computer types
COMP_PUBLIC_ACCESS = "PUBLICACCESSSERVER"
COMP_INTERNAL = "INTERNALSERVICESMACHINE"
COMP_MAINFRAME = "CENTRALMAINFRAME"
COMP_GATEWAY = "GATEWAY"

# Screen types
SCREEN_MESSAGE = "MESSAGE"
SCREEN_PASSWORD = "PASSWORD"
SCREEN_MENU = "MENU"
SCREEN_FILESERVER = "FILESERVER"
SCREEN_LOGSCREEN = "LOGSCREEN"
SCREEN_LINKS = "LINKS"

# Security types
SEC_PROXY = "PROXY"
SEC_FIREWALL = "FIREWALL"
SEC_MONITOR = "MONITOR"

# Password pools
PASSWORD_POOL = [
    "rosebud", "password", "letmein", "joshua", "god",
    "love", "sex", "secret", "master", "hello",
    "charlie", "dragon", "qwerty", "monkey", "shadow",
    "matrix", "access", "admin", "root", "guest",
    "portal", "alpine", "thunder", "falcon", "knight",
    "wizard", "hunter", "phoenix", "diamond", "crystal",
]

# File name pools
FILE_NAMES = [
    "accounts.dat", "payroll.dat", "staff_records.dat",
    "project_alpha.dat", "budget_2026.dat", "passwords.dat",
    "security_audit.dat", "memo_ceo.txt", "quarterly_report.dat",
    "client_list.dat", "server_config.dat", "backup_log.txt",
    "classified.dat", "employee_db.dat", "network_map.dat",
]

# Screen types (new)
SCREEN_BBS = "BBS"
SCREEN_SHOP = "SHOP"
SCREEN_HWSHOP = "HWSHOP"

# Game speed labels
SPEED_LABELS = {0: "Paused", 1: "Normal", 3: "Fast", 8: "MegaFast"}
VALID_SPEEDS = [0, 1, 3, 8]

# Mission types
MISSION_STEAL_FILE = "STEAL_FILE"
MISSION_DESTROY_FILE = "DESTROY_FILE"

# Mission statuses
MISSION_AVAILABLE = "AVAILABLE"
MISSION_ACCEPTED = "ACCEPTED"
MISSION_COMPLETED = "COMPLETED"
MISSION_FAILED = "FAILED"
MISSION_EXPIRED = "EXPIRED"

# Tool types (matching software names)
TOOL_PASSWORD_BREAKER = "PASSWORD_BREAKER"
TOOL_FILE_COPIER = "FILE_COPIER"
TOOL_FILE_DELETER = "FILE_DELETER"
TOOL_LOG_DELETER = "LOG_DELETER"
TOOL_TRACE_TRACKER = "TRACE_TRACKER"
TOOL_PROXY_DISABLE = "PROXY_DISABLE"
TOOL_FIREWALL_DISABLE = "FIREWALL_DISABLE"
TOOL_MONITOR_BYPASS = "MONITOR_BYPASS"
TOOL_DECRYPTER = "DECRYPTER"

# Tool tick rates (at 5Hz, speed x1)
TOOL_TICKS = {
    "PASSWORD_BREAKER": 45,   # ticks per password char
    "FILE_COPIER": 45,        # ticks per GQ file size
    "FILE_DELETER": 9,        # ticks per GQ file size
    "LOG_DELETER": 60,        # flat ticks
    "TRACE_TRACKER": 0,       # passive (shows trace %)
    "PROXY_DISABLE": 30,      # ticks per security level
    "FIREWALL_DISABLE": 35,   # ticks per security level
    "MONITOR_BYPASS": 25,     # ticks per security level
    "DECRYPTER": 20,          # ticks per GQ file size
}

# Tool statuses
TOOL_RUNNING = "RUNNING"
TOOL_COMPLETED = "COMPLETED"
TOOL_CANCELLED = "CANCELLED"

# Starting software (free with gateway)
STARTING_SOFTWARE = [
    ("Trace Tracker", "TRACE_TRACKER", "1.0", 1, 0),
]

# Software shop catalog: (name, type, version, size, cost)
SOFTWARE_CATALOG = [
    ("Password Breaker", "PASSWORD_BREAKER", "1.0", 2, 1500),
    ("File Copier", "FILE_COPIER", "1.0", 1, 100),
    ("File Deleter", "FILE_DELETER", "1.0", 1, 100),
    ("Log Deleter", "LOG_DELETER", "1.0", 1, 500),
    ("Trace Tracker", "TRACE_TRACKER", "1.0", 1, 300),
    ("Proxy Disable", "PROXY_DISABLE", "1.0", 2, 2000),
    ("Firewall Disable", "FIREWALL_DISABLE", "1.0", 2, 2500),
    ("Monitor Bypass", "MONITOR_BYPASS", "1.0", 2, 1800),
    ("Decrypter", "DECRYPTER", "1.0", 1, 1200),
]

# Mission payments (base, variance fraction)
MISSION_PAYMENTS = {
    "STEAL_FILE": (900, 0.3),
    "DESTROY_FILE": (800, 0.3),
}

# Uplink rating names
RATING_NAMES = {
    0: "Unregistered", 1: "Registered", 2: "Beginner",
    6: "Novice", 15: "Confident", 35: "Intermediate",
    60: "Skilled", 90: "Experienced", 125: "Knowledgeable",
}

# Rating gain per mission type
RATING_GAIN = {
    "STEAL_FILE": 3,
    "DESTROY_FILE": 3,
}

# Tool name aliases (user-facing name → tool type)
TOOL_ALIASES = {
    "password_breaker": "PASSWORD_BREAKER",
    "file_copier": "FILE_COPIER",
    "file_deleter": "FILE_DELETER",
    "log_deleter": "LOG_DELETER",
    "trace_tracker": "TRACE_TRACKER",
    "proxy_disable": "PROXY_DISABLE",
    "firewall_disable": "FIREWALL_DISABLE",
    "monitor_bypass": "MONITOR_BYPASS",
    "decrypter": "DECRYPTER",
}


# --- Hardware types ---
HW_CPU = "CPU"
HW_MODEM = "MODEM"
HW_MEMORY = "MEMORY"

# Starting hardware (type, name, value, cost)
STARTING_HARDWARE = [
    ("CPU",    "CPU (60 GHz)",    60, 0),
    ("MODEM",  "Modem (1 GQ/s)",   1, 0),
    ("MEMORY", "Memory (24 GQ)",  24, 0),
]

# Hardware shop catalog: (name, hw_type, value, cost)
HARDWARE_CATALOG = [
    ("CPU (60 GHz)",         "CPU",     60,   1000),
    ("CPU (80 GHz)",         "CPU",     80,   1300),
    ("CPU (100 GHz)",        "CPU",    100,   3000),
    ("CPU (120 GHz)",        "CPU",    120,   5000),
    ("CPU (150 GHz)",        "CPU",    150,   8000),
    ("CPU (200 GHz Turbo)",  "CPU",    200,  12000),
    ("Modem (1 GQ/s)",      "MODEM",    1,   1000),
    ("Modem (2 GQ/s)",      "MODEM",    2,   2000),
    ("Modem (4 GQ/s)",      "MODEM",    4,   4000),
    ("Modem (8 GQ/s)",      "MODEM",    8,   8000),
    ("Memory (8 GQ)",       "MEMORY",   8,   3000),
    ("Memory (16 GQ)",      "MEMORY",  16,   5500),
    ("Memory (24 GQ)",      "MEMORY",  24,   8000),
    ("Memory (32 GQ)",      "MEMORY",  32,  11000),
]

# CPU/modem baselines for scaling
CPU_BASELINE = 60       # tools run at 1.0x speed at 60 GHz
MODEM_BASELINE = 1      # file copy at 1.0x speed at 1 GQ/s

# Bounce routing
BOUNCE_DELAY_PER_HOP = 1.5   # each hop multiplies trace time by 1.5x
MAX_BOUNCE_HOPS = 8

# Monitor trace factor: active monitor speeds trace by 1 / (1 + level * factor)
MONITOR_TRACE_FACTOR = 0.3


# Admin forensics
ADMIN_REVIEW_INTERVAL = 300          # ticks between reviews (~60s at 1x)
CRIMINAL_THRESHOLD_GAMEOVER = 10     # arrest at this level

# Fine amounts by severity
FINE_LOW = 0           # warning only (basic traced systems)
FINE_MEDIUM = 300      # company systems (trace_action has FINE)
FINE_HIGH = 750        # government systems (trace_action has ARREST)

# Criminal record level names
CRIMINAL_LEVEL_NAMES = {
    0: "Clean", 1: "Caution", 3: "Flagged", 6: "Wanted", 10: "Arrested",
}


def get_rating_name(rating):
    """Get the rating name for a given numeric rating."""
    name = "Unregistered"
    for threshold in sorted(RATING_NAMES.keys()):
        if rating >= threshold:
            name = RATING_NAMES[threshold]
    return name


def get_criminal_level_name(record):
    """Get the criminal record level name for a given offense count."""
    name = "Clean"
    for threshold in sorted(CRIMINAL_LEVEL_NAMES.keys()):
        if record >= threshold:
            name = CRIMINAL_LEVEL_NAMES[threshold]
    return name
