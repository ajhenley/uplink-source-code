from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RunningTask(Base):
    __tablename__ = "running_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    tool_name: Mapped[str] = mapped_column(String(64))
    tool_version: Mapped[int] = mapped_column(Integer, default=1)
    target_ip: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    target_data: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    ticks_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
