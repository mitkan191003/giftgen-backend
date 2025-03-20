from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.services.cognito import (
    CognitoAuthenticationError,
    CognitoConfigurationError,
    get_cognito_verifier,
)


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_dev_user_email: Annotated[str | None, Header(alias="X-Dev-User-Email")] = None,
    x_dev_display_name: Annotated[str | None, Header(alias="X-Dev-Display-Name")] = None,
) -> User:
    settings = get_settings()
    if settings.auth_mode == "cognito":
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.split(" ", 1)[1].strip()
        try:
            identity = get_cognito_verifier().verify(token)
        except CognitoConfigurationError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except CognitoAuthenticationError as exc:
            raise HTTPException(
                status_code=401,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = db.scalar(select(User).where(User.auth_subject == identity.subject))
        if user is None:
            user = db.scalar(select(User).where(User.email == identity.email))
            if user is not None and user.auth_subject and user.auth_subject != identity.subject:
                raise HTTPException(status_code=409, detail="Email is already linked to another identity")

        if user is None:
            user = User(
                email=identity.email,
                auth_subject=identity.subject,
                display_name=identity.display_name,
                auth_provider="cognito",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

        changed = False
        if user.auth_subject != identity.subject:
            user.auth_subject = identity.subject
            changed = True
        if user.email != identity.email:
            user.email = identity.email
            changed = True
        if identity.display_name and user.display_name != identity.display_name:
            user.display_name = identity.display_name
            changed = True
        if user.auth_provider != "cognito":
            user.auth_provider = "cognito"
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user

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
