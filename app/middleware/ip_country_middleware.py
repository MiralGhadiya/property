from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.ip_country import get_client_ip, get_ip_country


class IPCountryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            request.state.ip_country = None
            return await call_next(request)

        ip = get_client_ip(request)

        country = None
        if ip:
            country = get_ip_country(ip)

        request.state.ip_country = country

        response = await call_next(request)
        return response
