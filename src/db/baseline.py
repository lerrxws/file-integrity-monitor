from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Baseline(Base):
    __tablename__ = "baselines"

    path: Mapped[str] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64))
