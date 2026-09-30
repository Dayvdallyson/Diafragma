from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from diafragma.models.products.models import ReservationItem, Unit
from diafragma.services.payments.service import (
    ReservationNotFoundError,
    ReservationNotPayableError,
    create_payment,
)
from diafragma.services.reservations.service import PENDING_TTL, create_reservation
from tests.reservations.conftest import DAILY_RATE, ENDS_ON, STARTS_ON

RENTAL_DAYS = (ENDS_ON - STARTS_ON).days


def _reserve(session, catalog, user):
    return create_reservation(
        session,
        user_id=user.id,
        product_id=UUID(catalog["product_id"]),
        store_id=UUID(catalog["store_id"]),
        starts_on=STARTS_ON,
        ends_on=ENDS_ON,
        channel="phone",
        idempotency_key="key-00000001",
    )


def test_creates_pending_rental_payment_for_full_period(session, catalog, make_user):
    user = make_user()
    reservation = _reserve(session, catalog, user)

    payment = create_payment(session, user_id=user.id, reservation_id=reservation.id)

    assert payment.status == "pending"
    assert payment.kind == "rental"
    assert payment.provider == "stripe"
    assert payment.currency == reservation.currency
    assert payment.external_id is None
    assert payment.amount_cents == DAILY_RATE * RENTAL_DAYS


def test_amount_sums_every_item(session, catalog, make_user):
    user = make_user()
    reservation = _reserve(session, catalog, user)
    second_unit = Unit(
        product_id=UUID(catalog["product_id"]),
        store_id=UUID(catalog["store_id"]),
        serial_number="SN-2",
    )
    session.add(second_unit)
    session.flush()
    session.add(
        ReservationItem(
            reservation_id=reservation.id,
            unit_id=second_unit.id,
            daily_rate_cents=5_000,
        )
    )
    session.commit()
    session.refresh(reservation)

    payment = create_payment(session, user_id=user.id, reservation_id=reservation.id)

    assert payment.amount_cents == (DAILY_RATE + 5_000) * RENTAL_DAYS


def test_rejects_unknown_reservation(session, make_user):
    with pytest.raises(ReservationNotFoundError):
        create_payment(session, user_id=make_user().id, reservation_id=uuid4())


def test_rejects_reservation_of_another_user(session, catalog, make_user):
    reservation = _reserve(session, catalog, make_user())

    with pytest.raises(ReservationNotFoundError):
        create_payment(session, user_id=make_user().id, reservation_id=reservation.id)


@pytest.mark.parametrize("status", ["confirmed", "cancelled", "expired"])
def test_rejects_reservation_that_is_not_pending(session, catalog, make_user, status):
    user = make_user()
    reservation = _reserve(session, catalog, user)
    reservation.status = status
    session.commit()

    with pytest.raises(ReservationNotPayableError):
        create_payment(session, user_id=user.id, reservation_id=reservation.id)


def test_rejects_pending_reservation_past_its_ttl(session, catalog, make_user):
    user = make_user()
    reservation = _reserve(session, catalog, user)
    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(seconds=1)

    with pytest.raises(ReservationNotPayableError):
        create_payment(
            session, user_id=user.id, reservation_id=reservation.id, now=after_ttl
        )
