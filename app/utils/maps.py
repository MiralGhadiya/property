# app/utils/maps.py

import base64
import os
import random
import requests

from app.utils.logger_config import app_logger as logger

GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def geocode_address(address: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "address": address,
        "key": GOOGLE_MAPS_KEY
    }

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if data.get("status") != "OK":
        return None

    result = data["results"][0]
    loc = result["geometry"]["location"]

    country_code = None
    country_name = None

    for component in result["address_components"]:
        if "country" in component["types"]:
            country_code = component["short_name"]   # US, AE, IN
            country_name = component["long_name"]

    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "formatted_address": result["formatted_address"],
        "location_type": result["geometry"]["location_type"],
        "country_code": country_code,
        "country_name": country_name
    }
    

def find_place(address: str):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

    params = {
        "input": address,
        "inputtype": "textquery",
        "fields": "place_id,photos",
        "key": GOOGLE_MAPS_KEY
    }

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if data.get("status") != "OK" or not data.get("candidates"):
        return None

    return data["candidates"][0]


def get_place_photo(address: str):

    place = find_place(address)

    if not place:
        return None

    photos = place.get("photos")

    if not photos:
        return None

    photo = random.choice(photos)
    logger.info(f"Selected photo reference: {photo['photo_reference']} for address: {address}")
    
    ref = photo["photo_reference"]
    logger.info(f"Fetching photo for reference: {ref}")

    url = (
        "https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth=600"
        f"&photo_reference={ref}"
        f"&key={GOOGLE_MAPS_KEY}"
    )
    logger.info(f"Constructed photo URL: {url}")

    r = requests.get(url, allow_redirects=True, timeout=10)

    if r.status_code != 200:
        return None

    image_base64 = base64.b64encode(r.content).decode()

    return f"data:image/jpeg;base64,{image_base64}"
        
    
def get_streetview_metadata(lat, lng):
    url = "https://maps.googleapis.com/maps/api/streetview/metadata"

    params = {
        "location": f"{lat},{lng}",
        "radius": 200,
        "source": "outdoor",
        "key": GOOGLE_MAPS_KEY
    }
    

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if data.get("status") != "OK":
        return None

    return data


def build_street_view(lat, lng):
    base = "https://maps.googleapis.com/maps/api/streetview"

    return (
        f"{base}?"
        f"size=600x400"
        f"&location={lat},{lng}"
        f"&radius=200"
        f"&source=outdoor"
        f"&fov=90"
        f"&pitch=0"
        f"&key={GOOGLE_MAPS_KEY}"
    )


def build_static_maps(lat, lng, address=None):
    base = "https://maps.googleapis.com/maps/api/staticmap"

    def common_params(zoom):
        return (
            f"center={lat},{lng}"
            f"&zoom={zoom}"
            f"&size=600x400"
            f"&scale=2"
            f"&markers=color:red%7C{lat},{lng}"
            f"&key={GOOGLE_MAPS_KEY}"
        )

    street_view = build_street_view(lat, lng)
    place_photo = get_place_photo(address) if address else None

    # fallback logic
    photo_or_street = place_photo if place_photo else street_view

    return {
        "roadmap": f"{base}?{common_params(16)}&maptype=roadmap",
        "hybrid": f"{base}?{common_params(16)}&maptype=hybrid",
        "terrain": f"{base}?{common_params(19)}&maptype=terrain",
        "location_image": photo_or_street
    }