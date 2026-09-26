from typing import Any, Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

class CreateProductRequest(BaseModel):
    sku: str = Field(max_length=64)
    name: str = Field(max_length=200)
    brand: str = Field(max_length=100)
    category: Literal[
        "camera",
        "lens",
        "lighting",
        "audio",
        "accessory",
    ]
    description: str
    specifications: dict[str, Any] = Field(default_factory=dict)
    min_rental_days: int = Field(default=1, ge=1)
    max_rental_days: int = Field(default=30, ge=1)

    @model_validator(mode="after")
    def validate_rental_days(self):
        if self.max_rental_days < self.min_rental_days:
            raise ValueError(
                "max_rental_days must be greater than or equal to min_rental_days"
            )
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

class UpdateProductRequest(BaseModel):
    sku: str | None = None
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    description: str | None = None
    specification: dict[str, Any] | None = None
    min_rental_days: int | None = None
    max_rental_days: int | None = None
