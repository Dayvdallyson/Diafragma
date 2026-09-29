import argparse
from getpass import getpass

from sqlalchemy import select

from diafragma.auth.security import hash_password
from diafragma.db.session import SessionLocal
from diafragma.models.users.models import User, UserRole

MIN_PASSWORD_LENGTH = 12


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("email")
    parser.add_argument("name")
    args = parser.parse_args()
    email = args.email.strip().lower()

    password = getpass("Senha: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")

    with SessionLocal() as session:
        if session.scalar(select(User).where(User.email == email)):
            raise SystemExit(f"A user with email {email} already exists")

        session.add(
            User(
                name=args.name,
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
            )
        )

        session.commit()

    print(f"Admin {email} created.")
