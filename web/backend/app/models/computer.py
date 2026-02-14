from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Computer(Base):
    __tablename__ = "computers"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    name: Mapped[str] = mapped_column(String(128))
    company_name: Mapped[str] = mapped_column(String(128))
    ip: Mapped[str] = mapped_column(String(32))
    computer_type: Mapped[int] = mapped_column(Integer)
    trace_speed: Mapped[float] = mapped_column(Float)
    hack_difficulty: Mapped[float] = mapped_column(Float)
    is_running: Mapped[bool] = mapped_column(Boolean, default=True)


class ComputerScreenDef(Base):
    __tablename__ = "computer_screen_defs"

    id: Mapped[int] = mapped_column(primary_key=True)
    computer_id: Mapped[int] = mapped_column(ForeignKey("computers.id"))
    screen_type: Mapped[int] = mapped_column(Integer)
    next_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sub_page: Mapped[int] = mapped_column(Integer, default=0)
    data1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    data2: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    data3: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
