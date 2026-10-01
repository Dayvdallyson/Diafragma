from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from diafragma.models.products.models import Payment, Reservation
from diafragma.services.reservations.service import _violated

DEFAULT_PROVIDER = "stripe"
ACTIVE_PAYMENT_INDEX = "uq_payment_one_active_per_reservation_kind"


class ReservationNotFoundError(Exception):
    pass


class ReservationNotPayableError(Exception):
    pass


class PaymentNotFoundError(Exception):
    pass


class LatePaymentError(Exception):
    def __init__(self, payment: Payment):
        super().__init__(payment.id)
        self.payment = payment


def _find_pending(session: Session, reservation_id: UUID) -> Payment | None:
    payment = session.scalars(
        select(Payment).where(
            Payment.reservation_id == reservation_id,
            Payment.kind == "rental",
            Payment.status == "pending",
        )
    ).one_or_none()
    return payment


def rental_amount_cents(reservation: Reservation) -> int:
    days = (reservation.ends_on - reservation.starts_on).days
    return sum(item.daily_rate_cents for item in reservation.items) * days


def create_payment(
    session: Session,
    *,
    user_id: UUID,
    reservation_id: UUID,
    provider: str = DEFAULT_PROVIDER,
    now: datetime | None = None,
) -> Payment:
    now = now or datetime.now(UTC)
    reservation = session.get(Reservation, reservation_id)
    if reservation is None or reservation.user_id != user_id:
        raise ReservationNotFoundError(reservation_id)
    if reservation.status != "pending" or (
        reservation.expires_at is not None and reservation.expires_at <= now
    ):
        raise ReservationNotPayableError(reservation_id)

    if existing := _find_pending(session, reservation_id):
        return existing

    payment = Payment(
        reservation_id=reservation_id,
        kind="rental",
        amount_cents=rental_amount_cents(reservation),
        currency=reservation.currency,
        provider=provider,
    )
    session.add(payment)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        if _violated(e, ACTIVE_PAYMENT_INDEX):
            return _find_pending(session, reservation.id)
        raise
    return payment


def confirm_payment(
    session: Session, *, provider: str, external_id: str, now: datetime | None = None
) -> Payment:
    now = now or datetime.now(UTC)
    payment = session.scalars(
        select(Payment).where(
            Payment.provider == provider, Payment.external_id == external_id
        )
    ).one_or_none()
    if payment is None:
        raise PaymentNotFoundError(external_id)

    won = session.scalars(
        update(Payment)
        .where(Payment.id == payment.id, Payment.status == "pending")
        .values(status="approved", paid_at=now)
        .returning(Payment.id)
    ).one_or_none()
    if won is None:
        return payment

    confirmed = session.scalars(
        update(Reservation)
        .where(
            Reservation.id == payment.reservation_id,
            Reservation.status == "pending",
            Reservation.expires_at > now,
        )
        .values(status="confirmed")
        .returning(Reservation.id)
    ).one_or_none()

    session.commit()

    if confirmed is None:
        raise LatePaymentError(payment)
    return payment
