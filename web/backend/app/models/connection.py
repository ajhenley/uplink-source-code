from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    target_ip: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trace_progress: Mapped[float] = mapped_column(Float, default=0.0)
    trace_active: Mapped[bool] = mapped_column(Boolean, default=False)


class ConnectionNode(Base):
    __tablename__ = "connection_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"))
    position: Mapped[int] = mapped_column(Integer)
    ip: Mapped[str] = mapped_column(String(32))
    is_traced: Mapped[bool] = mapped_column(Boolean, default=False)
