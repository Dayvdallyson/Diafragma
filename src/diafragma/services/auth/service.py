from sqlalchemy import select
from sqlalchemy.orm import Session

from diafragma.auth.security import DUMMY_HASH, verify_password
from diafragma.models.users.models import User


def authenticate_user(email: str, password: str, session: Session) -> User | None:
    user = session.scalar(select(User).where(User.email == email.strip().lower()))

    if user is None or user.hashed_password is None:
        verify_password(password, DUMMY_HASH)
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user
