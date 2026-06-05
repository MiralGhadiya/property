from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.models.system_config import SystemConfig
from app.scripts.config_seed import load_config_seed_values
from app.utils.logger_config import app_logger as logger


def import_env_variables():
    env_vars = load_config_seed_values()

    db: Session = SessionLocal()

    try:
        for key, value in env_vars.items():
            if value is None:
                continue

            existing = (
                db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            )

            if existing:
                logger.info(f"Skipping existing config: {key}")
                continue

            db.add(SystemConfig(config_key=key, config_value=value))

            logger.info(f"Inserted config: {key}")

        db.commit()
        logger.info("Environment variables imported successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_env_variables()
