from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id"), unique=True
    )
    name: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str] = mapped_column(String(64))
    balance: Mapped[int] = mapped_column(Integer, default=3000)
    uplink_rating: Mapped[int] = mapped_column(Integer, default=0)
    neuromancer_rating: Mapped[int] = mapped_column(Integer, default=5)
    credit_rating: Mapped[int] = mapped_column(Integer, default=10)
    gateway_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("gateways.id"), nullable=True
    )
    localhost_ip: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
