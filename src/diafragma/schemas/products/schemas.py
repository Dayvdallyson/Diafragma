from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def normalize_category(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


Category = Annotated[
    Literal["camera", "lens", "lighting", "audio", "accessory"],
    BeforeValidator(normalize_category),
]


class CreateProductRequest(BaseModel):
    sku: str = Field(max_length=64)
    name: str = Field(max_length=200)
    brand: str = Field(max_length=100)
    category: Category
    description: str
    specifications: dict[str, Any] = Field(default_factory=dict)
    min_rental_days: int = Field(default=1, ge=1)
    max_rental_days: int = Field(default=30, ge=1)

    @model_validator(mode="after")
    def validate_rental_days(self) -> "CreateProductRequest":
        if self.min_rental_days > self.max_rental_days:
            raise ValueError("min_rental_days cannot be greater than max_rental_days")
        return self


class UpdateProductRequest(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    category: Category | None = None
    description: str | None = None
    specifications: dict[str, Any] | None = None
    min_rental_days: int | None = Field(default=None, ge=1)
    max_rental_days: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_update(self) -> "UpdateProductRequest":
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        if (
            self.min_rental_days is not None
            and self.max_rental_days is not None
            and self.min_rental_days > self.max_rental_days
        ):
            raise ValueError("min_rental_days cannot be greater than max_rental_days")

        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    name: str
    brand: str
    category: str
    description: str
    specifications: dict[str, Any]
    min_rental_days: int
    max_rental_days: int
    created_at: datetime
