from celery import Celery

from config.app_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Initialize Celery
celery_app = Celery(
    "SwisscomApp", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)

# Import tasks
celery_app.autodiscover_tasks(
    [
        "app.celery_tasks.create_task",
        "app.celery_tasks.delete_task",
        "app.celery_tasks.dead_letter_task",
    ],
    force=True,
)
