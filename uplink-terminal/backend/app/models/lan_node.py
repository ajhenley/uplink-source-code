"""LAN node model for internal network topology."""

import json

from ..extensions import db


class LanNode(db.Model):
    __tablename__ = "lan_nodes"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    node_index = db.Column(db.Integer, nullable=False)
    node_type = db.Column(db.String(32), nullable=False)  # ROUTER, TERMINAL, LOCK, FILE_SERVER, MAINFRAME
    label = db.Column(db.String(64), nullable=False)
    row = db.Column(db.Integer, nullable=False, default=0)
    col = db.Column(db.Integer, nullable=False, default=0)
    is_discovered = db.Column(db.Boolean, default=False, nullable=False)
    is_locked = db.Column(db.Boolean, default=True, nullable=False)
    security_level = db.Column(db.Integer, default=0, nullable=False)
    is_bypassed = db.Column(db.Boolean, default=False, nullable=False)
    connections_json = db.Column(db.Text, default="[]")
    content_json = db.Column(db.Text, default="{}")

    @property
    def connections(self):
        try:
            return json.loads(self.connections_json) if self.connections_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    @connections.setter
    def connections(self, value):
        self.connections_json = json.dumps(value)

    @property
    def content(self):
        try:
            return json.loads(self.content_json) if self.content_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @content.setter
    def content(self, value):
        self.content_json = json.dumps(value)

    def __repr__(self):
        return f"<LanNode {self.node_index}:{self.node_type} on Computer {self.computer_id}>"
