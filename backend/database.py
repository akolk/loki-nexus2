from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
import time
from sqlalchemy.exc import OperationalError

# Handle asyncpg vs psycopg2 vs sqlite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./backend/data.db")

# If using sync session/engine (which we are for now mostly), we need sync driver.
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
