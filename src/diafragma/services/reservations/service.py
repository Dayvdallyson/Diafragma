from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from psycopg import errors as pg_errors
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from diafragma.models.products.models import (
    Product,
    ProductPrice,
    Reservation,
    ReservationItem,
    Store,
    Unit,
    UnitBlock,
)
from diafragma.services.products.service import ProductNotFoundError

PENDING_TTL = timedelta(minutes=15)
IDEMPOTENCY_CONSTRAINT = "uq_reservation_idempotency_key"
CONFLICT_ERRORS = (pg_errors.ExclusionViolation, pg_errors.DeadlockDetected)


class UnitUnavailableError(Exception):
    pass


class InvalidRentalPeriodError(Exception):
    pass


class PriceNotFoundError(Exception):
    pass


def find_available_units(
    session: Session,
    product_id: UUID,
    starts_on: date,
    ends_on: date,
    store_id: UUID | None = None,
) -> list[Unit]:
    period = Range(starts_on, ends_on, bounds="[)")
    overlapping_block = select(UnitBlock.id).where(
        UnitBlock.unit_id == Unit.id,
        UnitBlock.period.overlaps(period),
    )
    stmt = (
        select(Unit)
        .where(
            Unit.product_id == product_id,
            Unit.status == "active",
            ~overlapping_block.exists(),
        )
        .order_by(Unit.serial_number)
    )
    if store_id is not None:
        stmt = stmt.where(Unit.store_id == store_id)
    return list(session.scalars(stmt))


def _violated(error: DBAPIError, constraint: str) -> bool:
    diag = getattr(error.orig, "diag", None)
    return diag is not None and diag.constraint_name == constraint


def _find_by_key(session: Session, user_id: UUID, key: str) -> Reservation | None:
    return session.scalar(
        select(Reservation).where(
            Reservation.user_id == user_id, Reservation.idempotency_key == key
        )
    )


def _current_price(session: Session, product_id: UUID, country: str) -> ProductPrice:
    now = func.now()
    price = session.scalar(
        select(ProductPrice)
        .where(
            ProductPrice.product_id == product_id,
            ProductPrice.country == country,
            ProductPrice.valid_from <= now,
            or_(ProductPrice.valid_until.is_(None), ProductPrice.valid_until > now),
        )
        .order_by(ProductPrice.valid_from.desc())
        .limit(1)
    )
    if price is None:
        raise PriceNotFoundError(product_id)
    return price


def create_reservation(
    session: Session,
    *,
    user_id: UUID,
    product_id: UUID,
    store_id: UUID,
    starts_on: date,
    ends_on: date,
    channel: str,
    idempotency_key: str,
) -> Reservation:
    if existing := _find_by_key(session, user_id, idempotency_key):
        return existing

    product = session.get(Product, product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    days = (ends_on - starts_on).days
    if not product.min_rental_days <= days <= product.max_rental_days:
        raise InvalidRentalPeriodError(days)
    store = session.get_one(Store, store_id)
    price = _current_price(session, product_id, store.country)

    reservation = Reservation(
        user_id=user_id,
        pickup_store_id=store_id,
        return_store_id=store_id,
        starts_on=starts_on,
        ends_on=ends_on,
        currency=price.currency,
        channel=channel,
        expires_at=datetime.now(UTC) + PENDING_TTL,
        idempotency_key=idempotency_key,
    )
    session.add(reservation)
    try:
        session.flush()
    except IntegrityError as e:
        session.rollback()
        if _violated(e, IDEMPOTENCY_CONSTRAINT):
            return _find_by_key(session, user_id, idempotency_key)
        raise

    period = Range(starts_on, ends_on, bounds="[)")
    for unit in find_available_units(session, product_id, starts_on, ends_on, store_id):
        try:
            with session.begin_nested():
                item = ReservationItem(
                    reservation=reservation,
                    unit_id=unit.id,
                    daily_rate_cents=price.daily_rate_cents,
                )
                session.add(item)
                session.flush()
                session.add(
                    UnitBlock(
                        unit_id=unit.id, period=period, reservation_item_id=item.id
                    )
                )
        except DBAPIError as e:
            if not isinstance(e.orig, CONFLICT_ERRORS):
                raise
            continue
        session.commit()
        return reservation

    session.rollback()
    raise UnitUnavailableError(product_id)
