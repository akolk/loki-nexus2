from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# Default to SQLite for local development, but use DATABASE_URL if available (e.g. Postgres)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./backend/data.db")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
