import json
from unittest.mock import patch

from app.celery_tasks.dead_letter_task import process_dead_letter


@patch("app.celery_tasks.dead_letter_task.redis_client.get")
@patch("app.celery_tasks.dead_letter_task.redis_client.delete")
@patch("app.celery_tasks.dead_letter_task.redis_client.set")
@patch("app.celery_tasks.dead_letter_task.logger")
def test_no_rollback_item_found(mock_logger, mock_set, mock_delete, mock_get):
    mock_get.return_value = None
    process_dead_letter("group123", "nodeA", "task1")
    mock_logger.info.assert_called_with("No rollback item found for task1_group123")


@patch("app.celery_tasks.dead_letter_task.redis_client.get")
@patch("app.celery_tasks.dead_letter_task.redis_client.delete")
@patch("app.celery_tasks.dead_letter_task.redis_client.set")
@patch("app.celery_tasks.dead_letter_task.logger")
def test_invalid_rollback_item_format(mock_logger, mock_set, mock_delete, mock_get):
    mock_get.return_value = '{"invalid": "data"}'
    process_dead_letter("group123", "nodeA", "task1")
    mock_logger.error.assert_called_with(
        "Failed to decode or validate rollback item: task1_group123"
    )


@patch("app.celery_tasks.dead_letter_task.redis_client.get")
@patch("app.celery_tasks.dead_letter_task.redis_client.delete")
@patch("app.celery_tasks.dead_letter_task.redis_client.set")
@patch("app.celery_tasks.dead_letter_task.logger")
def test_node_not_in_rollback_item_nodes(mock_logger, mock_set, mock_delete, mock_get):
    mock_get.return_value = json.dumps({"nodes": ["nodeB", "nodeC"]})
    process_dead_letter("group123", "nodeA", "task1")
    mock_logger.info.assert_called_with(
        "Node nodeA not found in rollback item nodes for task1_group123"
    )


@patch("app.celery_tasks.dead_letter_task.redis_client.get")
@patch("app.celery_tasks.dead_letter_task.redis_client.delete")
@patch("app.celery_tasks.dead_letter_task.redis_client.set")
@patch("app.celery_tasks.dead_letter_task.logger")
def test_delete_rollback_item_no_nodes_left(
    mock_logger, mock_set, mock_delete, mock_get
):
    mock_get.return_value = json.dumps({"nodes": ["nodeA"]})
    process_dead_letter("group123", "nodeA", "task1")
    mock_delete.assert_called_once_with("task1_group123")
    mock_logger.info.assert_called_with(
        "Deleted task1_group123 from Redis as no nodes are left."
    )


@patch("app.celery_tasks.dead_letter_task.redis_client.get")
@patch("app.celery_tasks.dead_letter_task.redis_client.delete")
@patch("app.celery_tasks.dead_letter_task.redis_client.set")
@patch("app.celery_tasks.dead_letter_task.logger")
def test_update_rollback_item_with_remaining_nodes(
    mock_logger, mock_set, mock_delete, mock_get
):
    mock_get.return_value = json.dumps({"nodes": ["nodeA", "nodeB"]})
    process_dead_letter("group123", "nodeA", "task1")
    mock_set.assert_called_once_with("task1_group123", json.dumps({"nodes": ["nodeB"]}))
    mock_logger.info.assert_called_with(
        "Updated task1_group123 in Redis with remaining nodes."
    )
