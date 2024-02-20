from unittest import mock

import pytest
from redis.exceptions import ConnectionError, TimeoutError

from tests.mocks.mock_redis import MockRedis


@pytest.fixture(scope="module")
def mock_redis_client():
    with mock.patch(
        "app.shared.redis_client.redis_client", new_callable=MockRedis
    ) as mock_obj:
        yield mock_obj


def test_redis_set(mock_redis_client):
    result = mock_redis_client.set("key", "value")
    assert result is True


def test_redis_get(mock_redis_client):
    mock_redis_client.set("key", "value")
    get_result = mock_redis_client.get("key")
    assert get_result == "value"


def test_redis_delete(mock_redis_client):
    mock_redis_client.set("key", "value")
    result = mock_redis_client.delete("key")
    assert result == 1


def test_redis_set_connection_error(mock_redis_client):
    with pytest.raises(ConnectionError):
        mock_redis_client.set("error_key", "value")


def test_redis_get_timeout_error(mock_redis_client):
    with pytest.raises(TimeoutError):
        mock_redis_client.get("timeout_key")


def test_redis_delete_nonexistent_key(mock_redis_client):
    result = mock_redis_client.delete("nonexistent_key")
    assert result == 0
