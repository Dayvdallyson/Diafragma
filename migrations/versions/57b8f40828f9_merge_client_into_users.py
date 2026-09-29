"""merge client into users

Revision ID: 57b8f40828f9
Revises: 7be530ed1719
Create Date: 2026-09-29 06:45:04.683835

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "57b8f40828f9"
down_revision: str | Sequence[str] | None = "7be530ed1719"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROFILE_COLUMNS = (
    "birth_date, country, city, language, document_type, document_number, "
    "document_country, reliability_points"
)


def upgrade() -> None:
    """Upgrade schema."""
    # 1. users gains the profile columns that lived in client
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("country", sa.String(length=2), nullable=True))
    op.add_column("users", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "language", sa.String(length=10), server_default="pt-BR", nullable=False
        ),
    )
    op.add_column(
        "users", sa.Column("document_type", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "users", sa.Column("document_number", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users", sa.Column("document_country", sa.String(length=2), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "reliability_points", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.alter_column(
        "users",
        "name",
        existing_type=sa.VARCHAR(length=120),
        type_=sa.String(length=200),
        nullable=True,
    )
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.String(length=16),
        existing_nullable=True,
    )
    # autogenerate does not detect server_default changes
    op.alter_column("users", "id", server_default=sa.text("uuidv7()"))
    # fix the double prefix produced by the naming convention
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT "
        "ck_users_ck_users_admin_has_credentials TO ck_users_admin_has_credentials"
    )

    # 2. copy clients into users, keeping ids so reservation FKs stay valid
    op.execute(
        f"""
        INSERT INTO users (id, name, role, email, phone, is_active, created_at,
                           {PROFILE_COLUMNS})
        SELECT id, name, 'CUSTOMER', email, phone, true, created_at,
               {PROFILE_COLUMNS}
        FROM client
        """
    )

    # 3. constraints (autogenerate does not detect CHECK constraints)
    op.create_check_constraint(
        op.f("ck_users_has_contact"),
        "users",
        "email IS NOT NULL OR phone IS NOT NULL OR telegram_chat_id IS NOT NULL",
    )
    op.create_check_constraint(
        op.f("ck_users_phone_e164"), "users", r"phone ~ '^\+[1-9][0-9]{7,14}$'"
    )
    op.create_unique_constraint(
        op.f("uq_users_document_country"),
        "users",
        ["document_country", "document_type", "document_number"],
    )

    # 4. reservation.client_id -> reservation.user_id (rename keeps the data)
    op.drop_constraint(
        op.f("fk_reservation_client_id_client"), "reservation", type_="foreignkey"
    )
    op.alter_column("reservation", "client_id", new_column_name="user_id")
    op.create_foreign_key(
        op.f("fk_reservation_user_id_users"),
        "reservation",
        "users",
        ["user_id"],
        ["id"],
    )

    op.drop_table("client")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "client",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("phone", sa.VARCHAR(length=16), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=True),
        sa.Column("birth_date", sa.DATE(), nullable=True),
        sa.Column("email", sa.VARCHAR(length=254), nullable=True),
        sa.Column("country", sa.VARCHAR(length=2), nullable=True),
        sa.Column("city", sa.VARCHAR(length=100), nullable=True),
        sa.Column(
            "language", sa.VARCHAR(length=10), server_default="pt-BR", nullable=False
        ),
        sa.Column("document_type", sa.VARCHAR(length=20), nullable=True),
        sa.Column("document_number", sa.VARCHAR(length=50), nullable=True),
        sa.Column("document_country", sa.VARCHAR(length=2), nullable=True),
        sa.Column(
            "reliability_points", sa.INTEGER(), server_default="0", nullable=False
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            r"phone ~ '^\+[1-9][0-9]{7,14}$'", name=op.f("ck_client_phone_e164")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client")),
        sa.UniqueConstraint(
            "document_country",
            "document_type",
            "document_number",
            name=op.f("uq_client_document_country"),
        ),
        sa.UniqueConstraint("email", name=op.f("uq_client_email")),
        sa.UniqueConstraint("phone", name=op.f("uq_client_phone")),
    )
    # client requires a phone: users without one cannot go back, and any
    # reservation pointing at them will make the FK below fail loudly
    op.execute(
        f"""
        INSERT INTO client (id, name, email, phone, created_at, {PROFILE_COLUMNS})
        SELECT id, name, email, phone, created_at, {PROFILE_COLUMNS}
        FROM users
        WHERE role = 'CUSTOMER' AND phone IS NOT NULL
        """
    )

    op.drop_constraint(
        op.f("fk_reservation_user_id_users"), "reservation", type_="foreignkey"
    )
    op.alter_column("reservation", "user_id", new_column_name="client_id")
    op.create_foreign_key(
        op.f("fk_reservation_client_id_client"),
        "reservation",
        "client",
        ["client_id"],
        ["id"],
    )

    op.drop_constraint(op.f("uq_users_document_country"), "users", type_="unique")
    op.drop_constraint(op.f("ck_users_phone_e164"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_has_contact"), "users", type_="check")
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT "
        "ck_users_admin_has_credentials TO ck_users_ck_users_admin_has_credentials"
    )
    op.alter_column("users", "id", server_default=None)
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=16),
        type_=sa.VARCHAR(length=20),
        existing_nullable=True,
    )
    op.execute("UPDATE users SET name = coalesce(name, email, phone, 'unknown')")
    op.alter_column(
        "users",
        "name",
        existing_type=sa.String(length=200),
        type_=sa.VARCHAR(length=120),
        nullable=False,
    )
    op.drop_column("users", "reliability_points")
    op.drop_column("users", "document_country")
    op.drop_column("users", "document_number")
    op.drop_column("users", "document_type")
    op.drop_column("users", "language")
    op.drop_column("users", "city")
    op.drop_column("users", "country")
    op.drop_column("users", "birth_date")
