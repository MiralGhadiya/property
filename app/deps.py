# app/deps.py

from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Query
from uuid import UUID

from typing import Optional
from app import models
from app.models.staff import Staff
from app.database.db import get_db
from app.auth import decode_token
from app.utils.logger_config import app_logger as logger


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def require_management(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing"
        )

    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    sub = payload.get("sub")
    role = payload.get("role")

    if not sub or not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        entity_id = UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if role == "admin":
        admin = db.query(models.User).filter(
            models.User.id == entity_id,
            models.User.is_superuser == True
        ).first()

        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        return admin

    if role == "staff":
        staff = db.query(Staff).filter(
            Staff.id == entity_id
        ).first()

        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        return staff

    raise HTTPException(status_code=403, detail="Invalid role")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        logger.warning("Invalid or expired access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        # ✅ UUID-safe conversion
        user_id = UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        logger.warning(f"Authenticated user not found user_id={user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_email_verified:
        logger.warning(f"Unverified email access blocked user_id={user.id}")
        raise HTTPException(status_code=403, detail="Email not verified")

    if not user.is_active:
        logger.warning(f"Inactive user access blocked user_id={user.id}")
        raise HTTPException(status_code=401, detail="User inactive")

    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:

    if not token:
        return None

    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


def require_superuser(
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_superuser:
        logger.warning(f"Superuser access denied user_id={current_user.id}")
        raise HTTPException(
            status_code=403,
            detail="Superuser access required",
        )
    return current_user


def pagination_params(
    page: int = Query(1, ge=1),
    limit: int = Query(10000, ge=1),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
):
    return {
        "page": page,
        "limit": limit,
        "search": search,
        "is_active": is_active,
    }

