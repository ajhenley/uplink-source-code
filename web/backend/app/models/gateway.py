from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Gateway(Base):
    __tablename__ = "gateways"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id")
    )
    name: Mapped[str] = mapped_column(String(64), default="Gateway ALPHA")
    cpu_speed: Mapped[int] = mapped_column(Integer, default=60)
    modem_speed: Mapped[int] = mapped_column(Integer, default=1)
    memory_size: Mapped[int] = mapped_column(Integer, default=24)
    has_self_destruct: Mapped[bool] = mapped_column(Boolean, default=False)
    has_motion_sensor: Mapped[bool] = mapped_column(Boolean, default=False)
