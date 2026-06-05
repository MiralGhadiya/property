from datetime import datetime, timedelta, timezone

from requests import Session

from app.models.subscription import UserSubscription


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
        except Exception:
            sub.auto_renew = False
            sub.is_active = False
