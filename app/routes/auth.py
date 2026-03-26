# app/routes/auth.py
import os
import secrets
from sqlalchemy import desc
from app.auth import pwd_context
from sqlalchemy.orm import Session


from google.oauth2 import id_token
from google.auth.transport import requests

from dotenv import load_dotenv

from app.core.config_manager import get_config
load_dotenv()

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.ip_country import get_client_ip, get_ip_country

from app.utils.phone import get_country_from_mobile
from app.utils.email import send_reset_email, send_verification_email

from app.deps import get_db, get_current_user
from app.auth import verify_password, create_access_token, create_refresh_token

from app import schemas

from app.services import user_service, country_service, auth_service

from app.models import EmailVerificationToken, User, SubscriptionPlan, UserSubscription, PasswordResetToken

from app.utils.logger_config import app_logger as logger

# BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
def get_base_url():
    return get_config("BASE_URL", "http://localhost:8000")

datetime.now(timezone.utc)

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def verify_google_token(token: str):
    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            # os.getenv("GOOGLE_CLIENT_ID")
            get_config("GOOGLE_CLIENT_ID"),
            clock_skew_in_seconds=10  
        )
        return payload
    except Exception as e:
        print("Google verification error:", e)
        return None


@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):

    if user.email and user_service.get_user_by_email(db, user.email):
        raise HTTPException(400, "Email already registered")

    if user_service.get_user_by_mobile(db, user.mobile_number):
        raise HTTPException(400, "Mobile number already registered")

    try:
        dial_code, country_code = get_country_from_mobile(user.mobile_number)
    except ValueError as e:
    # This will show exact phone validation error to user
        raise HTTPException(status_code=400, detail=str(e))

    try:
        country = country_service.get_or_create_country_for_phone(
            db,
            dial_code=dial_code,
            country_code=country_code,
        )

        new_user = user_service.create_user(
            db,
            email=user.email,
            username=user.username,
            role=user.role,
            mobile_number=user.mobile_number,
            password=user.password,
            country_id=country.id,
        )

        free_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.name == "FREE",
            SubscriptionPlan.country_code == country.country_code,
            SubscriptionPlan.is_active == True
        ).first()

        if free_plan:
            db.add(UserSubscription(
                user_id=new_user.id,
                plan_id=free_plan.id,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(days=365),
                is_active=True
            ))

        raw_token = secrets.token_urlsafe(48)
        verification = EmailVerificationToken(
            user_id=new_user.id,
            token_hash=pwd_context.hash(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(verification)

        db.commit()
        
        try:
            send_verification_email(
                new_user.email,
                f"{get_base_url()}/verify-email?token={raw_token}"
            )
        except Exception:
            logger.exception("Failed to send verification email")

        return {"message": "Registration successful. Please verify your email."}

    except Exception:
        db.rollback()
        logger.exception("Registration failed")
        raise HTTPException(500, "Registration failed")


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    success = False
    message = "Invalid or expired verification link"

    tokens = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.used == False,
        EmailVerificationToken.expires_at > datetime.now(timezone.utc)
    ).all()

    verification = next(
        (t for t in tokens if pwd_context.verify(token, t.token_hash)),
        None
    )

    if verification:
        user = db.query(User).filter(User.id == verification.user_id).first()
        try:
            user.is_email_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            verification.used = True
            db.commit()
            success = True
            message = "Your email has been verified successfully."
        except Exception:
            db.rollback()
            logger.exception("Email verification failed")

    return templates.TemplateResponse(
        "emails/verify_email.html",
        {
            "request": request,
            "success": success,
            "message": message,
            # "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:3000")
            "frontend_url": get_config("FRONTEND_URL", "http://localhost:3000")
        }
    )


@router.get("/resend-verification-page", response_class=HTMLResponse)
def resend_verification_page(request: Request):
    return templates.TemplateResponse(
        "emails/resend_verification.html",
        {"request": request}
    )
    

@router.post("/resend-verification")
def resend_verification_email(
    data: schemas.ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        return {
            "message": "If this email is registered, a verification link has been sent"
        }

    if user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="Email is already verified"
        )

    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used == False,
    ).update({"used": True}, synchronize_session=False)

    raw_token = secrets.token_urlsafe(48)
    hashed_token = pwd_context.hash(raw_token)

    verification = EmailVerificationToken(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    
    try:
        db.add(verification)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to create email verification token")
        raise HTTPException(500, "Failed to resend verification email")

    verify_link = f"{get_base_url()}/verify-email?token={raw_token}"
    send_verification_email(user.email, verify_link)

    logger.info(f"Verification email resent user_id={user.id}")

    return {
        "message": "Verification email sent successfully"
    }


# @router.get("/verify-email-page", response_class=HTMLResponse)
# def verify_email_page(
#     token: str,
#     request: Request,
#     db: Session = Depends(get_db)
# ):
#     success = False
#     message = "Invalid or expired verification link"

#     tokens = db.query(EmailVerificationToken).filter(
#         EmailVerificationToken.used == False,
#         EmailVerificationToken.expires_at > datetime.now(timezone.utc)
#     ).all()

#     verification = next(
#         (t for t in tokens if pwd_context.verify(token, t.token_hash)),
#         None
#     )

#     if verification:
#         user = db.query(User).filter(User.id == verification.user_id).first()

#         try:
#             user.is_email_verified = True
#             user.email_verified_at = datetime.now(timezone.utc)
#             verification.used = True
#             db.commit()
#             success = True
#             message = "Email verified successfully"
#         except Exception:
#             db.rollback()
#             logger.exception("Email verification failed")

#     return templates.TemplateResponse(
#         "verify_email.html",
#         {
#             "request": request,
#             "success": success,
#             "message": message,
#             "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:8000")
#         }
#     )


@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):

    try:
        db_user = user_service.get_user_by_email(db, user.email)
        
        if db_user and db_user.provider != "LOCAL":
            raise HTTPException(
                status_code=400,
                detail="This account uses Google login"
            )

        if not db_user:
            logger.info(f"Login failed: user not found email={user.email}")
            raise HTTPException(401, "Invalid credentials")

        if not verify_password(user.password, db_user.hashed_password):
            logger.info(f"Login failed: invalid password email={user.email}")
            raise HTTPException(401, "Invalid credentials")

        if not db_user.is_active:
            raise HTTPException(403, "Account is inactive")

        if not db_user.is_email_verified:
            raise HTTPException(403, "Please verify your email")

        access_token = create_access_token({"sub": str(db_user.id)})
        refresh_token = create_refresh_token({"sub": str(db_user.id)})

        auth_service.store_refresh_token(
            db,
            db_user.id,
            pwd_context.hash(refresh_token),
            datetime.now(timezone.utc) + timedelta(days=7),
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Login failed")
        raise HTTPException(500, "Login failed")


@router.post("/google")
def google_login(
    request: Request,
    data: schemas.GoogleLogin,
    db: Session = Depends(get_db),
):
    payload = verify_google_token(data.id_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = payload.get("email")
    google_id = payload.get("sub")
    name = payload.get("name", "User")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # existing_user = db.query(User).filter(User.email == email).first()
    # if existing_user:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="This email is already registered"
    #     )

    user = db.query(User).filter(
        User.provider == "GOOGLE",
        User.provider_id == google_id
    ).first()

    country_id = None
    client_ip = get_client_ip(request)
    print(f"Client IP: {client_ip}")

    country_code = get_ip_country(client_ip)
    print(f"Country code from IP: {country_code}")

    if country_code:
        country = country_service.get_country_by_country_code(db, country_code)
        print(f"Country from DB: {country}")

        if not country:
            country = country_service.create_country(
                db,
                name=country_code,  
                dial_code=None,        
                country_code=country_code
            )
            print(f"Created new country: {country}")

        country_id = country.id

    if not user:
        user = User(
            email=email,
            username=name,
            mobile_number=f"google_{google_id[:10]}",
            country_id=country_id,
            hashed_password="GOOGLE_AUTH",
            provider="GOOGLE",
            provider_id=google_id,
            is_email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    auth_service.store_refresh_token(
        db,
        user.id,
        pwd_context.hash(refresh_token),
        datetime.now(timezone.utc) + timedelta(days=7),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

   
@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(
    data: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Rotate refresh token and issue new access token
    """

    token_record = auth_service.verify_refresh_token(
        db=db,
        refresh_token=data.refresh_token,
        pwd_context=pwd_context,
    )

    if not token_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )
    
    try:

        token_record.is_revoked = True

        access_token = create_access_token(
            {"sub": str(token_record.user_id)}
        )
        new_refresh_token = create_refresh_token(
            {"sub": str(token_record.user_id)}
        )

        auth_service.store_refresh_token(
            db=db,
            user_id=token_record.user_id,
            token_hash=pwd_context.hash(new_refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Refresh token rotation failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to rotate refresh token"
        )

    logger.info(
        f"Refresh token rotated user_id={token_record.user_id}"
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
    }

    
@router.get("/profile", response_model=schemas.UserProfile)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    latest_sub = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == current_user.id,
            # UserSubscription.payment_status == "PAID",
            UserSubscription.is_active == True,
            UserSubscription.is_expired == False,
        )
        .order_by(desc(UserSubscription.start_date))   # latest purchased
        .first()
    )

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "mobile_number": current_user.mobile_number,
        "country": current_user.country.name if current_user.country else None,
        "role": current_user.role,
        "subscription_id": latest_sub.id if latest_sub else None,
        "plan_name": latest_sub.plan.name if latest_sub else None,
        "has_active_subscription": bool(latest_sub),
    }
    
 
@router.put("/edit-profile")
def update_profile(
    data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    if data.email and data.email != current_user.email:
        existing_email = user_service.get_user_by_email(db, data.email)
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already in use"
            )
        current_user.email = data.email
        current_user.is_email_verified = False  # re-verify if email changes

    if data.mobile_number and data.mobile_number != current_user.mobile_number:
        existing_mobile = user_service.get_user_by_mobile(db, data.mobile_number)
        if existing_mobile:
            raise HTTPException(
                status_code=400,
                detail="Mobile number already in use"
            )
        current_user.mobile_number = data.mobile_number

    if data.username:
        current_user.username = data.username

    try:
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        logger.exception("Profile update failed")
        raise HTTPException(status_code=500, detail="Failed to update profile")

    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "mobile_number": current_user.mobile_number
        }
    }
       
    
@router.post("/change-password")
def change_password(
    data: schemas.ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    try:
        user_service.change_password(
            db, current_user, data.old_password, data.new_password
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(
    data: schemas.ForgotPassword,
    db: Session = Depends(get_db)
):
    
    user = user_service.get_user_by_email(db, data.email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="This email is not registered. Please enter your registered email id"
        )

    raw_token = secrets.token_urlsafe(48)
    hashed_token = pwd_context.hash(raw_token)

    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    try:
        db.add(reset)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to create password reset token")
        raise HTTPException(500, "Failed to initiate password reset")

    reset_link = f"{get_base_url()}/reset-password?token={raw_token}"
    
    send_reset_email(user.email, reset_link)

    logger.info(f"Password reset requested for email={user.email}")

    return {
        "message": "If email is registered, a password reset link has been sent. Please check your inbox."
    }


@router.post("/reset-password")
def reset_password(
    data: schemas.ResetPassword,
    db: Session = Depends(get_db)
):

    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc)
    ).all()

    reset_token = next(
        (t for t in tokens if pwd_context.verify(data.token, t.token_hash)),
        None
    )

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    
    try:
        user.hashed_password = pwd_context.hash(data.new_password)
        reset_token.used = True
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Password reset failed")
        raise HTTPException(status_code=500, detail="Password reset failed")

    return {"message": "Password reset successful"}


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request}
    )


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout user from ALL devices (revoke all refresh tokens)
    """
    try:    
        auth_service.logout_user(db, current_user.id)

        logger.info(f"User logout user_id={current_user.id}")

        return {"message": "Logged out successfully"}
    except Exception:
        logger.exception(f"Logout failed user_id={current_user.id}")
        raise HTTPException(500, "Logout failed")
    
    
# @router.post("/staff/login", response_model=APIResponse[dict])
# def staff_login(
#     data: StaffLogin,
#     db: Session = Depends(get_db),
# ):
#     staff_member = db.query(Staff).filter(Staff.email == data.email).first()

#     if not staff_member or not verify_password(data.password, staff_member.password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")

#     user = db.query(User).filter(User.id == staff_member.user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     access_token = create_access_token({"sub": str(user.id)})
#     refresh_token = create_refresh_token({"sub": str(user.id)})

#     auth_service.store_refresh_token(
#         db,
#         user.id,
#         pwd_context.hash(refresh_token),
#         datetime.now(timezone.utc) + timedelta(days=7),
#     )

#     return success_response(
#         data={
#             "access_token": access_token,
#             "refresh_token": refresh_token,
#             "token_type": "bearer",
#             "user": {
#                 "id": staff_member.id,
#                 "name": staff_member.name,
#                 "email": staff_member.email,
#                 "phone": staff_member.phone,
#                 "role": staff_member.role,
#                 "accesses": {
#                     "can_access_user": staff_member.can_access_user,
#                     "can_access_staff": staff_member.can_access_staff,
#                     "can_access_dashboard": staff_member.can_access_dashboard,
#                     "can_access_reports": staff_member.can_access_reports,
#                     "can_access_subscriptions_plans": staff_member.can_access_subscriptions_plans,
#                 },
#             },
#         },
#         message="Staff login successful"
#     )
