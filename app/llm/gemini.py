# app/llm/gemini.py

import json
import os

import google.generativeai as genai

from app.utils.logger_config import app_logger as logger

logger.info("Initializing Gemini client")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is not set")
    raise RuntimeError("Missing GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

logger.info("Gemini API configured successfully")
logger.debug(f"Gemini model loaded: {model}")


def generate_valuation_summary(form_data: dict):
    logger.info("Starting Gemini valuation summary generation")

    try:
        prompt = f"""
        You are an Automated Valuation Model (AVM).
        Return ONLY valid JSON. DO NOT include explanations.

        {{
          "property_details": {{
              "address": "{form_data.get('full_address')}",
              "city": "{form_data.get('city_location')}",
              "country": "{form_data.get('country')}",
              "property_type": "{form_data.get('property_type')}",
              "land_area_sqft": {int(form_data.get("land_area").split()[0])},
              "built_up_area_sqft": {int(form_data.get("built_up_area").split()[0])},
              "age_years": {int(form_data.get("year_built"))}
          }},
          "predicted_value": {{
              "low_value": 0,
              "mid_value": 0,
              "high_value": 0,
              "fair_market_value": 0,
              "confidence_score": 80
          }},
          "bank_lending_model": {{
              "recommended_ltv": 75,
              "safe_lending_value": 0,
              "risk_level": "Moderate",
              "reason": ""
          }},
          "buy_sell_recommendation": {{
              "buyer_recommendation": "",
              "seller_recommendation": "",
              "reasoning": ""
          }},
          "comparables_used": [
              {{
                  "address": "",
                  "land_area": "",
                  "sale_price": 0,
                  "distance_km": 0,
                  "adjustment_reason": ""
              }}
          ],
          "forecast": {{
              "growth_rate_percent": 6.0,
              "value_in_12_months": 0
          }}
        }}
        Return ONLY JSON.
        """

        response = model.generate_content(prompt)
        raw = response.text.strip()

        logger.debug("Raw Gemini response received")

        try:
            parsed = json.loads(raw)
            logger.info("Gemini valuation summary parsed successfully")
            return parsed

        except json.JSONDecodeError:
            logger.warning("Invalid JSON received, attempting cleanup")
            cleaned = raw[raw.find("{") : raw.rfind("}") + 1]
            parsed = json.loads(cleaned)
            logger.info("Gemini response cleaned and parsed successfully")
            return parsed

    except Exception:
        logger.exception("Gemini valuation generation failed")
        raise
