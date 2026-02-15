"""DataFile model."""

import json

from ..extensions import db


class DataFile(db.Model):
    __tablename__ = "data_files"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    filename = db.Column(db.String(128), nullable=False)
    size = db.Column(db.Integer, default=1)
    file_type = db.Column(db.String(32), default="DATA")
    encrypted = db.Column(db.Boolean, default=False, nullable=False)
    compressed = db.Column(db.Boolean, default=False, nullable=False)
    content_json = db.Column(db.Text, default="{}")

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
        return f"<DataFile {self.filename}>"
