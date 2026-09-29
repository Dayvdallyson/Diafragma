from datetime import datetime
from typing import Annotated
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, String, func, text
from sqlalchemy.orm import mapped_column

UuidPk = Annotated[
    UUID, mapped_column(primary_key=True, server_default=text("uuidv7()"))
]
CreatedAt = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now())
]
Timestamp = Annotated[datetime, mapped_column(DateTime(timezone=True))]
CountryCode = Annotated[str, mapped_column(String(2))]
CurrencyCode = Annotated[str, mapped_column(String(3))]
Cents = Annotated[int, mapped_column(BigInteger)]


def one_of(column: str, values: list[str]) -> str:
    options = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({options})"
