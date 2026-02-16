"""Game constants: well-known IPs, pools, trace speeds, balance."""

# Well-known IPs
IP_UPLINK_PAS = "234.773.0.666"
IP_UPLINK_TEST = "128.185.0.4"
IP_INTERNIC = "458.615.48.651"
IP_CRIMINAL_DB = "176.333.12.100"
IP_SOCIAL_SECURITY = "187.242.55.203"
IP_ACADEMIC_DB = "201.618.73.312"
IP_UPLINK_BANK = "491.220.38.901"
IP_NEWS_NETWORK = "301.444.12.876"
IP_STOCK_EXCHANGE = "310.555.20.100"

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
    "Protovision Networks", "OmniCorp Systems",
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
COMP_BANK = "BANKCOMPUTER"

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

# Password rotation pool (used after admin review)
PASSWORD_ROTATION_POOL = [
    "br34ch3d", "s3cur1ty", "r0t4t3d", "l0ckd0wn", "h4rd3n3d",
    "n3wp4ss", "ch4ng3d", "upd4t3d", "r3s3t01", "f1r3w4ll",
    "c0mpl3x", "str0ng3r", "d3f3ns3", "4l3rt3d", "m0n1t0r",
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
SCREEN_BANKACCOUNTS = "BANKACCOUNTS"
SCREEN_BANKTRANSFER = "BANKTRANSFER"
SCREEN_NEWS = "NEWS"
SCREEN_RANKINGS = "RANKINGS"
SCREEN_LAN = "LAN"
SCREEN_VOICEPRINT = "VOICEPRINT"
SCREEN_STOCKMARKET = "STOCKMARKET"
SCREEN_HIGHSECURITY = "HIGHSECURITY"
SCREEN_CONSOLE = "CONSOLE"

# Game speed labels
SPEED_LABELS = {0: "Paused", 1: "Normal", 3: "Fast", 8: "MegaFast"}
VALID_SPEEDS = [0, 1, 3, 8]

# Mission types
MISSION_STEAL_FILE = "STEAL_FILE"
MISSION_DESTROY_FILE = "DESTROY_FILE"
MISSION_STEAL_MONEY = "STEAL_MONEY"
MISSION_CHANGE_ACADEMIC = "CHANGE_ACADEMIC"
MISSION_CHANGE_CRIMINAL = "CHANGE_CRIMINAL"
MISSION_LAN_FILE = "LAN_FILE"
MISSION_LAN_DESTROY = "LAN_DESTROY"
MISSION_FRAME_USER = "FRAME_USER"
MISSION_TRACE_USER = "TRACE_USER"
MISSION_REMOVE_COMPUTER = "REMOVE_COMPUTER"
MISSION_CHANGE_SOCIAL = "CHANGE_SOCIAL"
MISSION_DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"
MISSION_STOCK_FRAUD = "STOCK_FRAUD"
MISSION_PAY_FINE = "PAY_FINE"

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
TOOL_BYPASSER = "BYPASSER"
TOOL_IP_PROBE = "IP_PROBE"
TOOL_LOG_MODIFIER = "LOG_MODIFIER"
TOOL_DICTIONARY_HACKER = "DICTIONARY_HACKER"
TOOL_VOICE_ANALYSER = "VOICE_ANALYSER"
TOOL_LAN_SCAN = "LAN_SCAN"
TOOL_LAN_PROBE = "LAN_PROBE"
TOOL_LAN_FORCE = "LAN_FORCE"
TOOL_LAN_SPOOF = "LAN_SPOOF"

# Version speed scaling
VERSION_SPEED_STEP = 0.5
BYPASSER_SPEED_PENALTY = 1.5

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
    "BYPASSER": 40,           # ticks per security level (before 1.5x penalty)
    "IP_PROBE": 80,           # flat ticks
    "LOG_MODIFIER": 40,       # flat ticks (faster than LOG_DELETER)
    "DICTIONARY_HACKER": 25,  # per-character (faster than PASSWORD_BREAKER's 45)
    "VOICE_ANALYSER": 50,     # flat rate, scaled by version/CPU
    "LAN_SCAN": 40,           # flat — discovers all LAN nodes
    "LAN_PROBE": 30,          # flat — deep scan of a specific node
    "LAN_FORCE": 35,          # per security level — brute force a LOCK node
    "LAN_SPOOF": 45,          # flat — activates sysadmin cloaking
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
# v1.0 = base price/size; v2.0 ~2x cost, +1 GQ; v3.0 ~3.5x; v4.0 ~5x, +1 GQ; v5.0 ~8x
SOFTWARE_CATALOG = [
    # Password Breaker (base: 2 GQ, 1500c)
    ("Password Breaker", "PASSWORD_BREAKER", "1.0", 2, 1500),
    ("Password Breaker", "PASSWORD_BREAKER", "2.0", 3, 3000),
    ("Password Breaker", "PASSWORD_BREAKER", "3.0", 3, 5200),
    ("Password Breaker", "PASSWORD_BREAKER", "4.0", 4, 7500),
    ("Password Breaker", "PASSWORD_BREAKER", "5.0", 4, 12000),
    # File Copier (base: 1 GQ, 100c)
    ("File Copier", "FILE_COPIER", "1.0", 1, 100),
    ("File Copier", "FILE_COPIER", "2.0", 2, 200),
    ("File Copier", "FILE_COPIER", "3.0", 2, 350),
    ("File Copier", "FILE_COPIER", "4.0", 3, 500),
    ("File Copier", "FILE_COPIER", "5.0", 3, 800),
    # File Deleter (base: 1 GQ, 100c)
    ("File Deleter", "FILE_DELETER", "1.0", 1, 100),
    ("File Deleter", "FILE_DELETER", "2.0", 2, 200),
    ("File Deleter", "FILE_DELETER", "3.0", 2, 350),
    ("File Deleter", "FILE_DELETER", "4.0", 3, 500),
    ("File Deleter", "FILE_DELETER", "5.0", 3, 800),
    # Log Deleter (base: 1 GQ, 500c)
    ("Log Deleter", "LOG_DELETER", "1.0", 1, 500),
    ("Log Deleter", "LOG_DELETER", "2.0", 2, 1000),
    ("Log Deleter", "LOG_DELETER", "3.0", 2, 1750),
    ("Log Deleter", "LOG_DELETER", "4.0", 3, 2500),
    ("Log Deleter", "LOG_DELETER", "5.0", 3, 4000),
    # Trace Tracker — v1.0 only (passive tool, no speed benefit)
    ("Trace Tracker", "TRACE_TRACKER", "1.0", 1, 300),
    # Proxy Disable (base: 2 GQ, 2000c)
    ("Proxy Disable", "PROXY_DISABLE", "1.0", 2, 2000),
    ("Proxy Disable", "PROXY_DISABLE", "2.0", 3, 4000),
    ("Proxy Disable", "PROXY_DISABLE", "3.0", 3, 7000),
    ("Proxy Disable", "PROXY_DISABLE", "4.0", 4, 10000),
    ("Proxy Disable", "PROXY_DISABLE", "5.0", 4, 16000),
    # Firewall Disable (base: 2 GQ, 2500c)
    ("Firewall Disable", "FIREWALL_DISABLE", "1.0", 2, 2500),
    ("Firewall Disable", "FIREWALL_DISABLE", "2.0", 3, 5000),
    ("Firewall Disable", "FIREWALL_DISABLE", "3.0", 3, 8700),
    ("Firewall Disable", "FIREWALL_DISABLE", "4.0", 4, 12500),
    ("Firewall Disable", "FIREWALL_DISABLE", "5.0", 4, 20000),
    # Monitor Bypass (base: 2 GQ, 1800c)
    ("Monitor Bypass", "MONITOR_BYPASS", "1.0", 2, 1800),
    ("Monitor Bypass", "MONITOR_BYPASS", "2.0", 3, 3600),
    ("Monitor Bypass", "MONITOR_BYPASS", "3.0", 3, 6300),
    ("Monitor Bypass", "MONITOR_BYPASS", "4.0", 4, 9000),
    ("Monitor Bypass", "MONITOR_BYPASS", "5.0", 4, 14400),
    # Decrypter (base: 1 GQ, 1200c)
    ("Decrypter", "DECRYPTER", "1.0", 1, 1200),
    ("Decrypter", "DECRYPTER", "2.0", 2, 2400),
    ("Decrypter", "DECRYPTER", "3.0", 2, 4200),
    ("Decrypter", "DECRYPTER", "4.0", 3, 6000),
    ("Decrypter", "DECRYPTER", "5.0", 3, 9600),
    # Bypasser — universal security bypass (base: 2 GQ, 3000c)
    ("Bypasser", "BYPASSER", "1.0", 2, 3000),
    ("Bypasser", "BYPASSER", "2.0", 3, 6000),
    ("Bypasser", "BYPASSER", "3.0", 3, 10500),
    ("Bypasser", "BYPASSER", "4.0", 4, 15000),
    ("Bypasser", "BYPASSER", "5.0", 4, 24000),
    # IP Probe — network reconnaissance (base: 1 GQ, 800c)
    ("IP Probe", "IP_PROBE", "1.0", 1, 800),
    ("IP Probe", "IP_PROBE", "2.0", 2, 1600),
    ("IP Probe", "IP_PROBE", "3.0", 2, 2800),
    ("IP Probe", "IP_PROBE", "4.0", 3, 4000),
    ("IP Probe", "IP_PROBE", "5.0", 3, 6400),
    # Log Modifier — stealth log editing (base: 1 GQ, 600c)
    ("Log Modifier", "LOG_MODIFIER", "1.0", 1, 600),
    ("Log Modifier", "LOG_MODIFIER", "2.0", 2, 1200),
    ("Log Modifier", "LOG_MODIFIER", "3.0", 2, 2100),
    ("Log Modifier", "LOG_MODIFIER", "4.0", 3, 3000),
    ("Log Modifier", "LOG_MODIFIER", "5.0", 3, 4800),
    # Dictionary Hacker — cheap password cracker, only works on weak passwords (base: 1 GQ, 500c)
    ("Dictionary Hacker", "DICTIONARY_HACKER", "1.0", 1, 500),
    ("Dictionary Hacker", "DICTIONARY_HACKER", "2.0", 1, 1000),
    ("Dictionary Hacker", "DICTIONARY_HACKER", "3.0", 2, 1800),
    ("Dictionary Hacker", "DICTIONARY_HACKER", "4.0", 2, 2500),
    ("Dictionary Hacker", "DICTIONARY_HACKER", "5.0", 3, 3600),
    # Voice Analyser — records voiceprints to bypass voice authentication (base: 1 GQ, 800c)
    ("Voice Analyser", "VOICE_ANALYSER", "1.0", 1, 800),
    ("Voice Analyser", "VOICE_ANALYSER", "2.0", 1, 1600),
    ("Voice Analyser", "VOICE_ANALYSER", "3.0", 2, 2800),
    ("Voice Analyser", "VOICE_ANALYSER", "4.0", 2, 4000),
    ("Voice Analyser", "VOICE_ANALYSER", "5.0", 3, 5600),
    # LAN Scan — discover all LAN nodes at once (base: 1 GQ, 600c)
    ("LAN Scan", "LAN_SCAN", "1.0", 1, 600),
    ("LAN Scan", "LAN_SCAN", "2.0", 1, 1200),
    ("LAN Scan", "LAN_SCAN", "3.0", 2, 2100),
    ("LAN Scan", "LAN_SCAN", "4.0", 2, 3000),
    ("LAN Scan", "LAN_SCAN", "5.0", 3, 4800),
    # LAN Probe — deep scan a specific LAN node + discover connections (base: 1 GQ, 500c)
    ("LAN Probe", "LAN_PROBE", "1.0", 1, 500),
    ("LAN Probe", "LAN_PROBE", "2.0", 1, 1000),
    ("LAN Probe", "LAN_PROBE", "3.0", 2, 1750),
    ("LAN Probe", "LAN_PROBE", "4.0", 2, 2500),
    ("LAN Probe", "LAN_PROBE", "5.0", 3, 4000),
    # LAN Force — brute force a LOCK node open, alerts sysadmin (base: 2 GQ, 1800c)
    ("LAN Force", "LAN_FORCE", "1.0", 2, 1800),
    ("LAN Force", "LAN_FORCE", "2.0", 2, 3600),
    ("LAN Force", "LAN_FORCE", "3.0", 3, 6300),
    ("LAN Force", "LAN_FORCE", "4.0", 3, 9000),
    ("LAN Force", "LAN_FORCE", "5.0", 4, 14400),
    # LAN Spoof — hide from sysadmin while in LAN (base: 2 GQ, 2000c)
    ("LAN Spoof", "LAN_SPOOF", "1.0", 2, 2000),
    ("LAN Spoof", "LAN_SPOOF", "2.0", 2, 4000),
    ("LAN Spoof", "LAN_SPOOF", "3.0", 3, 7000),
    ("LAN Spoof", "LAN_SPOOF", "4.0", 3, 10000),
    ("LAN Spoof", "LAN_SPOOF", "5.0", 4, 16000),
]

# Mission payments (base, variance fraction)
MISSION_PAYMENTS = {
    "STEAL_FILE": (900, 0.3),
    "DESTROY_FILE": (800, 0.3),
    "STEAL_MONEY": (3000, 0.4),
    "CHANGE_ACADEMIC": (1500, 0.3),
    "CHANGE_CRIMINAL": (2500, 0.3),
    "LAN_FILE": (2500, 0.3),
    "LAN_DESTROY": (2200, 0.3),
    "PLOT_STEAL": (6000, 0.0),
    "PLOT_DESTROY": (8000, 0.0),
    "PLOT_DEPLOY": (12000, 0.0),
    "FRAME_USER": (3500, 0.3),
    "TRACE_USER": (2000, 0.3),
    "REMOVE_COMPUTER": (5000, 0.3),
    "CHANGE_SOCIAL": (2500, 0.3),
    "DENIAL_OF_SERVICE": (4000, 0.3),
    "STOCK_FRAUD": (5000, 0.3),
    "PAY_FINE": (0, 0),
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
    "STEAL_MONEY": 8,
    "CHANGE_ACADEMIC": 5,
    "CHANGE_CRIMINAL": 6,
    "LAN_FILE": 7,
    "LAN_DESTROY": 7,
    "PLOT_STEAL": 5,
    "PLOT_DESTROY": 5,
    "PLOT_DEPLOY": 10,
    "FRAME_USER": 7,
    "TRACE_USER": 5,
    "REMOVE_COMPUTER": 10,
    "CHANGE_SOCIAL": 5,
    "DENIAL_OF_SERVICE": 7,
    "STOCK_FRAUD": 8,
    "PAY_FINE": 0,
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
    "bypasser": "BYPASSER",
    "ip_probe": "IP_PROBE",
    "log_modifier": "LOG_MODIFIER",
    "dictionary_hacker": "DICTIONARY_HACKER",
    "voice_analyser": "VOICE_ANALYSER",
    "lan_scan": "LAN_SCAN",
    "lan_probe": "LAN_PROBE",
    "lan_force": "LAN_FORCE",
    "lan_spoof": "LAN_SPOOF",
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
    ("Memory (48 GQ)",      "MEMORY",  48,  18000),
    ("Memory (64 GQ)",      "MEMORY",  64,  30000),
]

# Gateway model names by memory capacity
GATEWAY_MODELS = {
    8: "Micro", 16: "Compact", 24: "Basic",
    32: "Standard", 48: "Advanced", 64: "Elite",
}

# Nuke command cost
NUKE_COST = 1000

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

# Company retaliation
RETALIATION_TRACE_BOOST = 0.15
RETALIATION_TRACE_MIN = 5
RETALIATION_COUNTER_CHANCE = 0.20
RETALIATION_COUNTER_FINE = 1000


# NPC name pool (for bank accounts and records)
NPC_NAMES = [
    "John Smith", "Sarah Connor", "David Chen", "Maria Garcia",
    "James Wilson", "Emily Taylor", "Robert Brown", "Lisa Anderson",
    "Michael Davis", "Jennifer Thomas", "William Jackson", "Patricia White",
    "Richard Harris", "Elizabeth Martin", "Charles Thompson", "Margaret Robinson",
    "Thomas Clark", "Susan Lewis", "Christopher Lee", "Karen Walker",
]

# Bank account balance ranges
BANK_BALANCE_MIN = 5000
BANK_BALANCE_MAX = 500000

# Academic record constants
ACADEMIC_SUBJECTS = [
    "Computer Science", "Mathematics", "Physics", "Engineering",
    "Chemistry", "Biology", "Economics", "Business Studies",
    "Law", "Medicine",
]
ACADEMIC_CLASSES = ["1st", "2:1", "2:2", "3rd", "None"]

# Criminal record constants
CRIMINAL_CONVICTIONS = [
    "Robbery", "High tech fraud", "Tax evasion",
    "Embezzlement", "Forgery", "None",
]

SS_STATUSES = ["Active", "Suspended", "Deceased", "Revoked", "Flagged"]
SS_ADDRESSES = [
    "42 Oak Lane, Boston",
    "118 Pine St, Chicago",
    "7 Maple Ave, Denver",
    "305 Elm Rd, Seattle",
    "91 Cedar Blvd, Miami",
    "200 Birch Dr, Portland",
    "55 Spruce Ct, Atlanta",
    "163 Walnut Way, Dallas",
    "22 Ash Pl, Phoenix",
    "480 Willow Ln, New York",
]


# News system
NEWS_GENERATION_INTERVAL = 800   # ticks between random news articles
MAX_NEWS_ARTICLES = 30           # trim oldest beyond this
MAX_CONNECTION_HISTORY = 20      # max connection history entries
SECURITY_MAX_LEVEL = 5           # cap for security system upgrades

# Random news headline templates ({company} is replaced)
NEWS_RANDOM_EVENTS = [
    "{company} announces record quarterly profits",
    "{company} hit by internal data leak",
    "{company} unveils new security partnership",
    "Stock prices surge for {company} after merger talks",
    "{company} lays off 200 workers in restructuring",
    "CEO of {company} resigns amid scandal",
    "{company} wins government defense contract",
    "Hackers target {company} in coordinated attack",
    "{company} opens new data center in Singapore",
    "Whistleblower exposes {company} accounting fraud",
    "{company} acquires rival firm for $2.4 billion",
    "Fire at {company} headquarters causes evacuations",
    "{company} reports critical software vulnerability",
    "New {company} product launch exceeds expectations",
    "{company} faces class action lawsuit from investors",
]

# NPC agent names for rankings
NPC_AGENT_NAMES = [
    "Acid Burn", "Crash Override", "Cereal Killer", "Lord Nikon",
    "The Phantom", "Zero Cool", "Razor", "Blade Runner",
    "Ghost", "Neo", "Morpheus", "Trinity",
    "Darkstar", "Binary", "Cipher",
]

# NPC agent simulation
NPC_MISSION_INTERVAL = 400
NPC_MISSION_CHANCE = 0.35
NPC_CAUGHT_CHANCE = 0.08
NPC_CAUGHT_RATING_PENALTY = 15
NPC_RATING_GAIN_BASE = 3
NPC_RATING_GAIN_VARIANCE = 4

# Rating tier thresholds and unlock hints
RATING_UNLOCK_HINTS = {
    1: "You are now a Registered agent. Basic missions are available on the BBS.",
    2: "Beginner tier reached. You can now take on file-based contracts.",
    6: "Novice rating achieved. Academic record missions are now available.",
    15: "Confident tier! More complex missions await. Consider upgrading your hardware.",
    35: "Intermediate agent. You have access to high-value contracts.",
    60: "Skilled tier reached. Government systems are within your reach.",
    90: "Experienced agent. Few systems can withstand your expertise.",
    125: "Knowledgeable — the highest rating tier. You are elite.",
}


# --- LAN system constants ---
LAN_ROUTER = "ROUTER"
LAN_TERMINAL = "TERMINAL"
LAN_LOCK = "LOCK"
LAN_FILE_SERVER = "FILE_SERVER"
LAN_MAINFRAME = "MAINFRAME"
LAN_LOG_SERVER = "LOG_SERVER"

LAN_MIN_COMPANY_SIZE = 8
LAN_MAX_COMPANIES = 4

LAN_FILE_NAMES = [
    "classified_ops.dat", "research_alpha.dat", "prototype_specs.dat",
    "merger_plans.dat", "defense_contract.dat", "genome_data.dat",
    "encryption_keys.dat", "satellite_telemetry.dat", "agent_roster.dat",
    "financial_audit.dat", "patent_portfolio.dat", "supply_chain.dat",
    "internal_memo.dat", "project_nexus.dat", "board_minutes.dat",
    "security_blueprint.dat", "trade_secrets.dat", "r_and_d_report.dat",
]

LAN_NODE_CHARS = {
    LAN_ROUTER: "R",
    LAN_TERMINAL: "T",
    LAN_LOCK: "L",
    LAN_FILE_SERVER: "F",
    LAN_MAINFRAME: "M",
    LAN_LOG_SERVER: "S",
}

# SysAdmin AI states
SYSADMIN_ASLEEP = 0
SYSADMIN_CURIOUS = 1
SYSADMIN_SEARCHING = 2
SYSADMIN_FOUNDYOU = 3

# Nodes that wake the sysadmin when the player interacts
SYSADMIN_SENSITIVE_NODES = {LAN_FILE_SERVER, LAN_MAINFRAME, LAN_LOG_SERVER}

# Timing (in game ticks at 5Hz)
SYSADMIN_CURIOUS_TICKS = 50      # ~10s at 1x before searching
SYSADMIN_SEARCH_STEP_TICKS = 25  # ~5s per node step
SYSADMIN_TICK_INTERVAL = 5       # check every 5 ticks


# --- Stock market ---
STOCK_TICK_INTERVAL = 100        # ticks between price updates (~20s at 1x)
STOCK_BASE_PRICE = 100           # starting share price for size-1 company
STOCK_PRICE_PER_SIZE = 50        # additional price per company size
STOCK_VOLATILITY = 0.04          # max % random walk per tick (4%)
STOCK_SENTIMENT_DECAY = 0.7      # sentiment multiplied by this each tick
STOCK_BREACH_SENTIMENT = -3      # sentiment hit when company is breached
STOCK_NEWS_POSITIVE_SENTIMENT = 1  # positive news sentiment boost
STOCK_NEWS_NEGATIVE_SENTIMENT = -1  # negative news sentiment hit

# --- Tutorial ---
TUTORIAL_STEPS = 7  # total tutorial steps (0-6)
TUTORIAL_CHECK_INTERVAL = 50  # ticks between tutorial progress checks

# --- Fines ---
FINE_PER_POINT = 500  # credits per criminal record point removed
FINE_MIN_RECORD = 3   # minimum criminal record to generate PAY_FINE
FINE_POINTS_REMOVED = 2  # criminal record points removed on completion


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


def get_version_speed_multiplier(version_str):
    """Get the speed multiplier for a software version string.

    Formula: 1.0 + (version - 1) * VERSION_SPEED_STEP
    v1.0 = 1.0x, v2.0 = 1.5x, v3.0 = 2.0x, v4.0 = 2.5x, v5.0 = 3.0x
    """
    try:
        version = float(version_str)
    except (TypeError, ValueError):
        return 1.0
    return 1.0 + (version - 1.0) * VERSION_SPEED_STEP


# --- Plot system (Revelation) ---
# Company IPs
IP_ARC = "327.868.12.450"
IP_ARUNMOR = "194.255.38.901"

# Faction identifiers
FACTION_NONE = 0
FACTION_ARUNMOR = 1
FACTION_ARC = -1

# Plot acts and scenes
PLOT_ACT_NONE = 0      # Plot hasn't started
PLOT_ACT_1 = 1          # Introduction — both factions reach out
PLOT_ACT_2 = 2          # Bidding war — escalating offers
PLOT_ACT_3 = 3          # Player chooses a side
PLOT_ACT_4 = 4          # (Phase 14) Special missions
PLOT_ACT_5 = 5          # (Phase 14) Virus/counter-virus deployment
PLOT_ACT_6 = 6          # (Phase 14) Endgame

# Scene identifiers within each act
# Act 1 scenes
SCENE_1_INTRO = "1_intro"           # Uplink sends "strange events" email
SCENE_1_ARC_CONTACT = "1_arc"       # ARC contacts player
SCENE_1_ARUNMOR_CONTACT = "1_arun"  # Arunmor contacts player
# Act 2 scenes
SCENE_2_ARC_OFFER = "2_arc_offer"     # ARC: "join us, test Revelation"
SCENE_2_ARUN_OFFER = "2_arun_offer"   # Arunmor: "help us stop the virus"
SCENE_2_ARC_SWEETEN = "2_arc_sweet"   # ARC raises offer
SCENE_2_ARUN_SWEETEN = "2_arun_sweet" # Arunmor raises offer
SCENE_2_NEWS_VIRUS = "2_news_virus"   # News: systems going offline
# Act 3 scenes
SCENE_3_CHOICE_PROMPT = "3_choice"     # Both factions send final emails
SCENE_3_PLAYER_CHOSE = "3_chose"       # Player replied → loyalty locked

# Plot timing (in game ticks)
PLOT_START_TICK = 800           # ~2.5 min at 1x (after a few missions)
PLOT_SCENE_INTERVAL = 400       # ~80s between scenes
PLOT_ACT2_START = 1600          # ~5 min at 1x
PLOT_ACT3_START = 2800          # ~9 min at 1x

# Plot email addresses
PLOT_EMAIL_ARC = "admin@arc.net"
PLOT_EMAIL_ARUNMOR = "research@arunmor.com"
PLOT_EMAIL_UPLINK_INTERNAL = "internal@intl.uplink.co.uk"

# Plot mission payments
PLOT_PAYMENT_ARC = 8000
PLOT_PAYMENT_ARUNMOR = 7000

# Revelation virus version tracking
REVELATION_INITIAL_VERSION = "1.0"
FAITH_INITIAL_VERSION = "1.0"

# Act 4 scenes
SCENE_4_MISSION_1 = "4_mission1"       # First faction mission assigned
SCENE_4_MISSION_1_DONE = "4_m1done"    # First mission completed
SCENE_4_MISSION_2 = "4_mission2"       # Second faction mission assigned
SCENE_4_MISSION_2_DONE = "4_m2done"    # Second mission completed
SCENE_4_NEWS_ESCALATION = "4_news"     # News: virus spreading further

# Act 5 scenes
SCENE_5_DEPLOYMENT = "5_deploy"         # Final deployment mission
SCENE_5_WARFARE_1 = "5_war1"           # News: viral warfare begins
SCENE_5_WARFARE_2 = "5_war2"           # News: warfare intensifies
SCENE_5_RESOLUTION = "5_resolve"       # Outcome determined

# Act 6 scenes
SCENE_6_AFTERMATH = "6_aftermath"       # News: aftermath articles
SCENE_6_SENTENCING = "6_sentence"       # News: ARC leader sentenced
SCENE_6_EPILOGUE = "6_epilogue"         # Final retrospective, plot complete
SCENE_6_COMPLETE = "6_complete"         # Plot fully done

# Plot mission types
MISSION_PLOT_STEAL = "PLOT_STEAL"       # Steal data from rival faction
MISSION_PLOT_DESTROY = "PLOT_DESTROY"   # Destroy rival's research
MISSION_PLOT_DEPLOY = "PLOT_DEPLOY"     # Deploy virus/counter-virus

# Act 4-6 timing (in game ticks, relative — scheduled dynamically after loyalty lock)
PLOT_ACT4_DELAY = 400        # ticks after loyalty lock before Act 4 starts
PLOT_MISSION_INTERVAL = 600  # ticks between missions
PLOT_ACT5_DELAY = 400        # ticks after Act 4 completes before Act 5
PLOT_ACT6_DELAY = 600        # ticks after Act 5 resolves before Act 6 epilogue

# Plot mission payments (Act 4-5)
PLOT_MISSION_1_PAYMENT = 6000
PLOT_MISSION_2_PAYMENT = 8000
PLOT_DEPLOY_PAYMENT = 12000
