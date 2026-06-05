# app/services/valuation_service.py

from sqlalchemy.orm import Session

from app.models.valuation import ValuationReport
from app.utils.logger_config import app_logger as logger


def save_valuation_report(db: Session, payload: dict) -> int:
    logger.info(
        f"Saving valuation report valuation_id={payload.get('valuation_id')} " f"user_id={payload.get('user_id')}"
    )
    try:
        record = ValuationReport(
            valuation_id=payload["valuation_id"],
            user_id=payload["user_id"],
            subscription_id=payload["subscription_id"],
            category=payload["category"],
            country_code=payload["country_code"],
            user_fields=payload["user_fields"],
            ai_response=payload["ai_response"],
            report_context=payload["report_context"],
        )

        db.add(record)
        db.flush()

        logger.info(f"Valuation report saved record_id={record.id} " f"valuation_id={record.valuation_id}")

        return record.id

    except Exception:
        logger.exception("Failed to save valuation report")
        raise
