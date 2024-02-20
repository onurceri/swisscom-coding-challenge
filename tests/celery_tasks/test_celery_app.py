import unittest

from app.celery_tasks.celery_app import celery_app
from config.app_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND


class TestCeleryConfiguration(unittest.TestCase):
    def setUp(self):
        self.celery_config = celery_app.conf

    def test_broker_url(self):
        self.assertEqual(self.celery_config.broker_url, CELERY_BROKER_URL)

    def test_result_backend(self):
        self.assertEqual(self.celery_config.result_backend, CELERY_RESULT_BACKEND)

    def test_task_discovery(self):
        my_tasks = [
            "app.celery_tasks.create_task.rollback_create_group",
            "app.celery_tasks.dead_letter_task.process_dead_letter",
            "app.celery_tasks.delete_task.rollback_delete_group",
            "app.celery_tasks.create_task.create_group",
            "app.celery_tasks.delete_task.delete_group",
        ]
        discovered_tasks = list(celery_app.tasks.keys())
        self.assertTrue(all(task in discovered_tasks for task in my_tasks))
