# app/services/aut_service.py

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import RefreshToken, User
from app.utils.logger_config import app_logger as logger


def store_refresh_token(
    db: Session,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
):
    logger.debug(f"Storing refresh token user_id={user_id} expires_at={expires_at}")

    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    try:
        db.add(token)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to store refresh token")
        raise


def revoke_all_refresh_tokens(db: Session, user_id: UUID):
    logger.info(f"Revoking all refresh tokens user_id={user_id}")

    try:
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to revoke refresh tokens")
        raise


def logout_user(db: Session, user_id: UUID):
    logger.info(f"Logging out user user_id={user_id}")

    try:
        user = db.query(User).filter(User.id == user_id).first()
        # if user:
        #     user.is_active = False

        revoke_all_refresh_tokens(db, user_id)
        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Logout failed")
        raise


def revoke_refresh_token(db, user_id: UUID, refresh_token: str, pwd_context):
    tokens = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
        .all()
    )

    try:
        for token in tokens:
            if pwd_context.verify(refresh_token, token.token_hash):
                token.revoked = True
                db.commit()
                return True
    except Exception:
        db.rollback()
        logger.exception("Failed to revoke refresh token")
        raise

    return False


def verify_refresh_token(db, refresh_token: str, pwd_context):
    tokens = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .all()
    )

    for token in tokens:
        if pwd_context.verify(refresh_token, token.token_hash):
            return token

    return None
