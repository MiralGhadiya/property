import csv
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.auth import pwd_context
from app.database.db import SessionLocal
from app.models import User
from app.models.country import Country
from app.models.subscription_settings import SubscriptionSettings
from app.models.system_config import SystemConfig
from app.scripts.config_seed import load_config_seed_values
from app.services.subscription_service import add_subscription_plans_from_excel
from app.utils.logger_config import app_logger as logger


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUNTRIES_CSV_PATH = PROJECT_ROOT / "data - data.csv.csv"
SUBSCRIPTION_PLANS_XLSX_PATH = PROJECT_ROOT / "subscription_plans.xlsx"

SEEDED_MANAGEMENT_USERS = (
    {
        "email": "superadmin@gmail.com",
        "role": "SUPER_ADMIN",
        "username": "superadmin",
        "password": "superadmin",
        "mobile_number": "+919999000001",
        "country_code": "IN",
        "is_superuser": True,
    },
    {
        "email": "admin@gmail.com",
        "role": "ADMIN",
        "username": "admin",
        "password": "admin",
        "mobile_number": "+919999000002",
        "country_code": "IN",
        "is_superuser": True,
    },
)


def run_setup_step(
    db: Session,
    step_name: str,
    step_function: Callable[..., None],
    *args,
) -> None:
    logger.info(f"Starting setup step: {step_name}")

    try:
        step_function(db, *args)
        db.commit()
        logger.info(f"Completed setup step: {step_name}")
    except Exception:
        db.rollback()
        logger.exception(f"Setup step failed: {step_name}")
        raise


def import_env_variables(db: Session) -> None:
    env_vars = load_config_seed_values()

    for key, value in env_vars.items():
        if value is None:
            continue

        existing = db.query(SystemConfig).filter(
            SystemConfig.config_key == key
        ).first()

        if existing:
            logger.info(f"Skipping existing config: {key}")
            continue

        db.add(SystemConfig(
            config_key=key,
            config_value=value,
        ))

        logger.info(f"Inserted config: {key}")


def import_countries(db: Session, csv_path: Path) -> None:
    try:
        existing_country_codes = {
            country_code
            for (country_code,) in db.query(Country.country_code).all()
            if country_code
        }

        with csv_path.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                country_code = row["country_code"].strip()
                dial_code = row.get("dial_code", "").strip()

                if country_code in existing_country_codes:
                    logger.info(f"Skipping existing country: {country_code}")
                    continue

                db.add(Country(
                    name=row["name"].strip(),
                    country_code=country_code,
                    dial_code=dial_code,
                    currency_code=row.get("currency_code", "").strip() or None,
                ))
                existing_country_codes.add(country_code)

        # SessionLocal is configured with autoflush disabled, so flush here
        # to make newly imported countries visible to subsequent queries.
        db.flush()
        logger.info("Country import completed")

    except Exception as exc:
        raise RuntimeError(f"Country import failed: {exc}") from exc


def setup_subscription_settings(db: Session) -> None:
    existing = db.query(SubscriptionSettings).first()

    if existing:
        logger.info("Subscription settings already exist")
        return

    db.add(SubscriptionSettings(
        id=1,
        subscription_duration_days=365,
    ))

    logger.info("Subscription settings created")


def get_country_by_code(db: Session, country_code: str) -> Country:
    country = db.query(Country).filter(
        Country.country_code == country_code
    ).first()

    if not country:
        raise ValueError(
            f"Country not found for mobile number country code {country_code}"
        )

    return country


def get_existing_management_user(
    db: Session,
    user_data: dict[str, object],
) -> User | None:
    return db.query(User).filter(
        User.email == user_data["email"]
    ).first()


def build_mobile_number_candidate(base_mobile_number: str, offset: int) -> str:
    prefix = "+" if base_mobile_number.startswith("+") else ""
    digits = base_mobile_number.lstrip("+")

    if digits.isdigit():
        return f"{prefix}{int(digits) + offset}"

    return f"{base_mobile_number}_{offset}"


def get_available_mobile_number(
    db: Session,
    requested_mobile_number: str,
) -> str:
    candidate = requested_mobile_number
    attempt = 0

    while True:
        query = db.query(User).filter(User.mobile_number == candidate)

        if not query.first():
            return candidate

        attempt += 1
        candidate = build_mobile_number_candidate(
            requested_mobile_number,
            attempt,
        )


def seed_management_users(db: Session) -> None:
    for user_data in SEEDED_MANAGEMENT_USERS:
        existing_user = get_existing_management_user(db, user_data)

        if existing_user:
            logger.info(
                "Skipping existing management user "
                f"email={user_data['email']} username={user_data['username']}"
            )
            continue

        country = get_country_by_code(db, user_data["country_code"])
        assigned_mobile_number = get_available_mobile_number(
            db,
            user_data["mobile_number"],
        )

        if assigned_mobile_number != user_data["mobile_number"]:
            logger.warning(
                "Configured mobile number for management user is already in use. "
                f"Assigned fallback mobile={assigned_mobile_number} "
                f"email={user_data['email']}"
            )

        db.add(User(
            email=user_data["email"],
            role=user_data["role"],
            username=user_data["username"],
            mobile_number=assigned_mobile_number,
            country_id=country.id,
            hashed_password=pwd_context.hash(user_data["password"]),
            is_active=True,
            is_superuser=user_data["is_superuser"],
            is_email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        ))
        db.flush()

        logger.info(
            "Seeded management user "
            f"email={user_data['email']} role={user_data['role']}"
        )


def import_subscription_plans(db: Session, excel_path: Path) -> None:
    if not excel_path.exists():
        raise FileNotFoundError(
            f"Subscription plans Excel file not found: {excel_path}"
        )

    with excel_path.open("rb") as excel_file:
        created_plans = add_subscription_plans_from_excel(
            db=db,
            file=excel_file,
        )

    if created_plans:
        logger.info(
            "Subscription plans import completed "
            f"created={created_plans}"
        )
    else:
        logger.info("Subscription plans import completed with no new plans created")


def run_setup() -> None:
    db: Session = SessionLocal()

    try:
        logger.info("Running project setup bootstrap")

        run_setup_step(
            db,
            "Import environment variables into system_config",
            import_env_variables,
        )
        run_setup_step(
            db,
            "Import countries into countries table",
            import_countries,
            COUNTRIES_CSV_PATH,
        )
        run_setup_step(
            db,
            "Create subscription settings",
            setup_subscription_settings,
        )
        run_setup_step(
            db,
            "Seed management users into users table",
            seed_management_users,
        )
        run_setup_step(
            db,
            "Import subscription plans from subscription_plans.xlsx",
            import_subscription_plans,
            SUBSCRIPTION_PLANS_XLSX_PATH,
        )

        logger.info("Project setup completed successfully")

    except Exception:
        db.rollback()
        logger.exception("Project setup failed")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    run_setup()
