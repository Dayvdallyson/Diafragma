from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from diafragma.services.payments.service import (
    LatePaymentError,
    PaymentNotFoundError,
    confirm_payment,
    create_payment,
)
from diafragma.services.reservations.service import (
    PENDING_TTL,
    create_reservation,
    expire_pending_reservations,
)
from tests.reservations.conftest import ENDS_ON, STARTS_ON

EXTERNAL_ID = "pi_test_123"


def _pending_payment(session, catalog, user):
    reservation = create_reservation(
        session,
        user_id=user.id,
        product_id=UUID(catalog["product_id"]),
        store_id=UUID(catalog["store_id"]),
        starts_on=STARTS_ON,
        ends_on=ENDS_ON,
        channel="phone",
        idempotency_key="key-00000001",
    )
    payment = create_payment(session, user_id=user.id, reservation_id=reservation.id)
    payment.external_id = EXTERNAL_ID
    session.commit()
    return reservation, payment


def test_approves_payment_and_confirms_reservation(session, catalog, make_user):
    reservation, payment = _pending_payment(session, catalog, make_user())

    confirm_payment(session, provider="stripe", external_id=EXTERNAL_ID)

    session.refresh(payment)
    session.refresh(reservation)
    assert payment.status == "approved"
    assert payment.paid_at is not None
    assert reservation.status == "confirmed"


def test_is_idempotent_for_webhook_retries(session, catalog, make_user):
    reservation, payment = _pending_payment(session, catalog, make_user())

    confirm_payment(session, provider="stripe", external_id=EXTERNAL_ID)
    confirm_payment(session, provider="stripe", external_id=EXTERNAL_ID)
    retry = confirm_payment(session, provider="stripe", external_id=EXTERNAL_ID)

    session.refresh(payment)
    session.refresh(reservation)
    assert payment.status == "approved"
    assert retry.status == "approved"
    assert reservation.status == "confirmed"


def test_unknown_external_id(session):
    with pytest.raises(PaymentNotFoundError):
        confirm_payment(session, provider="stripe", external_id="pi_missing")


def test_late_payment_keeps_money_but_not_reservation(session, catalog, make_user):
    reservation, payment = _pending_payment(session, catalog, make_user())
    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(seconds=1)

    with pytest.raises(LatePaymentError):
        confirm_payment(
            session, provider="stripe", external_id=EXTERNAL_ID, now=after_ttl
        )

    session.refresh(payment)
    session.refresh(reservation)
    assert payment.status == "approved"
    assert reservation.status != "confirmed"


def test_payment_after_expiration_job_is_late(session, catalog, make_user):
    reservation, _ = _pending_payment(session, catalog, make_user())

    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(seconds=1)
    expire_pending_reservations(session, now=after_ttl)

    with pytest.raises(LatePaymentError):
        confirm_payment(
            session, provider="stripe", external_id=EXTERNAL_ID, now=after_ttl
        )

    session.refresh(reservation)
    assert reservation.status == "expired"
