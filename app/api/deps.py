from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import User


def get_current_user(
    db: Session = Depends(get_db),
    x_dev_user_email: Annotated[str | None, Header(alias="X-Dev-User-Email")] = None,
    x_dev_display_name: Annotated[str | None, Header(alias="X-Dev-Display-Name")] = None,
) -> User:
    settings = get_settings()
    if settings.auth_mode != "development":
        raise HTTPException(status_code=501, detail="Cognito auth wiring is not implemented yet")

    email = (x_dev_user_email or "demo@giftgen.local").strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=x_dev_display_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif x_dev_display_name and user.display_name != x_dev_display_name:
        user.display_name = x_dev_display_name
        db.commit()
        db.refresh(user)

    return user
