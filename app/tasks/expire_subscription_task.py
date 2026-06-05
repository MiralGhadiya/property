from datetime import datetime, timedelta, timezone

from requests import Session

from app.models.subscription import UserSubscription
from app.utils.logger_config import app_logger as logger


def process_autopay_renewals(db: Session):
    now = datetime.now(timezone.utc)

    subs = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.auto_renew == True,
            UserSubscription.end_date <= now + timedelta(days=1),
            UserSubscription.is_active == True,
        )
        .all()
    )

    for sub in subs:
        try:
            sub.end_date += timedelta(days=30)
        except Exception as exc:
            logger.exception("Failed to auto-renew subscription %s", sub.id)
            sub.auto_renew = False
            sub.is_active = False
