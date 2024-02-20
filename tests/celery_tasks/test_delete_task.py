import json
from unittest.mock import patch, MagicMock, call
import unittest
from app.celery_tasks.delete_task import (
    delete_group,
    rollback_delete_group,
    trigger_rollback,
)


@patch("app.celery_tasks.delete_task.node_client.delete_group")
@patch("app.celery_tasks.delete_task.logger")
@patch("app.celery_tasks.delete_task.trigger_rollback")
@patch("app.celery_tasks.delete_task.HOSTS", ["node1", "node2"])
def test_all_nodes_success(mock_trigger_rollback, mock_logger, mock_delete_group):
    mock_delete_group.return_value = MagicMock(status_code=200)
    delete_group("group123")
    calls = [
        call("Group group123 deleted on node1"),
        call("Group group123 deleted on node2"),
    ]
    mock_logger.info.assert_has_calls(calls, any_order=True)
    mock_trigger_rollback.assert_not_called()


@patch("app.celery_tasks.delete_task.node_client.delete_group")
@patch("app.celery_tasks.delete_task.logger")
@patch("app.celery_tasks.delete_task.trigger_rollback")
@patch("app.celery_tasks.delete_task.HOSTS", ["node1", "node2"])
def test_partial_success_trigger_rollback(
    mock_trigger_rollback, mock_logger, mock_delete_group
):
    mock_delete_group.side_effect = [
        MagicMock(status_code=200),
        MagicMock(status_code=404),
    ]
    delete_group("group123")
    mock_logger.error.assert_called_with(
        "Group group123 could not be deleted on node2. Retrying..."
    )
    mock_trigger_rollback.assert_called_once_with("group123", ["node1"])


@patch("app.celery_tasks.delete_task.node_client.delete_group")
@patch("app.celery_tasks.delete_task.logger")
@patch("app.celery_tasks.delete_task.trigger_rollback")
@patch("app.celery_tasks.delete_task.HOSTS", ["node1"])
def test_failure_no_success_nodes(
    mock_trigger_rollback, mock_logger, mock_delete_group
):
    mock_delete_group.return_value = MagicMock(status_code=404)
    delete_group("group123")
    mock_logger.error.assert_called_with(
        "Group group123 could not be deleted on node1. Retrying..."
    )
    mock_trigger_rollback.assert_called_once_with("group123", [])


@patch("app.celery_tasks.delete_task.redis_client.set")
@patch("app.celery_tasks.delete_task.celery_app.send_task")
def test_trigger_rollback(mock_send_task, mock_set):
    trigger_rollback("group123", ["node1", "node2"])
    mock_set.assert_called_once()
    args, kwargs = mock_send_task.call_args
    assert args[0] == "app.celery_tasks.delete_task.rollback_delete_group"
    assert kwargs["kwargs"] == {"group_id": "group123", "node": "node1"} or {
        "group_id": "group123",
        "node": "node2",
    }


@patch("app.celery_tasks.delete_task.node_client.create_group")
@patch("app.celery_tasks.delete_task.redis_client.get")
@patch("app.celery_tasks.delete_task.redis_client.set")
@patch("app.celery_tasks.delete_task.redis_client.delete")
@patch("app.celery_tasks.delete_task.logger")
def test_rollback_success(
    mock_logger, mock_delete, mock_set, mock_get, mock_create_group
):
    mock_get.return_value = json.dumps({"group_id": "group123", "nodes": ["node1"]})
    mock_create_group.return_value = MagicMock(status_code=201)
    rollback_delete_group("group123", "node1")
    mock_delete.assert_called_once_with("rollback_delete_group_group123")


@patch("app.celery_tasks.delete_task.node_client.create_group")
@patch("app.celery_tasks.delete_task.redis_client.get")
@patch("app.celery_tasks.delete_task.redis_client.delete")
@patch("app.celery_tasks.delete_task.logger")
def test_rollback_failure_with_retry(
    mock_logger, mock_delete, mock_get, mock_create_group
):
    mock_get.return_value = json.dumps({"group_id": "group123", "nodes": ["node1"]})
    mock_create_group.return_value = MagicMock(status_code=500)
    with patch(
        "app.celery_tasks.delete_task.rollback_delete_group.retry"
    ) as mock_retry:
        rollback_delete_group("group123", "node1")
        mock_retry.assert_called_once()
        mock_delete.assert_not_called()


@patch("app.celery_tasks.delete_task.redis_client.get")
@patch("app.celery_tasks.delete_task.logger")
def test_no_rollback_data_found(mock_logger, mock_get):
    mock_get.return_value = None
    rollback_delete_group("group123", "node1")
    mock_logger.info.assert_called_with("No rollback needed for group group123.")


@patch("app.celery_tasks.delete_task.redis_client.get")
@patch("app.celery_tasks.delete_task.logger")
def test_invalid_rollback_data(mock_logger, mock_get):
    mock_get.return_value = "invalid json"
    rollback_delete_group("group123", "node1")
    mock_logger.error.assert_called_with(
        "Failed to decode or validate rollback item: rollback_delete_group_group123"
    )


@patch("app.celery_tasks.delete_task.redis_client.get")
@patch("app.celery_tasks.delete_task.logger")
def test_rollback_data_missing_group_id_or_nodes(mock_logger, mock_get):
    mock_get.return_value = json.dumps({"invalid": "data"})
    rollback_delete_group("group123", "node1")
    mock_logger.error.assert_called_with(
        "Invalid rollback data for group group123: {'invalid': 'data'}"
    )


@patch("app.celery_tasks.delete_task.redis_client.get")
@patch("app.celery_tasks.delete_task.node_client.create_group")
@patch("app.celery_tasks.delete_task.logger")
def test_node_not_in_rollback_nodes(mock_logger, mock_create_group, mock_get):
    mock_get.return_value = json.dumps({"group_id": "group123", "nodes": ["node2"]})
    rollback_delete_group("group123", "node1")
    mock_logger.info.assert_called_with(
        "Node node1 not in rollback data for group group123, skipping rollback."
    )
    mock_create_group.assert_not_called()


if __name__ == "__main__":
    unittest.main()
