from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .base import engine

SessionLocal = sessionmaker(
  bind=engine,
  autoflush=False,
  expire_on_commit=False
)
