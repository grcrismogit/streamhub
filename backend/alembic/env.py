"""Configuración de Alembic: usa la misma URL y metadatos que la app."""

from alembic import context
from sqlalchemy import pool

from app.core.config import get_settings
from app.models import Base

config = context.config
target_metadata = Base.metadata
url = get_settings().sqlalchemy_url


def run_migrations_offline() -> None:
    context.configure(url=str(url), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
