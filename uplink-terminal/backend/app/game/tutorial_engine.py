"""Progressive tutorial system — teaches new players via emails triggered by game actions."""

from ..extensions import db
from ..models import GameSession, Email


# Tutorial step definitions: (subject, body)
TUTORIAL_EMAILS = [
    # Step 0: Sent on game creation
    (
        "Tutorial [1/7]: Getting Started",
        (
            "Welcome, new agent. This tutorial will guide you through\n"
            "your first steps as an Uplink operative.\n\n"
            "STEP 1: View your available commands.\n"
            "  Type: help\n\n"
            "This will show you all commands grouped by category.\n"
            "When you're ready, type 'links' to see your bookmarked\n"
            "systems, then 'connect 128.185.0.4' to connect to the\n"
            "Uplink Test Machine.\n\n"
            "-- Uplink Training Division"
        ),
    ),
    # Step 1: Triggered when player connects to any system
    (
        "Tutorial [2/7]: Inside a Computer",
        (
            "Good — you've connected to a remote system.\n\n"
            "When connected, you'll see screens like password prompts,\n"
            "menus, and file servers. Key commands:\n"
            "  look    — re-display the current screen\n"
            "  dc      — disconnect from the system\n\n"
            "The Uplink Test Machine password is: test\n"
            "Type it now to authenticate.\n\n"
            "-- Uplink Training Division"
        ),
    ),
    # Step 2: Triggered when player authenticates on any system
    (
        "Tutorial [3/7]: Navigating Screens",
        (
            "You're in. Computer systems have numbered menu options.\n"
            "Type the number to navigate. Try exploring the File Server\n"
            "and Log Screen.\n\n"
            "On a file server, you can view files. On real targets,\n"
            "you'll need hacking tools to copy, delete, or decrypt files.\n\n"
            "Type 'dc' when done exploring, then read the next email.\n\n"
            "-- Uplink Training Division"
        ),
    ),
    # Step 3: Triggered when player disconnects (after having been connected)
    (
        "Tutorial [4/7]: Buying Tools",
        (
            "Before taking on real missions, you need tools.\n\n"
            "Connect to the Uplink Public Access Server:\n"
            "  connect 234.773.0.666\n\n"
            "Select 'Software Sales' from the menu, then:\n"
            "  buy password_breaker 1\n\n"
            "This buys Password Breaker v1.0 — essential for\n"
            "cracking passwords on secured systems.\n\n"
            "Use 'software' anytime to see your owned tools.\n\n"
            "-- Uplink Training Division"
        ),
    ),
    # Step 4: Triggered when player buys any software
    (
        "Tutorial [5/7]: Accepting a Mission",
        (
            "Now you're armed. Time for your first contract.\n\n"
            "On the Uplink PAS, select 'Mission Board (BBS)' to\n"
            "see available missions. Type 'accept <#>' to take one.\n\n"
            "Start with 'Steal File' or 'Destroy File' missions —\n"
            "they're the simplest. The mission email will tell you\n"
            "the target system IP and what to do.\n\n"
            "IMPORTANT: Use 'route' to set up bounce routing before\n"
            "hacking. This slows down traces and protects your identity.\n\n"
            "-- Uplink Training Division"
        ),
    ),
    # Step 5: Triggered when player accepts a mission
    (
        "Tutorial [6/7]: Completing a Mission",
        (
            "Mission accepted. Check your email for full details.\n\n"
            "Typical hacking workflow:\n"
            "  1. Set up route: route add <ip> (use InterNIC, etc.)\n"
            "  2. Connect to target: connect <target_ip>\n"
            "  3. Run tools: run password_breaker\n"
            "  4. Complete objective (steal/delete/edit)\n"
            "  5. COVER TRACKS: run log_deleter before disconnecting\n"
            "  6. Disconnect: dc\n"
            "  7. Reply to mission email: reply <#>\n\n"
            "If you don't delete logs, admin review may detect you\n"
            "and increase your criminal record!\n\n"
            "-- Uplink Training Division"
        ),
    ),
    # Step 6: Triggered when player completes a mission
    (
        "Tutorial [7/7]: Tutorial Complete",
        (
            "Congratulations — you've completed your first contract.\n\n"
            "You now know the basics of being an Uplink agent:\n"
            "  - Connect, authenticate, navigate screens\n"
            "  - Buy and run hacking tools\n"
            "  - Accept and complete missions\n"
            "  - Cover your tracks\n\n"
            "Advanced tips:\n"
            "  - 'probe' scans a system's security before connecting\n"
            "  - 'speed 3' or 'speed 8' speeds up gameplay\n"
            "  - 'record' shows your criminal record status\n"
            "  - 'stocks' shows your stock portfolio\n"
            "  - Higher-rated missions pay more but need better tools\n\n"
            "Good luck out there, agent.\n\n"
            "-- Uplink Training Division"
        ),
    ),
]


def advance_tutorial(gs, step):
    """Advance tutorial to the given step and send the corresponding email.

    Only advances forward — ignores if tutorial is already at or past the step.
    """
    plot_data = gs.plot_data
    current_step = plot_data.get("tutorial_step", 0)

    if step <= current_step:
        return

    if step >= len(TUTORIAL_EMAILS):
        return

    plot_data["tutorial_step"] = step
    gs.plot_data = plot_data

    subject, body = TUTORIAL_EMAILS[step]
    email = Email(
        game_session_id=gs.id,
        subject=subject,
        body=body,
        from_addr="training@intl.uplink.co.uk",
        to_addr="agent@uplink.co.uk",
        game_tick_sent=gs.game_time_ticks,
    )
    db.session.add(email)


def get_tutorial_status(gs):
    """Get current tutorial step and total steps."""
    step = gs.plot_data.get("tutorial_step", 0)
    total = len(TUTORIAL_EMAILS)
    completed = step >= total - 1
    return step, total, completed
