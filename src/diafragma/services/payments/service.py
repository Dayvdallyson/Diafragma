from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from diafragma.models.products.models import Payment, Reservation

DEFAULT_PROVIDER = "stripe"


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

    payment = Payment(
        reservation_id=reservation.id,
        kind="rental",
        amount_cents=rental_amount_cents(reservation),
        currency=reservation.currency,
        provider=provider,
    )
    session.add(payment)
    session.commit()
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
    return Payment
