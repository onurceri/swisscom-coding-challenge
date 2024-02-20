import json
from httpx import Request, Response, ConnectError


class CustomTransport:
    def handle_request(self, request: Request):
        if "connection-error" in request.url.path:
            raise ConnectError("Connection failed")

        # Create group - POST
        if request.url.path == "/v1/group/" and request.method == "POST":
            request_body = json.loads(request.content.decode())
            group_id = request_body["groupId"]
            if group_id == "existing-group":
                return Response(
                    400, json={"message": "Bad request. Perhaps the object exists."}
                )
            elif group_id == "trigger-500":
                return Response(500, json={"message": "Internal Server Error"})
            elif group_id == "trigger-408":
                return Response(408, json={"message": "Request Timeout"})

            return Response(201, json={"message": "Group created"})

        # Delete group - DELETE
        elif request.url.path == "/v1/group/" and request.method == "DELETE":
            return Response(200, json={"message": "Group deleted"})

        # Get group - GET
        elif request.url.path.startswith("/v1/group/") and request.method == "GET":
            group_id = request.url.path.split("/")[-1]
            if group_id == "nonexistent-group":
                return Response(404, json={"message": "Not found"})
            return Response(200, json={"groupId": group_id})

        return Response(404, json={"message": "Not Found"})

    def close(self):
        pass