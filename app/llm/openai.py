#app/llm/openai.py

import json
from openai import OpenAI, OpenAIError
from langsmith import traceable

from app.core.config_manager import get_config
from app.utils.logger_config import app_logger as logger


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMServiceUnavailable(LLMError):
    pass


_client = None
_current_api_key = None


def get_openai_client():
    global _client, _current_api_key

    api_key = get_config("OPENAI_API_KEY")

    if not api_key:
        logger.error("OPENAI_API_KEY is not set")
        raise RuntimeError("Missing OPENAI_API_KEY")

    # If client exists AND key hasn't changed → reuse
    if _client and _current_api_key == api_key:
        return _client

    # Otherwise rebuild client
    logger.info("Initializing OpenAI client with latest API key")

    _client = OpenAI(api_key=api_key)
    _current_api_key = api_key

    return _client
  

BASE_PROMPT = """
          Role: Certified real estate valuation engine.

          Global Constraints:
          - Output ONLY valid JSON
          - No markdown, no explanations
          - Numbers only (no commas)
          - Infer missing data logically
          - Maintain internal consistency
          - Validate user-provided inputs against market norms
          - If values are unrealistic or inconsistent, override them with corrected estimates
          - Always infer purpose_of_valuation if not provided
          - If data is inferred, do NOT mention that it is inferred
          - Output must appear as authoritative and final

          Valuation Contract:
          - Produce three independent values: low, mid, high
          - Each tier MUST use different assumptions
          - Apply directional adjustments (superior ↑, inferior ↓)
          - Enforce meaningful spread between tiers
          - Provide a short professional explanation for each value tier (1-2 lines each)

          Compliance:
          - Market approach dominates
          - Lending model must be conservative and defensible
          
          Advanced Analytics:
          - Generate market_risk_score (1-10)
          - Generate property_risk_score (1-10)
          
          If configuration or construction status is missing:
          - Infer configuration based on property type, area, and market norms
          - Infer construction status as one of:
          Under Construction | Ready to Move | Vacant Plot | Occupied
          
          Additional Valuation Drivers (MANDATORY):
          - configuration materially impacts valuation
          - construction_status materially impacts valuation

          Rules:
          - Ready-to-move or completed properties command a premium
          - Under-construction properties require risk discounting
          - Vacant plots must NOT include construction value
          - Residential plots ignore configuration for area breakup but consider it for demand
          - Flats and houses MUST adjust value based on configuration (1BHK < 2BHK < 3BHK)
          
          Inference Rules (MANDATORY):
          - If location or project attributes are missing, infer them logically
          - Use city, address, property type, and zoning as signals
          - Use standard real estate norms
          - Never leave descriptive fields empty unless impossible
          - safe_lending_value MUST NOT be 0

          Location:
          - micro_location
          - municipal_authority
          - connectivity
          - social_infrastructure
          - surroundings
          - demand_profile
 
          Project:
          - developer
          - project_positioning
          - towers
          - amenities
          - market_perception

          Area Usage:
          - layout
          - floor_plan
          - current_usage
          
          Rental Analytics (MANDATORY):
          - Estimate monthly rent
          - Estimate annual rent
          - Calculate rental yield
          - Describe rental demand level
          - Estimate average rent in the locality per sqft
          - Provide 2-3 nearby rental comparables if possible
          
          Currency Rules (MANDATORY):
          - Determine the valuation currency based on property country
          - India → INR
          - United States → USD
          - UAE → AED
          - United Kingdom → GBP
          - Australia → AUD
          - Canada → CAD
          - Always produce valuation numbers in the local currency of the property country
          
          STRICT OUTPUT RULES (CRITICAL):
          - DO NOT return null, empty, or missing fields
          - Every field in the JSON schema MUST have a valid value
          - If exact value is unknown, generate a realistic estimate
          - Use:
              0 for numeric fields
              "N/A" for text fields ONLY if absolutely unavoidable
          - Prefer realistic inferred values over "N/A"
        """

PROPERTY_PROMPTS = {

    "residential plot": """
            Property Rules: Residential Plot

            Valuation Method:
            - Market comparable value is PRIMARY
            - Value land and buildup both is buildup area is given but focus on land value
            - Value land using nearby recent plot sale rates per sqft

            Adjustments:
            - Apply corner, road-facing, and size premiums
            - Apply demand premium in high-growth residential zones
            - Apply negative adjustments for irregular shape or poor access or outdated zoning or outside approved residential areas
            - Do NOT apply depreciation on land
            - Apply depreciation on buildup area

            Reconciliation:
            - Final value must not be lower than strong comparable-derived value
        """,

    "residential house": """
            Property Rules: Residential House

            Valuation Method:
            - Hybrid valuation: market comparables as anchor, cost-based as support
            - Value land separately from construction
            - Apply depreciation ONLY on construction

            Depreciation Caps:
            - Age < 10 years: max 10%
            - Age 10-20 years: max 20%

            Constraints:
            - Do NOT allow depreciated construction value to reduce market-driven valuation
            - Bias final value toward market comparables in high-demand zones

            Premiums:
            - Independent houses
            - Redevelopment potential
            - Corner or road-facing properties
        """,

    "residential flat": """
            Property Rules: Residential Flat

            Valuation Method:
            - Market comparable value is PRIMARY
            - Cost-based construction valuation is SECONDARY and supportive
            - Land value must be apportioned based on undivided share
            
            Valuation Drivers:
            - Configuration (1BHK, 2BHK, 3BHK, etc.) directly impacts market rate
            - Larger configurations command higher per-unit value but slightly lower per-sqft rate
            - Smaller configurations have higher liquidity but capped ticket size

            Depreciation:
            - Apply depreciation on construction component only
            - Cap depreciation at:
                - 10% if age < 10 years
                - 20% if age between 10 and 20 years
                - 30% if age > 20 years
                - 40% if age > 30 years
                
            Constraints:
            - Prefer same-building or same-society comparables
            - Configuration must align with built-up area

            Premiums:
            - Higher floor with lift access
            - Newer societies with amenities
            - Strong rental demand zones
            - Proximity to transit, IT parks, or CBD
        """,

    "commercial shop": """
            Property Rules: Commercial Shop

            Valuation Method:
            - Market comparables are DOMINANT
            - Ignore residential construction norms
            - Ground-floor retail premium applies
            - If propery is too small or old then apply decriciation accordingly on construction

            Depreciation:
            - Cap depreciation at 10% if age < 15 years

            Constraints:
            - Cost-based valuation must NOT undercut comparable-derived value
            - Apply footfall and frontage demand premiums
        """,

    "industrial unit": """
    
        Property Rules: Industrial Unit   

        Valuation Method:
        - Market comparables dominate where available
        - Value land plus industrial construction
        - Ignore residential norms entirely
        - Apply functional obsolescence risk adjustments

        Depreciation:
        - Cap depreciation at 15% if age < 20 years
        - Apply higher depreciation for specialized facilities

        Constraints:
        - Cost-based value cannot undercut market-derived value
        - Consider logistics access, zoning, and warehouse demand
      """
}


CORE_JSON_SCHEMA = """
        {
          "property_details":{
            "address":"",
            "city":"",
            "country":"",
            "property_type":"",
            "purpose_of_valuation": "",

            "micro_location":"",
            "municipal_authority":"",
            "connectivity":"",
            "social_infrastructure":"",
            "surroundings":"",
            "demand_profile":"",

            "developer":"",
            "project_positioning":"",
            "towers":"",
            "amenities":"",
            "market_perception":"",

            "layout":"",
            "floor_plan":"",
            "current_usage":"",

            "configuration":"",
            "construction_status":"",

            "land_area_sqft":0,
            "built_up_area_sqft":0,
            "age_years":0,
            "ownership_type":"",
            "zoning":"",
            
            "market_risk_score":0,
            "property_risk_score":0
            }
          "predicted_value":{
            "low_value":0,
            "mid_value":0,
            "high_value":0,
            "fair_market_value":0,
            "confidence_score":0,

            "low_explanation":"",
            "mid_explanation":"",
            "high_explanation":""
          },
          "bank_lending_model":{
            "recommended_ltv":0,"safe_lending_value":0,
            "risk_level":"","reason":""
          },
          "buy_sell_recommendation":{
            "buyer_recommendation":"",
            "seller_recommendation":"",
            "reasoning":""
          },
          "comparables_used":[{
            "address":"",
            "beds_baths":"",
            "land_size_sqft":0,
            "sale_date":"",
            "sale_price":0,
            "distance_km":0,
            "comparison_level":""
          }],
          "rental_analysis":{
            "estimated_monthly_rent":0,
            "estimated_annual_rent":0,
            "rental_yield_percent":0,
            "rental_demand_level":"",
            "average_rent_locality_per_sqft":0,
            "nearby_rental_comparables":[
              {
                "address":"",
                "configuration":"",
                "monthly_rent":0,
                "distance_km":0
              }
            ]
          }
        }
      """


BASIC_JSON_SCHEMA = """
{
  "property_details":{
    "address":"",
    "city":"",
    "country":"",
    "property_type":"",
    "micro_location":"",
    "municipal_authority":"",
    "connectivity":"",
    "social_infrastructure":"",
    "surroundings":"",
    "demand_profile":"",
    "developer":"",
    "project_positioning":"",
    "towers":"",
    "amenities":"",
    "market_perception":"",
    "layout":"",
    "floor_plan":"",
    "current_usage":"",
    "configuration":"",
    "construction_status":"",
    "land_area_sqft":0,
    "built_up_area_sqft":0,
    "age_years":0,
    "zoning":"",
    "title_details":"",
    "construction_year":0,
    "ownership_type":""
    },
  "predicted_value":{
    "low_value":0,
    "mid_value":0,
    "high_value":0,
    "fair_market_value":0,
    "confidence_score":0
  }
}
"""


FORECAST_SCHEMA = """
        {
          "year_1_growth_percent": 0,
          "year_2_growth_percent": 0,
          "year_3_growth_percent": 0,
          "year_4_growth_percent": 0,
          "year_5_growth_percent": 0,
          "value_in_12_months": 0
        }
      """


@traceable(name="generate_forecast", run_type="llm")
def generate_forecast(core_output: dict):
    prompt = f"""
        You are a real estate market forecasting engine.

        Rules:
        - Return ONLY valid JSON
        - No markdown
        - Numbers only
        - Growth rates must vary year-to-year
        - Base forecast on market maturity and property type

        Input:
        {{
          "fair_market_value": {core_output["predicted_value"]["fair_market_value"]},
          "property_type": "{core_output["property_details"]["property_type"]}",
          "city": "{core_output["property_details"]["city"]}",
          "confidence_score": {core_output["predicted_value"]["confidence_score"]}
        }}

        Return exactly this JSON:
        {{
          "year_1_growth_percent": 0,
          "year_2_growth_percent": 0,
          "year_3_growth_percent": 0,
          "year_4_growth_percent": 0,
          "year_5_growth_percent": 0,
          "value_in_12_months": 0
        }}
      """
    try:
      client = get_openai_client()

      response = client.chat.completions.create(
          model="gpt-5.2",
          messages=[{"role": "user", "content": prompt}],
          temperature=0.2,
          response_format={"type": "json_object"},
      )

      return json.loads(response.choices[0].message.content)
    
    except json.JSONDecodeError:
          logger.exception("Invalid JSON in forecast response")
          raise LLMServiceUnavailable("Forecast generation failed")

    except OpenAIError as e:
        logger.exception("OpenAI error during forecast")
        raise LLMServiceUnavailable("Forecast service unavailable") from e

    except Exception:
        logger.exception("Unexpected forecast failure")
        raise LLMServiceUnavailable("Forecast generation failed")



def _call_openai(final_prompt: str):
    client = get_openai_client()

    return client.chat.completions.create(
        model="gpt-5.2",
        messages=[{"role": "user", "content": final_prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

@traceable(name="generate_swot", run_type="llm")
def generate_swot(core_output: dict):
    prompt = f"""
        You are a real estate SWOT analysis engine.

        Rules:
        - Return ONLY valid JSON
        - No markdown
        - No explanations
        - Each list must contain 3–5 bullet points

        Input:
        {{
        "property_type": "{core_output['property_details']['property_type']}",
        "city": "{core_output['property_details']['city']}",
        "confidence_score": {core_output['predicted_value']['confidence_score']},
        "risk_level": "{core_output['bank_lending_model']['risk_level']}"
        }}

        Return exactly this JSON:
        {{
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
        }}
        """
        
    client = get_openai_client()

    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


@traceable(name="generate_valuation_report", run_type="chain")
def generate_valuation_report(form_data: dict, plan: str = "PRO"):
    logger.info("Starting valuation report generation")

    property_type = form_data.get("property_type")

    if not property_type:
        raise ValueError("property_type is required")
    
    property_rules = PROPERTY_PROMPTS.get(
        property_type.lower(),
        f"""
        Property Rules:
        - Interpret the property type "{property_type}" intelligently
        - Decide whether land, construction, or hybrid valuation applies
        - Use market comparables as the primary basis
        - Apply conservative, bank-grade assumptions
        - Handle non-standard or mixed-use properties logically
        """
    )

    if plan in ["PRO", "MASTER", "GLOBAL"]:
        schema = CORE_JSON_SCHEMA
    else:
        schema = BASIC_JSON_SCHEMA

    final_prompt = f"""
    {BASE_PROMPT}

    {property_rules}

    PLAN MODE: {plan}

    Input:
    {json.dumps(form_data, separators=(",", ":"))}

    Return exactly this JSON structure:
    {schema}
    """

    logger.debug("Final prompt constructed")

    try:
        response = _call_openai(final_prompt)
        content = response.choices[0].message.content
        parsed = json.loads(content)
        logger.info("Valuation report generated successfully")
        return parsed

    except json.JSONDecodeError:
        logger.error("Invalid JSON returned by OpenAI")
        logger.debug(content)
        raise ValueError("AI returned invalid JSON")

    except OpenAIError as e:
        logger.exception("OpenAI API error")
        raise RuntimeError("AI service unavailable") from e

    except Exception:
        logger.exception("Valuation generation failed")
        raise
