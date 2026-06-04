# app/deps.py

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models
from app.auth import decode_token
from app.database.db import get_db
from app.models.staff import Staff
from app.utils.logger_config import app_logger as logger


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def _get_access_subject(token: str | None) -> tuple[UUID, dict]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing",
        )

    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
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
        return UUID(sub), payload
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )


def require_management(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    entity_id, payload = _get_access_subject(token)
    role = payload.get("role")

    if not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if role == "admin":
        admin = db.get(models.User, entity_id)

        if not admin or not admin.is_superuser:
            raise HTTPException(status_code=404, detail="Admin not found")

        return admin

    if role == "staff":
        staff = db.get(Staff, entity_id)

        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        return staff

    raise HTTPException(status_code=403, detail="Invalid role")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        user_id, _ = _get_access_subject(token)
    except HTTPException:
        logger.warning("Invalid or expired access token")
        raise

    user = db.get(models.User, user_id)

    if not user:
        logger.warning(f"Authenticated user not found user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

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
    page: int = Query(
        1,
        ge=1,
        description="Page number starting from 1.",
    ),
    limit: int | None = Query(
        50,
        ge=1,
        le=100,
        description="Maximum records to return per page. Set to null only if the route supports unbounded results.",
    ),
    search: str | None = Query(
        None,
        description="Case-insensitive search term applied by the endpoint-specific query logic.",
    ),
    is_active: bool | None = Query(
        None,
        description="Optional active-state filter used by endpoints that support it.",
    ),
):
    return {
        "page": page,
        "limit": limit,
        "search": search,
        "is_active": is_active,
    }
