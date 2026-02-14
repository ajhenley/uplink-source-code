"""Data file model (files stored on computers)."""
from app.extensions import db


class DataFile(db.Model):
    __tablename__ = "data_files"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"))
    filename = db.Column(db.String(128), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.Integer, nullable=False)
    encrypted_level = db.Column(db.Integer, default=0)
    data = db.Column(db.String(4096), nullable=True)
    owner = db.Column(db.String(128), nullable=True)
    softwaretype = db.Column(db.Integer, default=0)
