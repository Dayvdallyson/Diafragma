from datetime import UTC, datetime, timedelta
from uuid import UUID

from diafragma.models.products.models import Reservation
from diafragma.services.reservations.service import (
    PENDING_TTL,
    create_reservation,
    expire_pending_reservations,
    find_available_units,
)
from tests.reservations.conftest import ENDS_ON, STARTS_ON


def _reserve(session, catalog, user, key="key-00000001") -> Reservation:
    return create_reservation(
        session,
        user_id=user.id,
        product_id=UUID(catalog["product_id"]),
        store_id=UUID(catalog["store_id"]),
        starts_on=STARTS_ON,
        ends_on=ENDS_ON,
        channel="phone",
        idempotency_key=key,
    )


def _available(session, catalog) -> int:
    return len(
        find_available_units(session, UUID(catalog["product_id"]), STARTS_ON, ENDS_ON)
    )


def test_expires_overdue_pending_and_frees_unit(session, catalog, make_user):
    reservation = _reserve(session, catalog, make_user())
    assert _available(session, catalog) == 0

    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(seconds=1)
    expired = expire_pending_reservations(session, now=after_ttl)

    assert expired == 1
    session.refresh(reservation)
    assert reservation.status == "expired"
    assert _available(session, catalog) == 1


def test_keeps_pending_that_has_not_reached_ttl(session, catalog, make_user):
    reservation = _reserve(session, catalog, make_user())

    expired = expire_pending_reservations(session, now=datetime.now(UTC))

    assert expired == 0
    session.refresh(reservation)
    assert reservation.status == "pending"
    assert _available(session, catalog) == 0


def test_never_expires_confirmed_reservation(session, catalog, make_user):
    reservation = _reserve(session, catalog, make_user())
    reservation.status = "confirmed"
    session.commit()

    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(hours=1)
    expired = expire_pending_reservations(session, now=after_ttl)

    assert expired == 0
    session.refresh(reservation)
    assert reservation.status == "confirmed"
    assert _available(session, catalog) == 0


def test_is_idempotent(session, catalog, make_user):
    _reserve(session, catalog, make_user())
    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(seconds=1)

    assert expire_pending_reservations(session, now=after_ttl) == 1
    assert expire_pending_reservations(session, now=after_ttl) == 0


def test_freed_unit_can_be_booked_again(session, catalog, make_user):
    _reserve(session, catalog, make_user(), key="key-00000001")
    after_ttl = datetime.now(UTC) + PENDING_TTL + timedelta(seconds=1)
    expire_pending_reservations(session, now=after_ttl)

    second = _reserve(session, catalog, make_user(), key="key-00000002")

    assert second.status == "pending"
    assert len(second.items) == 1
