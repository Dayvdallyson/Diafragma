from datetime import date
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Enum,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from diafragma.db.base import Base
from diafragma.db.types import CountryCode, CreatedAt, UuidPk


class UserRole(StrEnum):
    ADMIN = "admin"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role != 'ADMIN' OR (email IS NOT NULL AND hashed_password IS NOT NULL)",
            name="admin_has_credentials",
        ),
        CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL OR telegram_chat_id IS NOT NULL",
            name="has_contact",
        ),
        CheckConstraint(r"phone ~ '^\+[1-9][0-9]{7,14}$'", name="phone_e164"),
        UniqueConstraint("document_country", "document_type", "document_number"),
    )

    id: Mapped[UuidPk]
    name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        default=UserRole.CUSTOMER,
    )

    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(16), unique=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)

    hashed_password: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

    birth_date: Mapped[date | None] = mapped_column(Date)
    country: Mapped[CountryCode | None]
    city: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), server_default="pt-BR")
    document_type: Mapped[str | None] = mapped_column(String(20))
    document_number: Mapped[str | None] = mapped_column(String(50))
    document_country: Mapped[CountryCode | None]
    reliability_points: Mapped[int] = mapped_column(Integer, server_default="0")

    created_at: Mapped[CreatedAt]
