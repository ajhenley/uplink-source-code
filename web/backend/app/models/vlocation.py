from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class VLocation(Base):
    __tablename__ = "vlocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    ip: Mapped[str] = mapped_column(String(32), index=True)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    listed: Mapped[bool] = mapped_column(Boolean, default=True)
    computer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("computers.id"), nullable=True
    )
