"""CORS: the local dev origins (Vite on 5173, or 5174 when 5173 is busy) and nothing else."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app

# The endpoints the dashboard polls; their preflights failed with 400 from localhost:5174.
POLLED_PATHS = ["/home/state", "/events", "/ml/anomalies", "/ai/history", "/gestures/events"]


def preflight(client: TestClient, origin: str, path: str = "/home/state", method: str = "GET"):
    return client.options(
        f"/api/v1{path}",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
)
def test_preflight_from_local_dev_origins_succeeds(client: TestClient, origin: str) -> None:
    response = preflight(client, origin, method="POST")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    # Credentials behaviour is unchanged: the API does not use cookies.
    assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize("path", POLLED_PATHS)
def test_preflight_from_port_5174_succeeds_for_every_polled_endpoint(client: TestClient, path: str) -> None:
    # Regression: Vite fell back to 5174 and every preflight was rejected with 400.
    response = preflight(client, "http://localhost:5174", path)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"


@pytest.mark.parametrize("origin", ["http://evil.example", "http://localhost:3000", "https://localhost:5173"])
def test_unapproved_origin_is_rejected(client: TestClient, origin: str) -> None:
    response = preflight(client, origin)

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    # A simple request still gets no CORS grant, so the browser withholds the response.
    assert "access-control-allow-origin" not in client.get("/api/v1/home/state", headers={"Origin": origin}).headers


def test_allowed_origins_come_from_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMARTHOME_CORS_ORIGINS", '["https://home.example/"]')
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert preflight(client, "https://home.example").status_code == 200  # trailing slash normalised
        assert preflight(client, "http://localhost:5173").status_code == 400


def test_wildcard_origin_is_refused() -> None:
    with pytest.raises(ValidationError, match="not permitted"):
        Settings(_env_file=None, cors_origins=["*"])
