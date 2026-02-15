"""RunningTool model — active hacking tools."""

import json

from ..extensions import db


class RunningTool(db.Model):
    __tablename__ = "running_tools"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    software_id = db.Column(db.Integer, db.ForeignKey("software.id"), nullable=False)
    tool_type = db.Column(db.String(32), nullable=False)
    target_ip = db.Column(db.String(32), nullable=False, default="")
    target_param = db.Column(db.String(256), nullable=True)
    progress = db.Column(db.Float, default=0.0)
    ticks_required = db.Column(db.Integer, default=100)
    ticks_elapsed = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(32), default="RUNNING", nullable=False)
    result_json = db.Column(db.Text, default="{}")

    software = db.relationship("Software", lazy=True)

    @property
    def result(self):
        try:
            return json.loads(self.result_json) if self.result_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @result.setter
    def result(self, value):
        self.result_json = json.dumps(value)

    def __repr__(self):
        return f"<RunningTool {self.tool_type} [{self.status}] {self.progress:.0f}%>"
