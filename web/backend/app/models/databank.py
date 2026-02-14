from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DataFile(Base):
    __tablename__ = "data_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    computer_id: Mapped[int] = mapped_column(ForeignKey("computers.id"))
    filename: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer)
    file_type: Mapped[int] = mapped_column(Integer)
    encrypted_level: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    softwaretype: Mapped[int] = mapped_column(Integer, default=0)
