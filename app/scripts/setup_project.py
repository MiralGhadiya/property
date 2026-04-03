import csv
import os
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.database.db import Base, SessionLocal, engine
from app.models.country import Country
from app.models.subscription_settings import SubscriptionSettings
from app.models.system_config import SystemConfig
from app.scripts.config_seed import load_config_seed_values
from app.services.bootstrap_service import ensure_default_superusers
from app.services.subscription_service import add_subscription_plans_from_excel
from app.utils.logger_config import app_logger as logger


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUNTRIES_CSV_PATH = PROJECT_ROOT / "data - data.csv.csv"
SUBSCRIPTION_PLANS_XLSX_PATH = PROJECT_ROOT / "subscription_plans.xlsx"


def ensure_database_schema() -> None:
    if os.getenv("ENV") != "production":
        Base.metadata.create_all(bind=engine)


def run_setup_step(
    db: Session,
    step_name: str,
    step_function: Callable[..., None],
    *args,
) -> None:
    logger.info("Starting setup step: %s", step_name)

    try:
        step_function(db, *args)
        db.commit()
        logger.info("Completed setup step: %s", step_name)
    except Exception:
        db.rollback()
        logger.exception("Setup step failed: %s", step_name)
        raise


def import_env_variables(db: Session) -> None:
    env_vars = load_config_seed_values()

    for key, value in env_vars.items():
        existing = (
            db.query(SystemConfig)
            .filter(SystemConfig.config_key == key)
            .first()
        )

        if existing:
            logger.info("Skipping existing config: %s", key)
            continue

        db.add(
            SystemConfig(
                config_key=key,
                config_value=value,
            )
        )
        logger.info("Inserted config: %s", key)


def import_countries(db: Session, csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"Countries file not found: {csv_path}")

    existing_country_codes = {
        country_code
        for (country_code,) in db.query(Country.country_code).all()
        if country_code
    }

    with csv_path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            country_code = row["country_code"].strip()

            if country_code in existing_country_codes:
                logger.info("Skipping existing country: %s", country_code)
                continue

            db.add(
                Country(
                    name=row["name"].strip(),
                    country_code=country_code,
                    dial_code=row.get("dial_code", "").strip() or None,
                    currency_code=row.get("currency_code", "").strip() or None,
                )
            )
            existing_country_codes.add(country_code)

    db.flush()
    logger.info("Country import completed")


def setup_subscription_settings(db: Session) -> None:
    existing = db.query(SubscriptionSettings).first()

    if existing:
        logger.info("Subscription settings already exist")
        return

    db.add(
        SubscriptionSettings(
            id=1,
            subscription_duration_days=365,
        )
    )
    logger.info("Subscription settings created")


def seed_default_superusers(db: Session) -> None:
    result = ensure_default_superusers(db)
    logger.info(
        "Default superusers ensured created=%s skipped=%s",
        result["created"],
        result["skipped"],
    )


def import_subscription_plans(db: Session, excel_path: Path) -> None:
    if not excel_path.exists():
        logger.warning(
            "Subscription plans Excel file not found. Skipping bootstrap: %s",
            excel_path,
        )
        return

    with excel_path.open("rb") as excel_file:
        created_plans = add_subscription_plans_from_excel(
            db=db,
            file=excel_file,
        )

    if created_plans:
        logger.info(
            "Subscription plans import completed created=%s",
            created_plans,
        )
    else:
        logger.info("Subscription plans import completed with no new plans created")


def run_setup() -> None:
    ensure_database_schema()
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
            "Seed default superusers into users table",
            seed_default_superusers,
        )
        run_setup_step(
            db,
            "Import subscription plans into subscription_plans table",
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
