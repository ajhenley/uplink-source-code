"""Terminal session state machine."""

from enum import Enum


class SessionState(Enum):
    UNAUTHENTICATED = "unauthenticated"
    AUTHENTICATED = "authenticated"
    IN_GAME = "in_game"


class TerminalSession:
    """Per-connection terminal state."""

    def __init__(self, sid):
        self.sid = sid
        self.state = SessionState.UNAUTHENTICATED
        self.user_id = None
        self.username = None
        self.game_session_id = None
        self.game_session_name = None
        # Connection tracking
        self.current_computer_ip = None
        self.current_screen_index = 0
        self.authenticated_on_computer = False
        self.current_lan_node = None

    @property
    def is_in_lan(self):
        return self.current_lan_node is not None

    @property
    def prompt(self):
        if self.state == SessionState.UNAUTHENTICATED:
            return "> "
        elif self.state == SessionState.AUTHENTICATED:
            return f"{self.username}> "
        elif self.current_computer_ip:
            return f"{self.current_computer_ip}> "
        else:
            return "uplink> "

    @property
    def is_connected(self):
        return self.current_computer_ip is not None

    def login(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.state = SessionState.AUTHENTICATED

    def logout(self):
        self.leave_game()
        self.user_id = None
        self.username = None
        self.state = SessionState.UNAUTHENTICATED

    def enter_game(self, session_id, session_name):
        self.game_session_id = session_id
        self.game_session_name = session_name
        self.state = SessionState.IN_GAME

    def leave_game(self):
        self.disconnect()
        self.game_session_id = None
        self.game_session_name = None
        if self.user_id:
            self.state = SessionState.AUTHENTICATED
        else:
            self.state = SessionState.UNAUTHENTICATED

    def connect_to(self, ip, start_screen=0):
        """Connect to a remote computer."""
        self.current_computer_ip = ip
        self.current_screen_index = start_screen
        self.authenticated_on_computer = False
        self.current_lan_node = None

    def disconnect(self):
        """Disconnect from current computer."""
        self.current_computer_ip = None
        self.current_screen_index = 0
        self.authenticated_on_computer = False
        self.current_lan_node = None
