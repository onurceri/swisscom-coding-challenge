import json
from unittest.mock import MagicMock, call, patch
import httpx
import pytest

from app.celery_tasks.create_task import (
    _handle_failed_rollback,
    _is_rollback_needed,
    _update_rollback_data,
    create_group,
    logger,
    rollback_create_group,
    trigger_rollback,
)
from app.clients.node_client import NodeClient
from app.shared.redis_client import redis_client
from config.app_config import HOSTS

# Fixtures


@pytest.fixture
def setup_redis(mocker):
    mocker.patch.object(redis_client, "exists", return_value=False)
    mocker.patch.object(redis_client, "set", return_value=None)
    mocker.patch.object(redis_client, "delete", return_value=None)
    mocker.patch.object(
        redis_client, "get", return_value=json.dumps({"group_id": "groupId", "nodes": ["node1", "node2"]})
    )


@pytest.fixture
def setup_node_client(mocker):
    mocker.patch.object(
        NodeClient, "create_group", return_value=MagicMock(status_code=200)
    )


@pytest.fixture
def mock_is_rollback_needed(mocker):
    mocker.patch("app.celery_tasks.create_task._is_rollback_needed", return_value=False)


@pytest.fixture
def mock_logger(mocker):
    mocker.patch.object(logger, "info")


@pytest.fixture
def group_id_node_setup():
    return "test_group_id", "test_node"


# Tests


@pytest.mark.parametrize(
    "status_code,group_exists,expected",
    [
        (400, False, True),  # Group does not exist, needs rollback
        (400, True, False),  # Group exists, no rollback needed
        (500, False, True),  # Server error, rollback needed
        (200, False, False),  # Success, no rollback needed
    ],
)
def test_is_rollback_needed(mocker, status_code, group_exists, expected):
    mocked_response = MagicMock(spec=httpx.Response, status_code=status_code)
    get_group_status_code = 200 if group_exists else 404
    mocked_get_group_response = MagicMock(
        spec=httpx.Response, status_code=get_group_status_code
    )
    mocker.patch.object(NodeClient, "get_group", return_value=mocked_get_group_response)
    node = "test_node"
    group_id = "test_group_id"
    result = _is_rollback_needed(node, group_id, mocked_response)
    assert result is expected


def test_create_group_skips_creation_if_rollback_data_exists(
    mocker, setup_redis, mock_logger
):
    mocker.patch.object(redis_client, "exists", return_value=True)
    group_id = "test_group_id"
    create_group(group_id)
    redis_client.exists.assert_called_once_with(f"rollback_create_group_{group_id}")
    logger.info.assert_called_once_with(
        f"Rollback data exists for group {group_id}, skipping creation."
    )


def test_create_group_processes_all_nodes_successfully(
    setup_redis, setup_node_client, mock_is_rollback_needed
):
    group_id = "test_group_id"
    create_group(group_id)
    assert NodeClient.create_group.call_count == len(HOSTS)
    redis_client.delete.assert_called_once_with(f"rollback_create_group_{group_id}")


def test_create_group_triggers_rollback_on_failure(mocker, setup_redis):
    group_id = "test_group_id"
    mocker.patch.object(
        NodeClient,
        "create_group",
        side_effect=[MagicMock(status_code=500)]
        + [MagicMock(status_code=200)] * (len(HOSTS) - 1),
    )
    mocker.patch("app.celery_tasks.create_task._is_rollback_needed", return_value=True)
    mock_trigger_rollback = mocker.patch(
        "app.celery_tasks.create_task.trigger_rollback"
    )
    create_group(group_id)
    mock_trigger_rollback.assert_called_once_with(group_id, [])
    redis_client.set.assert_called_once_with(
        f"rollback_create_group_{group_id}", json.dumps([])
    )


@patch("app.celery_tasks.create_task.rollback_create_group.retry")
@patch("app.celery_tasks.create_task.redis_client.delete")
@patch("app.celery_tasks.create_task.celery_app.send_task")
def test_handle_failed_rollback_retry_behavior(
    mock_send_task, mock_redis_delete, mock_retry
):
    group_id = "test_group_id"
    node = "test_node"
    _handle_failed_rollback(group_id, node)
    mock_retry.assert_called()


@pytest.mark.usefixtures("setup_redis")
def test_update_rollback_data_remove_node():
    group_id = "test_group_id"
    node_to_remove = "node1"
    _update_rollback_data(group_id, node_to_remove)
    expected_data = {"group_id": "groupId", "nodes": ["node2"]}
    redis_client.set.assert_called_once_with(
        f"rollback_create_group_{group_id}", json.dumps(expected_data)
    )


@pytest.mark.usefixtures("setup_redis")
def test_update_rollback_data_remove_last_node(mocker):
    group_id = "test_group_id"
    mocker.patch.object(
        redis_client,
        "get",
        return_value=json.dumps({"group_id": "group_id", "nodes": ["node1"]}),
    )

    node_to_remove = "node1"
    _update_rollback_data(group_id, node_to_remove)
    redis_client.delete.assert_called_once_with(f"rollback_create_group_{group_id}")


@patch("app.celery_tasks.create_task._handle_failed_rollback")
@patch("app.celery_tasks.create_task._update_rollback_data")
@patch("app.clients.node_client.NodeClient.delete_group")
def test_rollback_create_group_success(
    mock_delete_group,
    mock_update_rollback_data,
    mock_handle_failed_rollback,
    group_id_node_setup,
    mocker,
):
    group_id, node = group_id_node_setup
    mock_delete_group.return_value = MagicMock(status_code=200)
    mocker.patch.object(
        redis_client, "get", return_value=json.dumps({"nodes": ["test_node"]})
    )
    rollback_create_group(group_id, node)
    mock_delete_group.assert_called_once_with(node, group_id)
    mock_update_rollback_data.assert_called_once_with(group_id, node)
    mock_handle_failed_rollback.assert_not_called()


@patch("app.celery_tasks.create_task._handle_failed_rollback")
@patch("app.celery_tasks.create_task._update_rollback_data")
@patch("app.clients.node_client.NodeClient.delete_group")
def test_rollback_create_group_failure(
    mock_delete_group,
    mock_update_rollback_data,
    mock_handle_failed_rollback,
    group_id_node_setup,
    mocker,
):
    group_id, node = group_id_node_setup
    mock_delete_group.return_value = MagicMock(status_code=500)
    mocker.patch.object(
        redis_client, "get", return_value=json.dumps({"nodes": ["test_node"]})
    )
    rollback_create_group(group_id, node)
    mock_delete_group.assert_called_once_with(node, group_id)
    mock_update_rollback_data.assert_not_called()
    mock_handle_failed_rollback.assert_called_once_with(group_id, node)


@patch("app.celery_tasks.create_task.logger.info")
def test_rollback_create_group_no_rollback_data(
    mock_logger_info, mocker, group_id_node_setup
):
    group_id, node = group_id_node_setup
    mocker.patch.object(redis_client, "get", return_value=None)
    rollback_create_group(group_id, node)
    mock_logger_info.assert_called_with(
        f"Rollback data doesn't exist for group {group_id}, skipping rollback. Node: {node}"
    )


@patch("app.shared.redis_client.redis_client.set")
@patch("app.celery_tasks.celery_app.celery_app.send_task")
def test_trigger_rollback(mock_send_task, mock_redis_set, group_id_node_setup):
    group_id, nodes_processed = group_id_node_setup
    trigger_rollback(group_id, nodes_processed)
    mock_redis_set.assert_called_once_with(
        f"rollback_create_group_{group_id}",
        json.dumps({"group_id": group_id, "nodes": nodes_processed}),
        ex=60 * 60,
    )
    assert mock_send_task.call_count == len(nodes_processed)
    calls = [
        call(
            "app.celery_tasks.create_task.rollback_create_group",
            kwargs={"group_id": group_id, "node": node},
        )
        for node in nodes_processed
    ]
    mock_send_task.assert_has_calls(calls, any_order=True)
