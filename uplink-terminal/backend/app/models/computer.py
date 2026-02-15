"""Computer and ComputerScreen models."""

import json

from ..extensions import db


class Computer(db.Model):
    __tablename__ = "computers"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    name = db.Column(db.String(128), nullable=False)
    company_name = db.Column(db.String(128), nullable=True)
    ip = db.Column(db.String(32), nullable=False)
    computer_type = db.Column(db.String(64), nullable=False, default="PUBLICACCESSSERVER")
    trace_speed = db.Column(db.Integer, default=-1)
    trace_action = db.Column(db.String(64), default="DISCONNECT")
    is_externally_open = db.Column(db.Boolean, default=True, nullable=False)
    admin_password = db.Column(db.String(64), nullable=True)

    screens = db.relationship("ComputerScreen", backref="computer", lazy=True,
                              cascade="all, delete-orphan",
                              order_by="ComputerScreen.screen_index")
    security_systems = db.relationship("SecuritySystem", backref="computer", lazy=True,
                                       cascade="all, delete-orphan")
    data_files = db.relationship("DataFile", backref="computer", lazy=True,
                                 cascade="all, delete-orphan")
    access_logs = db.relationship("AccessLog", backref="computer", lazy=True,
                                  cascade="all, delete-orphan",
                                  order_by="AccessLog.game_tick.desc()")
    bank_accounts = db.relationship("BankAccount", backref="computer", lazy=True,
                                    cascade="all, delete-orphan")
    lan_nodes = db.relationship("LanNode", backref="computer", lazy=True,
                                cascade="all, delete-orphan",
                                order_by="LanNode.node_index")

    def get_screen(self, index):
        """Get screen by index."""
        for s in self.screens:
            if s.screen_index == index:
                return s
        return None

    def __repr__(self):
        return f"<Computer {self.name} ({self.ip})>"


class ComputerScreen(db.Model):
    __tablename__ = "computer_screens"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    screen_index = db.Column(db.Integer, nullable=False)
    screen_type = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(128), default="")
    subtitle = db.Column(db.String(256), default="")
    content_json = db.Column(db.Text, default="{}")
    next_screen = db.Column(db.Integer, nullable=True)
    password = db.Column(db.String(64), nullable=True)

    @property
    def content(self):
        """Parse content JSON."""
        try:
            return json.loads(self.content_json) if self.content_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @content.setter
    def content(self, value):
        self.content_json = json.dumps(value)

    def __repr__(self):
        return f"<Screen {self.screen_index}:{self.screen_type} on Computer {self.computer_id}>"
