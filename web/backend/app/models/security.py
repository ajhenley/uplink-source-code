from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SecuritySystem(Base):
    __tablename__ = "security_systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    computer_id: Mapped[int] = mapped_column(ForeignKey("computers.id"))
    security_type: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
