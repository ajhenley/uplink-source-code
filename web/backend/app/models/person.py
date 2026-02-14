from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    name: Mapped[str] = mapped_column(String(128))
    age: Mapped[int] = mapped_column(Integer)
    is_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    localhost_ip: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    uplink_rating: Mapped[int] = mapped_column(Integer, default=0)
    neuromancer_rating: Mapped[int] = mapped_column(Integer, default=0)
    has_criminal_record: Mapped[bool] = mapped_column(Boolean, default=False)
    voice_index: Mapped[int] = mapped_column(Integer, default=0)
    photo_index: Mapped[int] = mapped_column(Integer, default=0)
