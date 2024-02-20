from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_group():
    test_group_id = "test_group_id"
    mock_task_id = "mock_task_id"
    with patch("app.api.routers.groups.create_group.delay") as mock_create:
        mock_create.return_value = MagicMock(id=mock_task_id)
        response = client.post("/groups/create", json={"group_id": test_group_id})
        assert response.status_code == 200
        assert response.json() == {"task_id": mock_task_id}
        mock_create.assert_called_once_with(test_group_id)


def test_delete_group():
    test_group_id = "test_group_id"
    mock_task_id = "mock_task_id"
    with patch("app.api.routers.groups.delete_group.delay") as mock_delete:
        mock_delete.return_value = MagicMock(id=mock_task_id)
        response = client.post("/groups/delete", json={"group_id": test_group_id})
        assert response.status_code == 200
        assert response.json() == {"task_id": mock_task_id}
        mock_delete.assert_called_once_with(test_group_id)


def test_get_task_status():
    task_id = "some_task_id"
    mock_result = {
        "task_id": task_id,
        "state": "SUCCESS",
        "status": "Completed",
    }
    with patch("app.api.routers.groups.celery_app") as mock_async_result:
        mock_async_result.AsyncResult.return_value = MagicMock(
            id="some_task_id", state="SUCCESS", status="Completed"
        )
        response = client.get(f"/groups/task/{task_id}")
        assert response.status_code == 200
        assert response.json() == mock_result
