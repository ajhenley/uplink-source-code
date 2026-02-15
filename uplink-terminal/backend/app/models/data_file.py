"""DataFile model."""

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

    def __repr__(self):
        return f"<DataFile {self.filename}>"
