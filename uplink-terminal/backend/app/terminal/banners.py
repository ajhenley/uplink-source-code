"""ASCII art banners and headers."""

from .output import bright_green, dim, green, RESET, GREEN, DIM, BRIGHT_GREEN

LOGO = f"""{GREEN}\
  _   _ ____  _     ___ _   _ _  __
 | | | |  _ \\| |   |_ _| \\ | | |/ /
 | | | | |_) | |    | ||  \\| | ' /
 | |_| |  __/| |___ | || |\\  | . \\
  \\___/|_|   |_____|___|_| \\_|_|\\_\\{RESET}"""

WELCOME = f"""{LOGO}

{DIM}════════════════════════════════════════════════════{RESET}
{BRIGHT_GREEN}  UPLINK CORPORATION TERMINAL ACCESS v1.0{RESET}
{DIM}  (c) 2001-2026 Uplink Corporation{RESET}
{DIM}  All connections monitored and logged{RESET}
{DIM}════════════════════════════════════════════════════{RESET}

{GREEN}  Type 'login <user> <pass>' or 'register <user> <pass>'{RESET}
{GREEN}  Type 'help' for available commands{RESET}
"""

LOGIN_SUCCESS = f"""{DIM}════════════════════════════════════════════════════{RESET}
{BRIGHT_GREEN}  SESSION MANAGER{RESET}
{DIM}════════════════════════════════════════════════════{RESET}
{GREEN}  Type 'games' to list saves, 'new <name>' to start{RESET}
{GREEN}  Type 'help' for available commands{RESET}
"""

GAME_ENTER = f"""{DIM}════════════════════════════════════════════════════{RESET}
{BRIGHT_GREEN}  UPLINK OPERATING SYSTEM v3.1{RESET}
{DIM}  Gateway online. All systems nominal.{RESET}
{DIM}════════════════════════════════════════════════════{RESET}

{GREEN}  Type 'links' to view bookmarked systems{RESET}
{GREEN}  Type 'map' to browse the network{RESET}
{GREEN}  Type 'connect <ip|#>' to connect to a system{RESET}
{GREEN}  Type 'status' for system info, 'help' for all commands{RESET}
"""
