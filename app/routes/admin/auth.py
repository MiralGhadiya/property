#app/routes/admin/auth.py

from typing import Union
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.models import User, Staff
from app.services import auth_service
from app.schemas import AdminLogin, AdminProfile, ChangePassword
from app.schemas.management import ManagementProfile

from app.deps import get_db, require_management, require_superuser
from app.utils.response import APIResponse, success_response
from app.auth import verify_password, create_access_token, hash_password

from app.utils.logger_config import app_logger as logger


router = APIRouter(
    prefix="/admin",
    tags=["admin-auth"]
)


# @router.post(
#     "/login",
#     response_model=APIResponse[AdminTokenResponse]
# )
# def admin_login(
#     data: AdminLogin,
#     db: Session = Depends(get_db),
# ):
#     logger.info(f"Admin login attempt email={data.email}")

#     user = db.query(User).filter(User.email == data.email).first()

#     if not user or not user.is_superuser:
#         raise HTTPException(status_code=403, detail="Admin access denied")

#     if not verify_password(data.password, user.hashed_password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")

#     if not user.is_active:
#         raise HTTPException(status_code=403, detail="Admin account disabled")

#     access_token = create_access_token(
#         {"sub": str(user.id), "role": "superuser"}
#     )

#     logger.info(f"Admin login successful user_id={user.id}")

#     return success_response(
#         data={
#             "access_token": access_token,
#             "token_type": "bearer",
#         },
#         message="Admin login successful"
#     )


@router.post("/management/login")
def management_login(
    data: AdminLogin,
    db: Session = Depends(get_db),
):
    
    # 1️⃣ Check Admin (superuser)
    admin = db.query(User).filter(
        User.email == data.email,
        User.is_superuser == True
    ).first()

    if admin:
        if not verify_password(data.password, admin.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not admin.is_active:
            raise HTTPException(status_code=403, detail="Admin account disabled")

        access_token = create_access_token(
            {"sub": str(admin.id), "role": "admin"}
        )

        return success_response(
            data={
                "type": "admin",
                "access_token": access_token,
                "token_type": "bearer",
                "profile": {
                    "id": admin.id,
                    "email": admin.email,
                    "username": admin.username,
                }
            },
            message="Admin login successful"
        )

    staff = db.query(Staff).filter(
        Staff.email == data.email
    ).first()

    if staff:
        if not verify_password(data.password, staff.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            {"sub": str(staff.id), "role": "staff"}
        )

        return success_response(
            data={
                "type": "staff",
                "access_token": access_token,
                "token_type": "bearer",
                "profile": {
                    "id": staff.id,
                    "name": staff.name,
                    "email": staff.email,
                    "role": staff.role,
                    "accesses": {
                        "can_access_user": staff.can_access_user,
                        "can_access_staff": staff.can_access_staff,
                        "can_access_dashboard": staff.can_access_dashboard,
                        "can_access_reports": staff.can_access_reports,
                        "can_access_subscriptions_plans": staff.can_access_subscriptions_plans,
                        "can_access_config": staff.can_access_config,
                    }
                }
            },
            message="Staff login successful"
        )

    raise HTTPException(status_code=403, detail="Access denied")
    

@router.get("/management/me")
def management_me(
    current: Union[User, Staff] = Depends(require_management),
):

    if isinstance(current, User):

        return success_response(
            data={
                "type": "admin",
                "id": current.id,
                "email": current.email,
                "username": current.username,
            },
            message="Admin profile fetched successfully"
        )

    if isinstance(current, Staff):

        return success_response(
            data={
                "type": "staff",
                "id": current.id,
                "name": current.name,
                "email": current.email,
                "role": current.role,
                "accesses": {
                    "can_access_user": current.can_access_user,
                    "can_access_staff": current.can_access_staff,
                    "can_access_dashboard": current.can_access_dashboard,
                    "can_access_reports": current.can_access_reports,
                    "can_access_subscriptions_plans": current.can_access_subscriptions_plans,
                    "can_access_config": current.can_access_config,
                }
            },
            message="Staff profile fetched successfully"
        )


# @router.get("/me", response_model=APIResponse[AdminProfile])
# def admin_me(
#     current_admin: User = Depends(require_management),
# ):
#     logger.debug(f"Admin profile fetched user_id={current_admin.id}")
#     return success_response(data=current_admin, message="Admin profile fetched successfully")


@router.post("/logout")
def admin_logout(
    current_admin: User = Depends(require_management),
    db: Session = Depends(get_db),
):
    try:
        auth_service.revoke_all_refresh_tokens(db, current_admin.id)
    except Exception as e:
        logger.exception("Admin logout failed")
        raise HTTPException(500, "Logout failed")

    return success_response(
        data=None,
        message="Admin logged out successfully"
    )


@router.post("/change-password")
def admin_change_password(
    data: ChangePassword,
    current_admin: User = Depends(require_management),
    db: Session = Depends(get_db),
):
    logger.info(f"Admin password change attempt user_id={current_admin.id}")
    
    if data.new_password != data.confirm_password:
        logger.warning(f"Admin password mismatch user_id={current_admin.id}")
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    if not verify_password(
        data.old_password,
        current_admin.hashed_password
    ):
        logger.warning(f"Admin old password incorrect user_id={current_admin.id}")
        raise HTTPException(
            status_code=401,
            detail="Old password is incorrect"
        )

    try:
        current_admin.hashed_password = hash_password(data.new_password)
        db.commit()
    except Exception as e:
        logger.error(f"Error changing admin password user_id={current_admin.id} error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error changing password"
        )
        
    logger.info(f"Admin password changed user_id={current_admin.id}")

    return success_response(
        data=None,
        message="Password changed successfully"
    )
