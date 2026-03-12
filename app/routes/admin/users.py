#app/router/admin/users.py

import os
import secrets
from uuid import UUID
from sqlalchemy import or_
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import hash_password, pwd_context
from app.deps import pagination_params, get_db, require_management

from app.models import User, EmailVerificationToken
from app.services import auth_service, country_service

from app.schemas.admin import AdminCreateUser, AdminUserUpdate
from app.schemas import AdminUserResponse, AdminResetPassword

from app.common import PaginatedResponse

from app.utils.email import send_verification_email
from app.utils.phone import get_country_from_mobile
from app.utils.date_filters import filter_by_date_range
from app.utils.response import APIResponse, success_response

from app.core.config_manager import get_config

from app.utils.logger_config import app_logger as logger


router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"]
)

# BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
def get_base_url():
    return get_config("BASE_URL", "http://localhost:8000")

USER_NOT_FOUND = "User not found"

@router.get("", response_model=APIResponse[PaginatedResponse[AdminUserResponse]])
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_management),  
    params: dict = Depends(pagination_params),
    is_email_verified: Optional[bool] = Query(None),
    is_superuser: Optional[bool] = Query(None),
    country_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    verified_from: Optional[datetime] = Query(None),
    verified_to: Optional[datetime] = Query(None),
    verified_within_days: Optional[int] = Query(
        None, ge=1, le=365, description="Email verified within last N days"
    ),
    sort_by: str = Query("id"),
    order: str = Query("desc"),
):
    logger.info(
        "Admin listing users "
        f"page={params['page']} limit={params['limit']} "
        f"search={params['search']}"
    )
    
    query = db.query(User)
    
    if params["search"]:
        query = query.filter(
            or_(
                User.username.ilike(f"%{params['search']}%"),
                User.email.ilike(f"%{params['search']}%"),
                User.mobile_number.ilike(f"%{params['search']}%"),
            )
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if is_email_verified is not None:
        query = query.filter(User.is_email_verified == is_email_verified)

    if is_superuser is not None:
        query = query.filter(User.is_superuser == is_superuser)

    if country_id:
        query = query.filter(User.country_id == country_id)

    if verified_within_days:
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=verified_within_days)

        query = query.filter(
            User.email_verified_at.isnot(None),
            User.email_verified_at >= start_date,
        )

    else:
        if verified_from or verified_to:
            query = query.filter(
                User.email_verified_at.isnot(None)
            )

            query = filter_by_date_range(
                query,
                User.email_verified_at,
                verified_from,
                verified_to,
            )

    total = query.count()

    ALLOWED_SORT_FIELDS = {
        "id": User.id,
        "email": User.email,
        "username": User.username,
        "email_verified_at": User.email_verified_at,
    }

    sort_column = ALLOWED_SORT_FIELDS.get(sort_by)
    if not sort_column:
        raise HTTPException(400, "Invalid sort field")

    if order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    if params["limit"] is not None:
        query = query.offset((params["page"] - 1) * params["limit"]).limit(params["limit"])
    
    users = query.all()

    logger.debug(
        f"Admin fetched users count={len(users)} total={total}"
    )

    return success_response(
    data={
            "data": users,
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            }
        },
        message="User list fetched successfully"
    )
    

@router.get("/{user_id}", response_model=APIResponse[AdminUserResponse])
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_management),
):
    logger.info(f"Admin fetching user user_id={user_id}")
    
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        logger.warning(f"{USER_NOT_FOUND} user_id={user_id}")
        raise HTTPException(404, USER_NOT_FOUND)

    return success_response(
        data=user,
        message="User fetched successfully"
    )


@router.post("", response_model=APIResponse[AdminUserResponse])
def create_user(
    data: AdminCreateUser,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    logger.info(f"Admin creating user email={data.email}")

    # Check existing email
    if data.email:
        existing_email = db.query(User).filter(
            User.email == data.email
        ).first()

        if existing_email:
            raise HTTPException(400, "Email already in use")

    # Check existing mobile
    existing_mobile = db.query(User).filter(
        User.mobile_number == data.mobile_number
    ).first()

    if existing_mobile:
        raise HTTPException(400, "Mobile number already in use")

    # Detect country from mobile
    # dial_code, country_code = get_country_from_mobile(data.mobile_number)
    try:
        dial_code, country_code = get_country_from_mobile(data.mobile_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    country = country_service.get_country_by_dial_code(db, dial_code)
    if not country:
        country = country_service.create_country(
            db,
            name=country_code,
            dial_code=dial_code,
            country_code=country_code
        )

    # Create user
    new_user = User(
        username=data.username,
        email=data.email,
        mobile_number=data.mobile_number,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_superuser=data.is_superuser,
        country_id=country.id,
        is_active=True,
        is_email_verified=True,   # ✅ directly verified
        email_verified_at=datetime.now(timezone.utc),  # ✅ set timestamp
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        logger.exception("Failed to create user")
        raise HTTPException(500, "User creation failed")

    return success_response(
        data=new_user,
        message="User created successfully"
    )
    

@router.patch("/{user_id}", response_model=APIResponse[AdminUserResponse])
def update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    logger.info(f"Admin updating user user_id={user_id}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, USER_NOT_FOUND)

    if data.username and data.username != user.username:
        user.username = data.username

    if data.email and data.email != user.email:
        existing_email = db.query(User).filter(
            User.email == data.email,
            User.id != user.id
        ).first()

        if existing_email:
            raise HTTPException(400, "Email already in use")

        # Update email + reset verification
        user.email = data.email
        user.is_email_verified = False
        user.email_verified_at = None

        # Invalidate old verification tokens
        db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used == False
        ).update({"used": True})

        # Create new verification token
        raw_token = secrets.token_urlsafe(48)
        verification = EmailVerificationToken(
            user_id=user.id,
            token_hash=pwd_context.hash(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(verification)

        # Send verification email
        try:
            send_verification_email(
                user.email,
                f"{get_base_url()}/verify-email?token={raw_token}"
            )
        except Exception:
            logger.exception(
                f"Failed to send verification email after admin update user_id={user.id}"
            )

    if data.mobile_number and data.mobile_number != user.mobile_number:
        existing_mobile = db.query(User).filter(
            User.mobile_number == data.mobile_number,
            User.id != user.id
        ).first()

        if existing_mobile:
            raise HTTPException(400, "Mobile number already in use")

        user.mobile_number = data.mobile_number

        # dial_code, country_code = get_country_from_mobile(data.mobile_number)
        try:
            dial_code, country_code = get_country_from_mobile(data.mobile_number)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        country = country_service.get_country_by_dial_code(db, dial_code)
        if not country:
            country = country_service.create_country(
                db,
                name=country_code,
                dial_code=dial_code,
                country_code=country_code
            )

        user.country_id = country.id

    if data.role and data.role != user.role:
        user.role = data.role

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception("Failed to update user")
        raise HTTPException(500, "User update failed")

    return success_response(
        data=user,
        message="User updated successfully"
    )


@router.patch("/{user_id}/toggle-active", response_model=APIResponse[dict])
def toggle_user_active(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    logger.info(f"Admin toggling user active state user_id={user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.warning(f"{USER_NOT_FOUND} during toggle user_id={user_id}")
        raise HTTPException(404, USER_NOT_FOUND)

    try:
        user.is_active = not user.is_active
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to toggle user active state")
        raise HTTPException(500, "Update failed")

    if not user.is_active:
        logger.info(f"User deactivated and sessions revoked user_id={user.id}")
        auth_service.revoke_all_refresh_tokens(db, user.id)
    else:
        logger.info(f"User activated user_id={user.id}")

    return success_response(
        data={
            "is_active": user.is_active
        },
        message="User active state updated successfully"
    )
    

@router.post("/{user_id}/logout")
def force_logout_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    logger.info(f"Admin forcing logout user_id={user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.warning(f"{USER_NOT_FOUND} during force logout user_id={user_id}")
        raise HTTPException(404, USER_NOT_FOUND)

    auth_service.revoke_all_refresh_tokens(db, user.id)
    
    logger.info(f"User logged out from all sessions user_id={user.id}")

    return {
        "success": True,
        "message":"User logged out from all sessions"
    }


@router.post("/{user_id}/verify-email")
def verify_user_email(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    logger.info(f"Admin verifying email user_id={user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.warning(f"{USER_NOT_FOUND} during email verify user_id={user_id}")
        raise HTTPException(404, USER_NOT_FOUND)

    if user.is_email_verified:
        logger.info(f"Email already verified user_id={user_id}")
        return {
            "success": False,
            "message": "User email is already verified"
        }
    
    try:
        user.is_email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to verify user email")
        raise HTTPException(500, "Email verification failed")
    
    logger.info(f"User email verified user_id={user_id}")

    return {
        "success": True,
        "message": "User email verified successfully"
    }


@router.post("/{user_id}/reset-password", response_model=APIResponse[dict])
def admin_reset_password(
    user_id: UUID,
    data: AdminResetPassword,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    logger.info(f"Admin resetting password user_id={user_id}")
    
    if data.new_password != data.confirm_password:
        logger.warning(f"Password mismatch during reset user_id={user_id}")
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.warning(f"{USER_NOT_FOUND} during password reset user_id={user_id}")
        raise HTTPException(404, USER_NOT_FOUND)
    
    try:
        user.hashed_password = hash_password(data.new_password)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to reset user password")
        raise HTTPException(500, "Password reset failed")

    auth_service.revoke_all_refresh_tokens(db, user.id)
    
    logger.info(f"User password reset and sessions revoked user_id={user.id}")

    return success_response(
        data={},
        message="User password reset successfully"
    )