# app/middleware/ip_country.py

import requests
from fastapi import Request
from functools import lru_cache

from app.core.config_manager import get_config
from app.utils.logger_config import app_logger as logger


def get_ipinfo_token() -> str | None:
    token = get_config("IPINFO_TOKEN")

    if not token:
        logger.warning("IPINFO_TOKEN is not set; IP country lookup may fail")

    return token


@lru_cache(maxsize=10_000)
def get_ip_country(ip: str) -> str | None:
    """
    Returns ISO country code (e.g. 'IN') or None
    """

    token = get_ipinfo_token()

    if not token:
        logger.debug("Skipping IP lookup because IPINFO_TOKEN is not set")
        return None

    if not ip or ip in ("127.0.0.1", "localhost"):
        logger.debug(f"Skipping IP lookup for ip={ip}")
        return None

    logger.debug(f"Resolving country for ip={ip}")

    try:
        url = f"https://api.ipinfo.io/lite/{ip}"

        res = requests.get(
            url,
            params={"token": token},
            timeout=2
        )

        if res.status_code == 200:
            try:
                data = res.json()
            except ValueError:
                logger.warning(
                    f"Invalid JSON from IPINFO ip={ip} body={res.text}"
                )
                return None

            country = data.get("country_code")

            logger.debug(f"IP resolved: {ip} → {country}")

            return country

        logger.warning(
            f"IPINFO returned status={res.status_code} ip={ip} body={res.text}"
        )

    except requests.RequestException:
        logger.exception(f"Network error while resolving ip={ip}")

    except Exception:
        logger.exception("IPINFO request failed")

    return None


def get_client_ip(request: Request) -> str | None:
    """
    Extract client IP from common proxy/CDN headers
    """

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        logger.debug("Client IP resolved from cf-connecting-ip")
        return cf_ip.strip()

    xff = request.headers.get("x-forwarded-for")
    if xff:
        logger.debug("Client IP resolved from x-forwarded-for")
        return xff.split(",")[0].strip()

    xri = request.headers.get("x-real-ip")
    if xri:
        logger.debug("Client IP resolved from x-real-ip")
        return xri.strip()

    if request.client:
        client_ip = request.client.host
    else:
        logger.warning("request.client is None; defaulting client IP to None")
        client_ip = None

    logger.debug(f"Client IP resolved from request.client.host:- {client_ip}")

    return client_ip