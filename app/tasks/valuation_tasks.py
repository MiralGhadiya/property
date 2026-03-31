# app/tasks/valuation_tasks.py

import io
import base64
import smtplib
from datetime import datetime, timezone

import matplotlib.pyplot as plt
from sqlalchemy import text

from app.celery_app import celery_app
from app.database.db import SessionLocal
from app.llm.openai import (
    generate_forecast,
    generate_swot,
    generate_valuation_report,
)
from app.models.subscription import UserSubscription
from app.models.valuation import ValuationJob, ValuationReport
from app.services.subscription_service import increment_usage
from app.services.valuation_report_builder import build_report_context
from app.services.valuation_service import save_valuation_report
from app.utils.email import send_pdf_email
from app.utils.logger_config import app_logger as logger
from app.utils.maps import build_static_maps, geocode_address


def get_currency_from_country(db, country_code):
    from app.models.country import Country

    country = (
        db.query(Country)
        .filter(Country.country_code == country_code)
        .first()
    )

    if not country:
        return "USD"

    return country.currency_code


def _start_valuation_job(job_id: str) -> dict | None:
    db = SessionLocal()

    try:
        job = db.query(ValuationJob).filter(ValuationJob.id == job_id).first()
        if not job:
            return None

        if job.status == "completed":
            logger.info(f"Skipping already completed valuation job_id={job_id}")
            return None

        job.status = "processing"
        job.error_message = None
        db.commit()

        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.id == job.subscription_id)
            .first()
        )
        if not subscription:
            raise RuntimeError("Subscription not found for job")

        plan_name = subscription.plan.name.upper()

        return {
            "job_id": job.id,
            "user_id": job.user_id,
            "subscription_id": job.subscription_id,
            "category": job.category,
            "country_code": job.country_code,
            "user_input": job.request_payload,
            "plan_name": plan_name,
        }

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _reserve_valuation_id() -> str:
    db = SessionLocal()

    try:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = get_next_valuation_sequence(db)
        valuation_id = f"DV-{today}-{seq:04d}"
        db.commit()
        return valuation_id

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _lookup_currency_code(country_code: str | None) -> str:
    if not country_code:
        return "USD"

    db = SessionLocal()

    try:
        return get_currency_from_country(db, country_code) or "USD"
    finally:
        db.close()


def _finalize_valuation_job(
    job_context: dict,
    valuation_id: str,
    ai_json: dict,
    context: dict,
) -> None:
    db = SessionLocal()

    try:
        job = (
            db.query(ValuationJob)
            .filter(ValuationJob.id == job_context["job_id"])
            .with_for_update()
            .first()
        )
        if not job:
            raise RuntimeError("Valuation job not found during finalization")

        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.id == job_context["subscription_id"])
            .with_for_update()
            .first()
        )
        if not subscription:
            raise RuntimeError("Subscription not found during finalization")

        save_valuation_report(
            db,
            {
                "valuation_id": valuation_id,
                "user_id": job.user_id,
                "subscription_id": job.subscription_id,
                "category": job.category,
                "country_code": job.country_code,
                "user_fields": job_context["user_input"],
                "ai_response": ai_json,
                "report_context": context,
            },
        )

        increment_usage(db, subscription, commit=False)

        job.status = "completed"
        job.valuation_id = valuation_id
        job.error_message = None
        db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _mark_valuation_job_failed(job_id: str, error_message: str) -> None:
    db = SessionLocal()

    try:
        failed_job = db.query(ValuationJob).filter(ValuationJob.id == job_id).first()
        if not failed_job:
            return

        failed_job.status = "failed"
        failed_job.error_message = error_message
        db.commit()

    except Exception:
        db.rollback()
        logger.exception(f"Failed to persist valuation failure state job_id={job_id}")
    finally:
        db.close()


def _load_valuation_result(job_id: str) -> dict:
    db = SessionLocal()

    try:
        job = (
            db.query(ValuationJob)
            .filter(ValuationJob.id == job_id)
            .first()
        )
        if not job or not job.valuation_id:
            raise RuntimeError("Completed valuation job is missing valuation reference")

        valuation = (
            db.query(ValuationReport)
            .filter(ValuationReport.valuation_id == job.valuation_id)
            .first()
        )
        if not valuation:
            raise RuntimeError("Generated valuation report was not found")

        currency_code = None
        if valuation.report_context:
            currency_code = valuation.report_context.get("currency_code")

        return {
            "status": "success",
            "job_id": job.id,
            "valuation_id": valuation.valuation_id,
            "report_context": valuation.report_context,
            "currency_code": currency_code,
            "message": "Valuation generated successfully",
        }
    finally:
        db.close()


def _load_email_delivery_context(valuation_id: str, user_id: int) -> tuple[str, str | None]:
    db = SessionLocal()

    try:
        valuation = (
            db.query(ValuationReport)
            .filter(
                ValuationReport.valuation_id == valuation_id,
                ValuationReport.user_id == user_id,
            )
            .first()
        )

        if not valuation:
            raise RuntimeError("Valuation not found or unauthorized")

        client_email = valuation.user_fields.get("email")
        client_name = valuation.user_fields.get("full_name")

        if not client_email:
            raise RuntimeError("Client email missing")

        return client_email, client_name

    finally:
        db.close()


def build_calculation_input(user_input: dict):
    """
    Keep user values only if provided.
    Remove empty fields so AI can infer them.
    """
    return {
        k: v
        for k, v in user_input.items()
        if v not in [None, "", "null"]
    }


def get_next_valuation_sequence(db) -> int:
    """
    Ensure the legacy public valuation sequence exists, then return the next value.
    The advisory lock prevents duplicate sequence bootstrapping across workers.
    """
    db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": 482001})

    sequence_exists = db.execute(
        text("SELECT to_regclass('public.valuation_seq')")
    ).scalar()

    if sequence_exists is None:
        db.execute(
            text("CREATE SEQUENCE valuation_seq START WITH 1 INCREMENT BY 1")
        )

        max_existing_suffix = db.execute(
            text(
                """
                SELECT COALESCE(
                    MAX(CAST(split_part(valuation_id, '-', 3) AS BIGINT)),
                    0
                )
                FROM valuation_reports
                WHERE valuation_id ~ '^DV-[0-9]{8}-[0-9]+$'
                """
            )
        ).scalar()

        if max_existing_suffix:
            db.execute(
                text("SELECT setval('valuation_seq', :value, true)"),
                {"value": int(max_existing_suffix)},
            )

    return int(db.execute(text("SELECT nextval('valuation_seq')")).scalar())


def run_valuation_job(job_id: str) -> dict | None:
    try:
        job_context = _start_valuation_job(job_id)
        if not job_context:
            return

        user_input = job_context["user_input"]
        plan_name = job_context["plan_name"]
        calculation_input = build_calculation_input(user_input)
        core = generate_valuation_report(calculation_input, plan=plan_name)
        
        if plan_name != "BASIC":
            forecast = generate_forecast(core)
            core["forecast"] = forecast
        else:
            core["forecast"] = None
            

        # forecast = generate_forecast(core)
        # core["forecast"] = forecast

        # if plan_name in ["PRO", "MASTER"]:
        #     core["swot_analysis"] = generate_swot(core)
        # else:
        #     core["swot_analysis"] = {
        #         "strengths": [],
        #         "weaknesses": [],
        #         "opportunities": [],
        #         "threats": []
        #     }
        
        if plan_name in ["PRO", "MASTER", "GLOBAL"]:
            try:
                # Ensure bank_lending_model exists
                if "bank_lending_model" not in core:
                    core["bank_lending_model"] = {
                        "recommended_ltv": 0,
                        "safe_lending_value": 0,
                        "risk_level": "medium",
                        "reason": ""
                    }

                elif "risk_level" not in core["bank_lending_model"]:
                    core["bank_lending_model"]["risk_level"] = "medium"

                core["swot_analysis"] = generate_swot(core)

            except Exception as e:
                logger.warning(f"SWOT generation failed: {e}")
                core["swot_analysis"] = {
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": []
                }

        ai_json = core
        ai_json["valuation_validity_days"] = 60
        valuation_id = _reserve_valuation_id()
                
        print("AI JSON RESPONSE:", ai_json)
        
        print("FORECAST FROM AI:", ai_json.get("forecast"))
    
        context = build_report_context(ai_json, user_input, valuation_id=valuation_id)
        
        if plan_name != "BASIC" and context["future_outlook"]:
            years = [item["year"] for item in context["future_outlook"]]
            values = [item["expected_value"] for item in context["future_outlook"]]

            plt.figure(figsize=(6, 4))
            plt.plot(years, values, marker='o')

            for i, txt in enumerate(context["future_outlook"]):
                plt.annotate(
                    f"{txt['growth_percent']}%",
                    (years[i], values[i]),
                    textcoords="offset points",
                    xytext=(0,10),
                    ha='center'
                )

            plt.title("5-Year Price Forecast")
            plt.xlabel("Year")
            plt.ylabel("Projected Value")
            plt.grid(True)

            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", bbox_inches="tight")
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            plt.close()

            context["forecast_chart"] = image_base64
        else:
            context["forecast_chart"] = []
        
        address = ai_json["property_details"]["address"]

        # 3️⃣ Geocode
        geo = geocode_address(address)

        currency_code = "USD"

        if geo:
            context["property_maps"] = build_static_maps(
                geo["lat"],
                geo["lng"],
                address
            )

            detected_country = geo.get("country_code")

            if detected_country:
                currency_code = _lookup_currency_code(detected_country)

        else:
            context["property_maps"] = None
            
        context["currency_code"] = currency_code

        # if geo:
        #     maps = build_static_maps(geo["lat"], geo["lng"])

        #     # context["property_identification"]["location"] = {
        #     #     "latitude": geo["lat"],
        #     #     "longitude": geo["lng"],
        #     #     "location_type": geo["location_type"],
        #     #     "formatted_address": geo["formatted_address"],
        #     #     "maps": maps
        #     # }
        # else:
        #     context["property_identification"]["location"] = None
            
        # html = render_html("valuation_template.html", context)
        # pdf_path = generate_pdf_from_html(html)

        # send_pdf_email(
        #     to_email=user_input["email"],
        #     subject="Your Desktop Valuation Report",
        #     message=f"Dear {user_input['full_name']},\n\nPlease find attached your valuation report.",
        #     pdf_path=pdf_path,
        # )
        
        # valuation_id = str(uuid4())
        # valuation_id = f"DV-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8]}"

        # valuation_id = context["property_identification"]["valuation_id"]
        _finalize_valuation_job(job_context, valuation_id, ai_json, context)

        logger.info(f"Valuation completed job_id={job_id}")
        return _load_valuation_result(job_id)

    except Exception as e:
        _mark_valuation_job_failed(job_id, str(e))
        logger.exception(f"Valuation failed job_id={job_id}")
        raise

        
@celery_app.task(
    bind=True,
    autoretry_for=(RuntimeError,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 2},
)
def process_valuation_job(self, job_id: str):
    return run_valuation_job(job_id)


def send_report_email_direct(
    valuation_id: str,
    user_id,
    pdf_bytes: bytes,
    original_filename: str,
):
    logger.info(
        f"Email send started valuation_id={valuation_id} user_id={user_id}"
    )

    client_email, client_name = _load_email_delivery_context(
        valuation_id,
        user_id,
    )

    send_pdf_email(
        to_email=client_email,
        subject="Your Desktop Valuation Report",
        client_name=client_name,
        pdf_bytes=pdf_bytes,
        filename=original_filename,
    )

    logger.info(f"Email sent successfully valuation_id={valuation_id}")


@celery_app.task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, ConnectionError),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def send_report_email_task(
    self,
    valuation_id: str,
    user_id: int,
    pdf_base64: str,
    original_filename: str,
):
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        send_report_email_direct(
            valuation_id=valuation_id,
            user_id=user_id,
            pdf_bytes=pdf_bytes,
            original_filename=original_filename,
        )

    except Exception:
        logger.exception(f"Email sending failed valuation_id={valuation_id}")
        raise
