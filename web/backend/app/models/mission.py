from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    mission_type: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(1024))
    employer_name: Mapped[str] = mapped_column(String(128))
    payment: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer)
    min_rating: Mapped[int] = mapped_column(Integer, default=0)
    target_computer_ip: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    target_data: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at_tick: Mapped[int] = mapped_column(Integer, default=0)
    due_at_tick: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
