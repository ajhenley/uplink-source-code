from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    name: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer)
    growth: Mapped[int] = mapped_column(Integer)
    alignment: Mapped[int] = mapped_column(Integer)
    boss_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    admin_email_addr: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
