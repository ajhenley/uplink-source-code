"""Stock market model."""
from app.extensions import db


class StockEntry(db.Model):
    __tablename__ = "stock_entries"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    company_name = db.Column(db.String(128), nullable=False)
    current_price = db.Column(db.Integer, nullable=False)
    previous_price = db.Column(db.Integer, nullable=False)
    volatility = db.Column(db.Float, default=0.1)


class StockHolding(db.Model):
    __tablename__ = "stock_holdings"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    company_name = db.Column(db.String(128), nullable=False)
    shares = db.Column(db.Integer, default=0)
    purchase_price = db.Column(db.Integer, default=0)
