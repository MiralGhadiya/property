#app/services/country_service.py

from app.models import Country
from sqlalchemy.orm import Session

from app.utils.logger_config import app_logger as logger


def get_country_by_dial_code(db: Session, dial_code: str):
    logger.debug(f"Looking up country by dial_code={dial_code}")

    return db.query(Country).filter(
        Country.dial_code == dial_code
    ).first()


def get_or_create_country_for_phone(
    db: Session,
    dial_code: str,
    country_code: str,
):
    logger.debug(
        "Resolving country from phone "
        f"dial_code={dial_code} country_code={country_code}"
    )

    country = get_country_by_country_code(db, country_code)
    if country:
        return country

    return create_country(
        db,
        name=country_code,
        dial_code=dial_code,
        country_code=country_code,
    )


def create_country(db: Session, name: str, dial_code: str, country_code: str):
    logger.info(
        f"Creating country name={name} dial_code={dial_code} country_code={country_code}"
    )

    country = Country(
        name=name,
        dial_code=dial_code,
        country_code=country_code,
    )
    try:
        db.add(country)
        db.commit()
        db.refresh(country)
    except Exception:
        db.rollback()
        logger.exception("Failed to create country")
        raise

    return country


def get_country_by_country_code(db: Session, country_code: str):
    logger.debug(f"Looking up country by country_code={country_code}")

    return db.query(Country).filter(
        Country.country_code == country_code
    ).first()
