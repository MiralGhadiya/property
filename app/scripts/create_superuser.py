from getpass import getpass

from dotenv import load_dotenv

from app.auth import pwd_context
from app.database.db import SessionLocal
from app.models import Country, User
from app.utils.phone import get_country_from_mobile

load_dotenv()


def create_superuser():
    db = SessionLocal()

    try:
        print("=== Create Superuser ===")

        email = input("Email: ").strip().lower()
        username = input("Username: ").strip()
        mobile_number = input("Mobile number (with country code): ").strip()

        password = getpass("Password: ")
        confirm_password = getpass("Confirm Password: ")

        if password != confirm_password:
            print("Passwords do not match")
            return

        if db.query(User).filter(User.email == email).first():
            print("Email already exists")
            return

        if db.query(User).filter(User.mobile_number == mobile_number).first():
            print("Mobile number already exists")
            return

        _, country_code = get_country_from_mobile(mobile_number)

        country = db.query(Country).filter(Country.country_code == country_code).first()

        if not country:
            print(f"Country not found for country code {country_code}")
            return

        user = User(
            email=email,
            username=username,
            mobile_number=mobile_number,
            country_id=country.id,
            hashed_password=pwd_context.hash(password),
            is_active=True,
            is_superuser=True,
            is_email_verified=True,
        )

        db.add(user)
        db.commit()

        print("Superuser created successfully")

    except Exception as e:
        db.rollback()
        print("Failed to create superuser:", e)

    finally:
        db.close()


if __name__ == "__main__":
    create_superuser()
