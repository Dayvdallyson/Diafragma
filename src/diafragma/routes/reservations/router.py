from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from diafragma.auth.dependencies import CurrentUser
from diafragma.db.dependencies import SessionDep
from diafragma.schemas.reservations.schemas import (
    CreateReservationRequest,
    ReservationResponse,
)
from diafragma.services.products.service import ProductNotFoundError
from diafragma.services.reservations.service import (
    InvalidRentalPeriodError,
    PriceNotFoundError,
    StoreNotFoundError,
    UnitUnavailableError,
    create_reservation,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])

IdempotencyKey = Annotated[str, Header(min_length=8, max_length=64)]


@router.post(
    "", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED
)
def create(
    payload: CreateReservationRequest,
    user: CurrentUser,
    session: SessionDep,
    idempotency_key: IdempotencyKey,
):
    try:
        return create_reservation(
            session,
            user_id=user.id,
            idempotency_key=idempotency_key,
            **payload.model_dump(),
        )
    except (ProductNotFoundError, StoreNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{type(e).__name__.removesuffix('NotFoundError')} not found",
        )
    except (InvalidRentalPeriodError, PriceNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
        )
    except UnitUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No unit available for this period",
        )
