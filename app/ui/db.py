"""Database bootstrap for Streamlit."""

from contextlib import contextmanager

from app.database import Base, SessionLocal, engine


def init_database() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
