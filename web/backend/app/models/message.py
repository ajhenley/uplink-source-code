from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    from_name: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(String(4096))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at_tick: Mapped[int] = mapped_column(Integer, default=0)
