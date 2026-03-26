import csv

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.models.country import Country


def import_countries(csv_path: str):
    db: Session = SessionLocal()

    try:
        existing_country_codes = {
            country_code
            for (country_code,) in db.query(Country.country_code).all()
            if country_code
        }

        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                country_code = row["country_code"].strip()

                if country_code in existing_country_codes:
                    print(f"Skipping existing country: {country_code}")
                    continue

                db.add(
                    Country(
                        name=row["name"].strip(),
                        country_code=country_code,
                        dial_code=row.get("dial_code", "").strip(),
                        currency_code=row.get("currency_code", "").strip() or None,
                    )
                )
                existing_country_codes.add(country_code)

            db.commit()
            print("Countries imported successfully.")

    except Exception as e:
        db.rollback()
        print("Error importing countries:", str(e))

    finally:
        db.close()


if __name__ == "__main__":
    import_countries("data - data.csv.csv")
