# app/tasks/valuation_tasks.py

import io
import os
import base64
import smtplib
from sqlalchemy import text
from datetime import datetime, timezone
import matplotlib.pyplot as plt
from app.celery_app import celery_app
from app.database.db import SessionLocal
from app.models.valuation import ValuationJob, ValuationReport
from app.services.subscription_service import increment_usage
from app.services.valuation_service import save_valuation_report
from app.services.valuation_report_builder import build_report_context
from app.llm.openai import (
    generate_valuation_report,
    generate_forecast,
    generate_swot,
)
from app.utils.email import send_pdf_email
from app.utils.maps import geocode_address, build_static_maps
from app.models.subscription import UserSubscription

from app.utils.logger_config import app_logger as logger


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


@celery_app.task(
    bind=True,
    autoretry_for=(RuntimeError,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 2},
)
def process_valuation_job(self, job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ValuationJob).filter(ValuationJob.id == job_id).first()
        if not job:
            return

        job.status = "processing"
        db.commit()

        user_input = job.request_payload

        # ai_json = generate_valuation_report(user_input)
        
        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.id == job.subscription_id)
            .first()
        )
        
        plan_name = subscription.plan.name.upper()
        
        core = generate_valuation_report(user_input, plan=plan_name)
        
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
        
        if plan_name in ["PRO", "MASTER"]:
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
        # valuation_id = f"DV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8]}"
        
        today = datetime.now(timezone.utc).strftime("%Y%m%d")

        seq = db.execute(text("SELECT nextval('valuation_seq')")).scalar()

        valuation_id = f"DV-{today}-{seq:04d}"
                
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
                currency_code = get_currency_from_country(db, detected_country)

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
        save_valuation_report(
            db,
            {
                "valuation_id": valuation_id,
                "user_id": job.user_id,
                "subscription_id": job.subscription_id,
                "category": job.category,
                "country_code": job.country_code,
                "user_fields": user_input,
                "ai_response": ai_json,
                "report_context": context,
            },
        )

        if not subscription:
            raise RuntimeError("Subscription not found for job")

        increment_usage(db, subscription)

        job.status = "completed"
        job.valuation_id = valuation_id
        # job.pdf_path = pdf_path
        db.commit()

        logger.info(f"Valuation completed job_id={job_id}")

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        logger.exception(f"Valuation failed job_id={job_id}")
        raise
    finally:
        db.close()
        

        
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
    db = SessionLocal()
    temp_path = None

    try:
        logger.info(
            f"Email task started valuation_id={valuation_id} user_id={user_id}"
        )

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

        pdf_bytes = base64.b64decode(pdf_base64)

        # safe_filename = f"Valuation_Report_{valuation_id}.pdf"

        send_pdf_email(
            to_email=client_email,
            subject="Your Desktop Valuation Report",
            client_name=client_name,
            pdf_bytes=pdf_bytes,
            filename=original_filename,  
        )

        logger.info(f"Email sent successfully valuation_id={valuation_id}")

    except Exception:
        logger.exception(f"Email sending failed valuation_id={valuation_id}")
        raise

    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.remove(temp_path)

        db.close()