import logging
from httpx import Client, ConnectError, Response


logger = logging.getLogger(__name__)


class NodeClient:
    def __init__(self, httpx_client: Client = None):
        self._httpx_client = httpx_client or Client()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._httpx_client.close()

    def _handle_request(self, method, url, **kwargs) -> Response:
        """
        Handle HTTP request with error handling.
        """
        try:
            response = self._httpx_client.request(method, url, **kwargs)
            return response
        except ConnectError as exc:
            logger.error("Failed to connect to node")
            return Response(status_code=500, content=str(exc))

    def create_group(self, node: str, group_id: str) -> Response:
        logger.info(f"Creating group {group_id} on {node}")
        url = f"http://{node}/v1/group/"
        data = {"groupId": group_id}
        return self._handle_request("POST", url, json=data)

    def delete_group(self, node: str, group_id: str) -> Response:
        logger.info(f"Deleting group {group_id} on {node}")
        url = f"http://{node}/v1/group/"
        data = {"groupId": group_id}
        return self._handle_request("DELETE", url, json=data)

    def get_group(self, node: str, group_id: str) -> Response:
        logger.info(f"Getting group {group_id} on {node}")
        url = f"http://{node}/v1/group/{group_id}"
        return self._handle_request("GET", url)
