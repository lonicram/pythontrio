"""Integration tests for FastAPI main application endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Test that the root endpoint returns a welcome message.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 200.
        - Response contains the expected welcome message with app name.
    """
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to PythonTrio"}


def test_health_endpoint(client: TestClient) -> None:
    """Test that the health endpoint returns healthy status.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 200.
        - Response contains status field with value 'healthy'.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
