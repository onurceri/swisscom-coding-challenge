FROM python:3.9-slim

WORKDIR /usr/src/app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENV HOSTS="host.docker.internal:8001,host.docker.internal:8002,host.docker.internal:8003"

ENV CELERY_BROKER_URL="amqp://guest:guest@rabbitmq/"
ENV CELERY_RESULT_BACKEND="redis://redis:6379/0"

ENV CELERY_DEFAULT_RETRY_DELAY=10
ENV CELERY_DEFAULT_MAX_RETRIES=3

ENV REDIS_HOST="redis"
ENV REDIS_PORT=6379
ENV REDIS_DB=0

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
