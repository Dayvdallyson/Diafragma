from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diafragma.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
