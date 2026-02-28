from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
import time
from sqlalchemy.exc import OperationalError

# Handle postgres via standard env variables or fallback to sqlite
PG_USER = os.environ.get("POSTGRES_USER")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
PG_HOST = os.environ.get("POSTGRES_HOST")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_DB = os.environ.get("POSTGRES_DB")

# Construct DATABASE_URL if all Postgres variables are provided
if all([PG_USER, PG_PASSWORD, PG_HOST, PG_DB]):
    DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
else:
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./backend/data.db")

# If env var is `postgresql+asyncpg`, strip `+asyncpg`.
if "postgresql+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    retries = 10
    while retries > 0:
        try:
            SQLModel.metadata.create_all(engine)
            print("Database initialized.")
            return
        except OperationalError:
            print("Waiting for database...")
            time.sleep(2)
            retries -= 1
    print("Failed to initialize database.")

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
