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

# Game speed labels
SPEED_LABELS = {0: "Paused", 1: "Normal", 3: "Fast", 8: "MegaFast"}
VALID_SPEEDS = [0, 1, 3, 8]
