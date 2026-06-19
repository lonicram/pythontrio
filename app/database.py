"""SQLAlchemy database engine and session configuration."""

import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

connect_args: dict[str, bool] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)


@event.listens_for(engine, "before_cursor_execute")
def log_sql(
    conn: Connection,
    cursor: object,
    statement: str,
    parameters: object,
    context: object,
    executemany: bool,
) -> None:
    logger.info("SQL: %s | params: %s", statement, parameters)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def get_db() -> Iterator[Session]:
    """Dependency that provides a database session.

    Yields:
        Session: A SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
