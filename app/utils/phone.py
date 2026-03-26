import phonenumbers
from phonenumbers.phonenumberutil import (
    region_code_for_country_code,
    region_code_for_number,
    NumberParseException,
)
from app.utils.logger_config import app_logger as logger


def get_country_from_mobile(mobile: str):
    try:
        # Ensure country code is provided (E.164 format)
        if not mobile.startswith("+"):
            raise ValueError("Missing country code. Phone number must start with '+'")

        phone = phonenumbers.parse(mobile, None)

        # Validate phone number
        if not phonenumbers.is_valid_number(phone):
            raise ValueError("Incorrect country code or invalid phone number")

        country_code = region_code_for_number(phone)

        if not country_code:
            country_code = region_code_for_country_code(phone.country_code)

        if not country_code:
            raise ValueError("Incorrect country code")

        dial_code = f"+{phone.country_code}"
        return dial_code, country_code.upper()

    except NumberParseException as e:
        logger.warning(f"Invalid phone number format mobile={mobile}, error={e}")
        raise ValueError("Invalid phone number format") from e

    except ValueError as e:
        logger.warning(f"{e} mobile={mobile}")
        raise
