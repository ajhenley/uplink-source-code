"""Player stock holdings."""
from ..extensions import db


class StockHolding(db.Model):
    __tablename__ = "stock_holdings"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False
    )
    company_name = db.Column(db.String(128), nullable=False)
    shares = db.Column(db.Integer, default=0, nullable=False)
    avg_buy_price = db.Column(db.Integer, default=0, nullable=False)  # in credits

    __table_args__ = (
        db.UniqueConstraint("game_session_id", "company_name", name="uq_holding"),
    )
