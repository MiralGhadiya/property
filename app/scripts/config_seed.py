import os

from dotenv import dotenv_values

CONFIG_ENV_KEYS = (
    "ENV",
    "DATABASE_URL",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_SSLMODE",
    "POSTGRES_CONNECT_TIMEOUT",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_RECYCLE",
    "REDIS_URL",
    "NGINX_PORT",
    "BASE_URL",
    "FRONTEND_URL",
    "JWT_SECRET_KEY",
    "ALGORITHM",
    "EMAIL_USER",
    "EMAIL_PASSWORD",
    "ADMIN_FEEDBACK_EMAILS",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "IPINFO_TOKEN",
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "EXCHANGE_RATE_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "GOOGLE_CLIENT_ID",
    "LANGSMITH_TRACING",
    "LANGSMITH_API_KEY",
    "STARTUP_MAX_RETRIES",
    "STARTUP_RETRY_DELAY",
)


def load_config_seed_values() -> dict[str, str]:
    env_file_values = {
        key: value for key, value in dotenv_values(".env").items() if value is not None
    }

    if env_file_values:
        return env_file_values

    return {
        key: value for key in CONFIG_ENV_KEYS if (value := os.getenv(key)) is not None
    }
