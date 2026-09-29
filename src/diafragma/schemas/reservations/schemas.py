from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

Channel = Literal["web_voice", "phone", "telegram"]


class RentalPeriod(BaseModel):
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def validate_period(self) -> "RentalPeriod":
        if self.ends_on <= self.starts_on:
            raise ValueError("ends_on must be after starts_on")
        return self


class AvailabilityQuery(RentalPeriod):
    store_id: UUID | None = None


class CreateReservationRequest(RentalPeriod):
    product_id: UUID
    store_id: UUID
    channel: Channel


class AvailableUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_id: UUID
    condition: str


class AvailabilityResponse(BaseModel):
    product_id: UUID
    starts_on: date
    ends_on: date
    available: int
    units: list[AvailableUnitResponse]


class ReservationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    unit_id: UUID
    daily_rate_cents: int


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    starts_on: date
    ends_on: date
    expires_at: datetime | None
    currency: str
    items: list[ReservationItemResponse]

    @computed_field
    @property
    def total_cents(self) -> int:
        days = (self.ends_on - self.starts_on).days
        return days * sum(item.daily_rate_cents for item in self.items)
