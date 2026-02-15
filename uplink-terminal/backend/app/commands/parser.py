"""Command tokenizer, registry, and dispatch."""

import shlex

from ..terminal.session import SessionState


class Command:
    def __init__(self, name, handler, states, usage, description):
        self.name = name
        self.handler = handler
        self.states = states
        self.usage = usage
        self.description = description


class CommandRegistry:
    def __init__(self):
        self._commands = {}

    def register(self, name, handler, states=None, usage="", description=""):
        if states is None:
            states = list(SessionState)
        self._commands[name] = Command(name, handler, states, usage, description)

    def get(self, name):
        return self._commands.get(name)

    def commands_for_state(self, state):
        return [
            cmd for cmd in self._commands.values() if state in cmd.states
        ]


registry = CommandRegistry()


def tokenize(text):
    """Split input into tokens, respecting quoted strings."""
    try:
        return shlex.split(text)
    except ValueError:
        # Unmatched quotes — fall back to simple split
        return text.split()


def dispatch(text, terminal_session):
    """Parse and execute a command. Returns output string."""
    text = text.strip()
    if not text:
        return None

    tokens = tokenize(text)
    cmd_name = tokens[0].lower()
    args = tokens[1:]

    cmd = registry.get(cmd_name)

    # Screen-contextual dispatch: when connected, try screen handler first
    # so screen-specific interpretations (e.g. 'addlink <#>' on InterNIC) win.
    # Core navigation commands (dc, look, connect, trace, status, etc.) always
    # go through the registry.
    _always_registry = {"dc", "look", "connect", "trace", "status", "help",
                        "clear", "save", "quit", "logout", "speed", "links",
                        "map", "rmlink", "run", "stop", "tools", "email",
                        "read", "reply", "software", "gateway", "route",
                        "probe", "record", "balance", "missions", "finance",
                        "whoami", "rename"}
    if (terminal_session.state == SessionState.IN_GAME
            and terminal_session.is_connected
            and cmd_name not in _always_registry):
        from ..game.screen_handler import handle_screen_input
        result = handle_screen_input(text, terminal_session)
        if result is not None:
            return result

    if cmd is not None and terminal_session.state in cmd.states:
        return cmd.handler(args, terminal_session)

    # If connected and nothing matched, try screen handler as final fallback
    if (terminal_session.state == SessionState.IN_GAME
            and terminal_session.is_connected):
        from ..game.screen_handler import handle_screen_input
        result = handle_screen_input(text, terminal_session)
        if result is not None:
            return result

    # Command exists but wrong state
    if cmd is not None:
        from ..terminal.output import error
        return error(f"Command '{cmd_name}' not available in current state.")

    from ..terminal.output import error
    return error(
        f"Unknown command: '{cmd_name}'. "
        f"Type 'help' for available commands."
    )
