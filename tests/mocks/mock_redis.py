from redis.exceptions import ConnectionError, TimeoutError


class MockRedis:
    def __init__(self, *args, **kwargs):
        self.data = {"existing_key": "value"}

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        if name == "error_key":
            raise ConnectionError("Failed to connect to Redis")
        self.data[name] = value
        return True

    def get(self, name):
        if name == "timeout_key":
            raise TimeoutError("Redis operation timed out")
        return self.data.get(name)

    def delete(self, name):
        if name == "nonexistent_key":
            return 0
        return self.data.pop(name, None) is not None

    def exists(self, name):
        return name in self.data
