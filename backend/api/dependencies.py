from fastapi import Depends, Header
from sqlmodel import Session, select
from typing import Tuple
import logging

from backend.database import engine
from backend.models import User, Soul

logger = logging.getLogger(__name__)


def get_session():
    with Session(engine) as session:
        yield session


def get_current_user(
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session),
) -> Tuple[User, Soul]:
    statement = select(User).where(User.username == x_forwarded_user)
    results = session.exec(statement)
    user = results.first()

    if not user:
        user = User(
            username=x_forwarded_user, soul_data={"style": "concise", "preferences": {}}
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    soul = Soul(
        user_id=str(user.id),
        username=user.username,
        preferences=user.soul_data.get("preferences", {}),
        style=user.soul_data.get("style", "concise"),
    )
    return user, soul
