# app/services/user_service.py

from app.models import User
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password

from app.utils.logger_config import app_logger as logger


def get_user_by_username(db: Session, username: str):
    logger.debug(f"Fetching user by username={username}")
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    logger.debug(f"Fetching user by email={email}")
    return db.query(User).filter(User.email == email).first()


def get_user_by_mobile(db: Session, mobile_number: str):
    logger.debug(f"Fetching user by mobile_number={mobile_number}")
    return db.query(User).filter(
        User.mobile_number == mobile_number
    ).first()


def create_user(
    db: Session,
    email: str,
    username: str,
    mobile_number: str,
    password: str,
    country_id: int,
    role: str
):
    logger.info(
        f"Creating user username={username} "
        f"email={email} mobile={mobile_number}"
    )
    user = User(
        email=email,
        username=username,
        mobile_number=mobile_number,
        country_id=country_id,
        role=role,
        hashed_password=hash_password(password),
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception("Failed to create user")
        raise
    
    logger.info(f"User created user_id={user.id}")
    return user


def change_password(db: Session, user: User, old_password: str, new_password: str):
    logger.info(f"Changing password user_id={user.id}")
    
    if not verify_password(old_password, user.hashed_password):
        logger.warning(f"Invalid old password user_id={user.id}")
        raise ValueError("Invalid password")

    try:
        user.hashed_password = hash_password(new_password)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to change password")
        raise