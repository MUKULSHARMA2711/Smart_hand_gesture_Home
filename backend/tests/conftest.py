from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

SendCommand = Callable[..., httpx.Response]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, sensor_seed=42)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """A fresh app per test, so in-memory state never leaks between tests."""
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def send_command(client: TestClient) -> SendCommand:
    def send(device_id: str, action: str, **body: object) -> httpx.Response:
        return client.post(f"/api/v1/devices/{device_id}/command", json={"action": action, **body})

    return send
