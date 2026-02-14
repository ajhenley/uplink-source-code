from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AccessLog(Base):
    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    computer_id: Mapped[int] = mapped_column(ForeignKey("computers.id"))
    log_time: Mapped[str] = mapped_column(String(32))
    from_ip: Mapped[str] = mapped_column(String(32))
    from_name: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(String(256))
    log_type: Mapped[int] = mapped_column(Integer)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    data1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
