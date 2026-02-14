from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    event_type: Mapped[str] = mapped_column(String(64))  # "warning", "fine", "arrest", "mission_generate"
    trigger_tick: Mapped[int] = mapped_column(Integer)
    data: Mapped[str] = mapped_column(String(4096), default="{}")  # JSON string
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
