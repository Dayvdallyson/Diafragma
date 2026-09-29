from datetime import UTC, datetime, timedelta
from uuid import UUID

from diafragma.models.products.models import ProductPrice
from diafragma.services.reservations.service import create_reservation
from tests.reservations.conftest import DAILY_RATE, ENDS_ON, STARTS_ON


def test_uses_current_price_not_scheduled_one(session, catalog, make_user):
    session.add(
        ProductPrice(
            product_id=UUID(catalog["product_id"]),
            country="BR",
            currency="BRL",
            daily_rate_cents=99_999,
            valid_from=datetime.now(UTC) + timedelta(days=7),
        )
    )
    session.commit()

    reservation = create_reservation(
        session,
        user_id=make_user().id,
        product_id=UUID(catalog["product_id"]),
        store_id=UUID(catalog["store_id"]),
        starts_on=STARTS_ON,
        ends_on=ENDS_ON,
        channel="phone",
        idempotency_key="key-00000001",
    )

    assert reservation.items[0].daily_rate_cents == DAILY_RATE
