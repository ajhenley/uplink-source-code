"""News article model."""
from app.extensions import db


class NewsArticle(db.Model):
    __tablename__ = "news_articles"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    headline = db.Column(db.String(256), nullable=False)
    body = db.Column(db.String(4096), nullable=False)
    category = db.Column(db.String(64), default="general")
    created_at_tick = db.Column(db.Integer, default=0)
    expires_at_tick = db.Column(db.Integer, nullable=True)
