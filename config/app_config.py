from starlette.config import Config

config = Config(".env")

HOSTS = config(
    "HOSTS",
    cast=lambda v: [i.strip() for i in v.split(",")],
)

CELERY_BROKER_URL = config("CELERY_BROKER_URL", cast=str)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", cast=str)

CELERY_DEFAULT_RETRY_DELAY = config("CELERY_DEFAULT_RETRY_DELAY", cast=int, default=10)
CELERY_DEFAULT_MAX_RETRIES = config("CELERY_DEFAULT_MAX_RETRIES", cast=int, default=3)

REDIS_HOST = config("REDIS_HOST", cast=str, default="localhost")
REDIS_PORT = config("REDIS_PORT", cast=int, default=6379)
REDIS_DB = config("REDIS_DB", cast=int, default=0)
