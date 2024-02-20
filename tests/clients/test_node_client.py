import pytest
from app.clients.node_client import NodeClient
from httpx import Client
from tests.mocks.mock_transports import CustomTransport


@pytest.fixture
def client():
    custom_transport = CustomTransport()
    with NodeClient(httpx_client=Client(transport=custom_transport)) as client_instance:
        yield client_instance


def test_create_group_success(client):
    response = client.create_group(node="node", group_id="new-group")
    assert response.status_code == 201
    assert response.json() == {"message": "Group created"}


def test_create_group_bad_request(client):
    response = client.create_group(node="node", group_id="existing-group")
    assert response.status_code == 400
    assert response.json() == {"message": "Bad request. Perhaps the object exists."}


def test_create_group_internal_server_error(client):
    response = client.create_group(node="node", group_id="trigger-500")
    assert response.status_code == 500
    assert response.json() == {"message": "Internal Server Error"}


def test_create_group_bad_gateway_error(client):
    response = client.create_group(node="node", group_id="trigger-408")
    assert response.status_code == 408
    assert response.json() == {"message": "Request Timeout"}


def test_delete_group_success(client):
    response = client.delete_group(node="node", group_id="any-group")
    assert response.status_code == 200
    assert response.json() == {"message": "Group deleted"}


def test_get_group_success(client):
    response = client.get_group(node="node", group_id="existing-group")
    assert response.status_code == 200
    assert response.json() == {"groupId": "existing-group"}


def test_get_group_not_found(client):
    response = client.get_group(node="node", group_id="nonexistent-group")
    assert response.status_code == 404
    assert response.json() == {"message": "Not found"}
