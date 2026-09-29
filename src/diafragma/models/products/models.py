from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, JSONB, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diafragma.db.base import Base
from diafragma.db.types import (
    Cents,
    CountryCode,
    CreatedAt,
    CurrencyCode,
    Timestamp,
    UuidPk,
    one_of,
)
from diafragma.models.users.models import User


class Store(Base):
    __tablename__ = "store"

    id: Mapped[UuidPk]
    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[CountryCode]
    city: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text)
    time_zone: Mapped[str] = mapped_column(String(64))
    currency: Mapped[CurrencyCode]
    phone: Mapped[str | None] = mapped_column(String(16))

    units: Mapped[list["Unit"]] = relationship(back_populates="store")


class Product(Base):
    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint(
            one_of("category", ["camera", "lens", "lighting", "audio", "accessory"]),
            name="category_valid",
        ),
        CheckConstraint("min_rental_days >= 1", name="min_days_positive"),
        CheckConstraint("max_rental_days >= min_rental_days", name="max_gte_min"),
    )

    id: Mapped[UuidPk]
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    specifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    min_rental_days: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    max_rental_days: Mapped[int] = mapped_column(SmallInteger, server_default="30")
    created_at: Mapped[CreatedAt]

    photos: Mapped[list["ProductPhoto"]] = relationship(
        back_populates="product", order_by="ProductPhoto.position"
    )
    prices: Mapped[list["ProductPrice"]] = relationship(back_populates="product")
    units: Mapped[list["Unit"]] = relationship(back_populates="product")


class ProductPhoto(Base):
    __tablename__ = "product_photo"
    __table_args__ = (UniqueConstraint("product_id", "position"),)

    id: Mapped[UuidPk]
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    s3_key: Mapped[str] = mapped_column(String(512))
    position: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    alt_text: Mapped[str | None] = mapped_column(String(300))

    product: Mapped["Product"] = relationship(back_populates="photos")


class ProductPrice(Base):
    __tablename__ = "product_price"
    __table_args__ = (
        CheckConstraint("daily_rate_cents > 0", name="rate_positive"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from", name="valid_period"
        ),
    )

    id: Mapped[UuidPk]
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    country: Mapped[CountryCode]
    currency: Mapped[CurrencyCode]
    daily_rate_cents: Mapped[Cents]
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    valid_until: Mapped[Timestamp | None]

    product: Mapped["Product"] = relationship(back_populates="prices")


class UnitBlock(Base):
    __tablename__ = "unit_block"
    __table_args__ = (
        ExcludeConstraint(
            ("unit_id", "="),
            ("period", "&&"),
            name="unit_block_no_overlap",
            using="gist",
        ),
        CheckConstraint(
            "(reservation_item_id IS NULL) <> (maintenance_id IS NULL)",
            name="exactly_one_source",
        ),
        CheckConstraint(
            "NOT isempty(period) AND NOT lower_inf(period)",
            name="period_valid",
        ),
    )

    id: Mapped[UuidPk]
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("unit.id"))
    period: Mapped[Range[Date]] = mapped_column(DATERANGE)
    reservation_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reservation_item.id", ondelete="CASCADE"), unique=True
    )
    maintenance_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("maintenance.id", ondelete="CASCADE"), unique=True
    )
    created_at: Mapped[CreatedAt]

    unit: Mapped["Unit"] = relationship()


class Unit(Base):
    __tablename__ = "unit"
    __table_args__ = (
        CheckConstraint(
            one_of("condition", ["new", "excellent", "good", "fair"]),
            name="condition_valid",
        ),
        CheckConstraint(
            one_of("status", ["active", "sold", "lost", "retired"]),
            name="status_valid",
        ),
    )

    id: Mapped[UuidPk]
    product_id: Mapped[UUID] = mapped_column(ForeignKey("product.id"))
    store_id: Mapped[UUID] = mapped_column(ForeignKey("store.id"))
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    condition: Mapped[str] = mapped_column(String(20), server_default="new")
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    acquired_at: Mapped[date | None] = mapped_column(Date)

    product: Mapped["Product"] = relationship(back_populates="units")
    store: Mapped["Store"] = relationship(back_populates="units")
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="unit")


class Maintenance(Base):
    __tablename__ = "maintenance"
    __table_args__ = (
        CheckConstraint("cost_cents IS NULL OR cost_cents >= 0", name="cost_positive"),
        CheckConstraint(
            "(cost_cents IS NULL) = (currency IS NULL)", name="cost_has_currency"
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at > starts_at", name="valid_period"
        ),
    )

    id: Mapped[UuidPk]
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("unit.id"))
    reason: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[Timestamp]
    expected_end_at: Mapped[Timestamp | None]
    ended_at: Mapped[Timestamp | None]
    cost_cents: Mapped[Cents | None]
    currency: Mapped[CurrencyCode | None]

    unit: Mapped["Unit"] = relationship(back_populates="maintenances")


class Reservation(Base):
    __tablename__ = "reservation"
    __table_args__ = (
        CheckConstraint("ends_on > starts_on", name="valid_period"),
        CheckConstraint(
            one_of(
                "status",
                [
                    "pending",
                    "confirmed",
                    "picked_up",
                    "returned",
                    "cancelled",
                    "expired",
                ],
            ),
            name="status_valid",
        ),
        CheckConstraint(
            one_of("channel", ["web_voice", "phone", "telegram"]), name="channel_valid"
        ),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_reservation_idempotency_key"
        ),
    )

    id: Mapped[UuidPk]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    pickup_store_id: Mapped[UUID] = mapped_column(ForeignKey("store.id"))
    return_store_id: Mapped[UUID] = mapped_column(ForeignKey("store.id"))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    expires_at: Mapped[Timestamp | None]
    picked_up_at: Mapped[Timestamp | None]
    returned_at: Mapped[Timestamp | None]
    currency: Mapped[CurrencyCode]
    channel: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[CreatedAt]

    user: Mapped[User] = relationship()
    items: Mapped[list["ReservationItem"]] = relationship(back_populates="reservation")
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    payments: Mapped[list["Payment"]] = relationship(back_populates="reservation")


class ReservationItem(Base):
    __tablename__ = "reservation_item"
    __table_args__ = (
        UniqueConstraint("reservation_id", "unit_id"),
        CheckConstraint("daily_rate_cents > 0", name="rate_positive"),
    )

    id: Mapped[UuidPk]
    reservation_id: Mapped[UUID] = mapped_column(
        ForeignKey("reservation.id", ondelete="CASCADE")
    )
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("unit.id"))
    daily_rate_cents: Mapped[Cents]

    reservation: Mapped["Reservation"] = relationship(back_populates="items")
    unit: Mapped["Unit"] = relationship()


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (
        UniqueConstraint("provider", "external_id"),
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint(
            one_of("kind", ["rental", "deposit", "penalty"]), name="kind_valid"
        ),
        CheckConstraint(
            one_of("status", ["pending", "approved", "declined", "refunded"]),
            name="status_valid",
        ),
    )

    id: Mapped[UuidPk]
    reservation_id: Mapped[UUID] = mapped_column(ForeignKey("reservation.id"))
    kind: Mapped[str] = mapped_column(String(20))
    amount_cents: Mapped[Cents]
    currency: Mapped[CurrencyCode]
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    provider: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[CreatedAt]
    paid_at: Mapped[Timestamp | None]

    reservation: Mapped["Reservation"] = relationship(back_populates="payments")
