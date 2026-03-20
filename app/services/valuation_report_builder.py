# app/services/valuation_report_builder.py

from datetime import datetime


def _get_value_or_fallback(user_val, ai_val, default="N/A"):
    """Helper function to get value with fallback chain."""
    return user_val or ai_val or default


def _build_property_details(user_input, ai_json, construction_year, property_age):
    """Extract property details section."""
    built_up_area = (
        user_input.get("built_up_area_sqft")
        or ai_json["property_details"].get("built_up_area_sqft")
    )
    
    return {
        "name_of_owner": user_input.get("full_name", "N/A"),
        # "project_name": user_input.get("project_name", "N/A"),
        "project_name": (
            user_input.get("project_name")
            or ai_json["property_details"].get("project_name")
            or ai_json["property_details"].get("developer")
            or "Independent Property"
        ),
        "property_address": ai_json["property_details"].get("address", "N/A"),
        "property_type": ai_json["property_details"].get("property_type", "N/A"),
        # "configuration": _get_value_or_fallback(
        #     user_input.get("configuration"),
        #     ai_json["property_details"].get("configuration")
        # ),
        "configuration": ai_json["property_details"].get("configuration"),
        "land_area_sqft": ai_json["property_details"].get("land_area_sqft", "N/A"),
        "carpet_area": built_up_area if built_up_area else "N/A",
        # "construction_status": _get_value_or_fallback(
        #     user_input.get("construction_status"),
        #     ai_json["property_details"].get("construction_status")
        # ),
        
        "construction_status": ai_json["property_details"].get("construction_status"),
        # "construction_year": _get_value_or_fallback(
        #     construction_year,
        #     ai_json["property_details"].get("construction_year")
        # ),
        "construction_year": ai_json["property_details"].get("construction_year"),
        # "property_age_years": _get_value_or_fallback(
        #     property_age,
        #     ai_json["property_details"].get("age_years")
        # ),
        "property_age_years": ai_json["property_details"].get("age_years"),
        # "last_sale_date": _get_value_or_fallback(
        #     user_input.get("last_sale_date"),
        #     ai_json["property_details"].get("last_sale_date")
        # ),
        # "last_sale_price": _get_value_or_fallback(
        #     user_input.get("last_sale_price"),
        #     ai_json["property_details"].get("last_sale_price")
        # ),
        # "ownership_type": _get_value_or_fallback(
        #     user_input.get("ownership_type"),
        #     ai_json["property_details"].get("ownership_type")
        # ),
        "ownership_type": ai_json["property_details"].get("ownership_type"),
        "title_details": ai_json["property_details"].get("title_details", "N/A"),
        # "purpose_of_report": user_input.get("purpose_of_valuation", "N/A"),
        "purpose_of_report": (
            user_input.get("purpose_of_valuation")
            or ai_json["property_details"].get("purpose_of_valuation")
            or ai_json.get("purpose_of_report")
            or "Market Value Assessment"
        ),
        "type_of_valuation": "Desktop Valuation Opinion",
        "inspection": "No Physical Inspection Conducted",
        "confidentiality": "Strictly for internal reference",
    }


def _build_location_identification(user_input, ai_json):
    """Extract location identification section."""
    return {
        "micro_location": _get_value_or_fallback(
            user_input.get("micro_location"),
            ai_json["property_details"].get("micro_location")
        ),
        "municipal_authority": _get_value_or_fallback(
            user_input.get("municipal_authority"),
            ai_json["property_details"].get("municipal_authority")
        ),
        "connectivity": _get_value_or_fallback(
            user_input.get("connectivity"),
            ai_json["property_details"].get("connectivity")
        ),
        "social_infrastructure": _get_value_or_fallback(
            user_input.get("social_infrastructure"),
            ai_json["property_details"].get("social_infrastructure")
        ),
        "surroundings": _get_value_or_fallback(
            user_input.get("surroundings"),
            ai_json["property_details"].get("surroundings")
        ),
        "zoning": ai_json["property_details"].get("zoning", "N/A"),
        "demand_profile": _get_value_or_fallback(
            user_input.get("demand_profile"),
            ai_json["property_details"].get("demand_profile")
        ),
    }


def _build_project_profile(user_input, ai_json):
    """Extract project profile section."""
    return {
        "developer": _get_value_or_fallback(
            user_input.get("developer"),
            ai_json["property_details"].get("developer")
        ),
        "project_positioning": _get_value_or_fallback(
            user_input.get("project_positioning"),
            ai_json["property_details"].get("project_positioning")
        ),
        "towers": _get_value_or_fallback(
            user_input.get("towers"),
            ai_json["property_details"].get("towers")
        ),
        "amenities": _get_value_or_fallback(
            user_input.get("amenities"),
            ai_json["property_details"].get("amenities")
        ),
        "market_perception": _get_value_or_fallback(
            user_input.get("market_perception"),
            ai_json["property_details"].get("market_perception")
        ),
    }


def _build_area_details(user_input, ai_json, built_up_area):
    """Extract area details section."""
    return {
        "carpet_area_sqft": built_up_area if built_up_area else "N/A",
        "layout": _get_value_or_fallback(
            user_input.get("layout"),
            ai_json["property_details"].get("layout")
        ),
        "floor_plan": _get_value_or_fallback(
            user_input.get("floor_plan"),
            ai_json["property_details"].get("floor_plan")
        ),
        "current_usage": _get_value_or_fallback(
            user_input.get("current_usage"),
            ai_json["property_details"].get("current_usage")
        ),
    }


def _build_market_benchmark(raw_comparables):
    """Extract market benchmark section."""
    return [
        {
            "address": comp.get("address", "N/A"),
            "beds_baths": comp.get("beds_baths", "N/A"),
            "land_size_sqft": comp.get("land_size_sqft", "N/A"),
            "sale_date": comp.get("sale_date", "N/A"),
            "sale_price": comp.get("sale_price", "N/A"),
            "distance_km": comp.get("distance_km", "N/A"),
            "comparison_level": comp.get("comparison_level", "Comparable"),
        }
        for comp in raw_comparables
    ]


def _build_indicative_market_value(mid_value, area_for_valuation):
    """Extract indicative market value section."""
    adopted_rate = (
        int(mid_value / area_for_valuation)
        if area_for_valuation and area_for_valuation > 0
        else "N/A"
    )
    
    return {
        "area_considered_sqft": area_for_valuation,
        "adopted_market_rate": adopted_rate,
        "indicative_value": mid_value,
    }


def _build_value_range(ai_json):
    """Extract value range section."""
    return {
        "conservative": {
            "value": ai_json["predicted_value"]["low_value"],
            "explanation": ai_json["predicted_value"].get(
                "low_explanation",
                "Lower bound estimate based on conservative assumptions."
            )
        },
        "mid_range": {
            "value": ai_json["predicted_value"]["mid_value"],
            "explanation": ai_json["predicted_value"].get(
                "mid_explanation",
                "Fair market value under normal conditions."
            )
        },
        "optimistic": {
            "value": ai_json["predicted_value"]["high_value"],
            "explanation": ai_json["predicted_value"].get(
                "high_explanation",
                "Upper bound estimate assuming strong demand."
            )
        }
    }


def _build_advanced_analytics(ai_json):
    """Extract advanced analytics section."""
    return {
        "confidence_score": ai_json["predicted_value"].get("confidence_score", 0),
        "recommended_ltv": ai_json.get("bank_lending_model", {}).get("recommended_ltv", 0),
        "safe_lending_value": ai_json.get("bank_lending_model", {}).get("safe_lending_value", 0),
        "risk_level": ai_json.get("bank_lending_model", {}).get("risk_level", "N/A"),
        "valuation_validity_days": ai_json.get("valuation_validity_days", 60),
    }


def _build_future_outlook(ai_json):
    """Extract future outlook section."""
    forecast = ai_json.get("forecast", {})
    current_year = datetime.now().year
    base_value = ai_json["predicted_value"]["mid_value"]
    
    growth_rates = [
        forecast.get("year_1_growth_percent", 0),
        forecast.get("year_2_growth_percent", 0),
        forecast.get("year_3_growth_percent", 0),
        forecast.get("year_4_growth_percent", 0),
        forecast.get("year_5_growth_percent", 0),
    ]
    
    future_outlook = []
    for i, rate in enumerate(growth_rates, start=1):
        projected_value = int(base_value * ((1 + rate / 100) ** i))
        future_outlook.append({
            "year": current_year + i,
            "expected_value": projected_value,
            "growth_percent": rate,
        })
    
    return future_outlook


def _build_rental_analysis(ai_json):
    """Extract rental analysis section."""
    rental_raw = ai_json.get("rental_analysis", {})
    
    return {
        "estimated_monthly_rent": rental_raw.get("estimated_monthly_rent", 0),
        "estimated_annual_rent": rental_raw.get("estimated_annual_rent", 0),
        "rental_yield_percent": rental_raw.get("rental_yield_percent", 0),
        "rental_demand_level": rental_raw.get("rental_demand_level", "N/A"),
        "average_rent_locality": rental_raw.get("average_rent_locality", 0),
        "nearby_rental_comparables": rental_raw.get("nearby_rental_comparables", []),
    }


def _calculate_construction_year_and_age(year_built):
    """Calculate construction year and property age from year_built."""
    if not year_built:
        return None, None
    try:
        construction_year = int(year_built)
        property_age = datetime.now().year - construction_year
        return construction_year, property_age
    except ValueError:
        return None, None


def _build_report_metadata(user_input, valuation_id):
    """Extract report metadata section."""
    return {
        "valuation_id": valuation_id or "N/A",
        "date_of_report": datetime.now().strftime("%d %B %Y"),
        "client_name": user_input.get("client_name", "N/A"),
    }


def build_report_context(ai_json, user_input, valuation_id=None):    
    built_up_area = (
        user_input.get("built_up_area_sqft")
        or ai_json["property_details"].get("built_up_area_sqft")
    )
    
    year_built = user_input.get("year_built")
    construction_year, property_age = _calculate_construction_year_and_age(year_built)
    
    report_metadata = _build_report_metadata(user_input, valuation_id)
    property_details = _build_property_details(user_input, ai_json, construction_year, property_age)
    location_identification = _build_location_identification(user_input, ai_json)
    project_profile = _build_project_profile(user_input, ai_json)
    area_details = _build_area_details(user_input, ai_json, built_up_area)
    
    raw_comparables = ai_json.get("comparables_used", [])
    market_benchmark = _build_market_benchmark(raw_comparables)
    
    mid_value = ai_json["predicted_value"]["mid_value"]
    area_for_valuation = built_up_area or 0
    indicative_market_value = _build_indicative_market_value(mid_value, area_for_valuation)
    
    value_range = _build_value_range(ai_json)
    advanced_analytics = _build_advanced_analytics(ai_json)

    nearby_market_evidence = [
        "Recent transactions in nearby premium projects support the adopted rate",
        "Strong demand for ready-to-move residential units",
        "Limited supply of new premium projects in the locality",
        "Healthy resale and rental absorption observed",
    ]

    # future_outlook = _build_future_outlook(ai_json)
    future_outlook = []
    
    if ai_json.get("forecast"):
        future_outlook = _build_future_outlook(ai_json)
        
    swot_analysis = ai_json.get(
        "swot_analysis",
        {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }
    )
    
    rental_analysis = _build_rental_analysis(ai_json)
    
    disclaimer = [
        "This report is a Desktop Valuation Opinion prepared using secondary market data.",
        "No physical or on-site inspection of the subject property has been carried out.",
        "The value stated represents an indicative market value for cross-check/reference purposes only.",
        "Actual realizable value may vary based on physical condition, legal status, negotiations, and market sentiment.",
        "This report is not intended for statutory, legal, lending, or enforcement purposes.",
        "No responsibility is assumed for title verification, encumbrances, or statutory approvals.",
        "This report is confidential and intended solely for the client.",
    ]

    return {
        "property_details": property_details,
        "report_metadata": report_metadata,
        "location_identification": location_identification,
        "project_profile": project_profile,
        "area_details": area_details,
        "market_benchmark": market_benchmark,
        "indicative_market_value": indicative_market_value,
        "value_range": value_range,
        "advanced_analytics": advanced_analytics,
        "nearby_market_evidence": nearby_market_evidence,
        "future_outlook": future_outlook,
        "swot_analysis": swot_analysis,
        "rental_analysis": rental_analysis,
        "disclaimer": disclaimer,
        "currency_code": ai_json.get("currency_code"),
    }
