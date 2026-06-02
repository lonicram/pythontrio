"""Integration tests for user profiles API endpoints."""

from fastapi.testclient import TestClient

# ID that should never exist in the test database
NON_EXISTENT_ID = 99999


def test_list_user_profiles_empty(client: TestClient) -> None:
    """Test that listing user profiles returns an empty list when no profiles exist.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 200.
        - Response body is an empty list.
    """
    response = client.get("/user-profiles/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_user_profile_minimal(client: TestClient) -> None:
    """Test that creating a user profile with only required fields works.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 201.
        - Response contains the user profile with correct fields.
        - User profile has an assigned ID.
        - is_active defaults to True.
    """
    payload = {
        "email": "newuser@example.com",
    }

    response = client.post("/user-profiles/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] is None
    assert data["full_name"] is None
    assert data["is_active"] is True
    assert "id" in data
    assert isinstance(data["id"], int)
    assert "created_at" in data
    assert "updated_at" in data


def test_create_user_profile_full(client: TestClient) -> None:
    """Test that creating a user profile with all fields stores correctly.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 201.
        - All provided fields are stored correctly.
    """
    payload = {
        "email": "johndoe@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "is_active": True,
    }

    response = client.post("/user-profiles/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "johndoe@example.com"
    assert data["username"] == "johndoe"
    assert data["full_name"] == "John Doe"
    assert data["is_active"] is True


def test_create_user_profile_inactive(client: TestClient) -> None:
    """Test that creating an inactive user profile works.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 201.
        - is_active field is set to False.
    """
    payload = {
        "email": "inactive@example.com",
        "username": "inactiveuser",
        "is_active": False,
    }

    response = client.post("/user-profiles/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["is_active"] is False


def test_create_user_profile_duplicate_email(client: TestClient, created_user_profile: dict) -> None:
    """Test that creating a user profile with duplicate email returns 409.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 409 (Conflict).
        - Error detail message is appropriate.
    """
    payload = {
        "email": created_user_profile["email"],
        "username": "differentuser",
    }

    response = client.post("/user-profiles/", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


def test_create_user_profile_duplicate_username(client: TestClient, created_user_profile: dict) -> None:
    """Test that creating a user profile with duplicate username returns 409.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 409 (Conflict).
        - Error detail message is appropriate.
    """
    payload = {
        "email": "uniqueemail@example.com",
        "username": created_user_profile["username"],
    }

    response = client.post("/user-profiles/", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


def test_get_user_profile_by_id(client: TestClient, created_user_profile: dict) -> None:
    """Test that retrieving a user profile by ID returns the correct profile.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 200.
        - Response contains the user profile matching the requested ID.
    """
    user_id = created_user_profile["id"]

    response = client.get(f"/user-profiles/{user_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == created_user_profile["email"]
    assert data["username"] == created_user_profile["username"]


def test_get_user_profile_not_found(client: TestClient) -> None:
    """Test that retrieving a non-existent user profile returns 404.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    response = client.get(f"/user-profiles/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "User profile not found"


def test_update_user_profile_email(client: TestClient, created_user_profile: dict) -> None:
    """Test that updating only the email field works correctly.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 200.
        - Email is updated correctly.
        - Other fields remain unchanged.
    """
    user_id = created_user_profile["id"]

    update_payload = {
        "email": "newemail@example.com",
    }
    response = client.put(f"/user-profiles/{user_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "newemail@example.com"
    assert data["username"] == created_user_profile["username"]
    assert data["full_name"] == created_user_profile["full_name"]


def test_update_user_profile_multiple_fields(client: TestClient, created_user_profile: dict) -> None:
    """Test that updating multiple fields works correctly.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 200.
        - Multiple fields are updated correctly.
    """
    user_id = created_user_profile["id"]

    update_payload = {
        "full_name": "Updated Full Name",
        "is_active": False,
    }
    response = client.put(f"/user-profiles/{user_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["full_name"] == "Updated Full Name"
    assert data["is_active"] is False
    assert data["email"] == created_user_profile["email"]


def test_update_user_profile_duplicate_email(client: TestClient, created_user_profile: dict) -> None:
    """Test that updating to duplicate email returns 409.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 409 (Conflict).
        - Error detail message is appropriate.
    """
    # Create a second user profile
    second_payload = {
        "email": "seconduser@example.com",
        "username": "seconduser",
    }
    second_response = client.post("/user-profiles/", json=second_payload)
    assert second_response.status_code == 201
    second_user_id = second_response.json()["id"]

    # Try to update first user's email to match second user
    update_payload = {
        "email": created_user_profile["email"],
    }
    response = client.put(f"/user-profiles/{second_user_id}", json=update_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


def test_update_user_profile_duplicate_username(client: TestClient, created_user_profile: dict) -> None:
    """Test that updating to duplicate username returns 409.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 409 (Conflict).
        - Error detail message is appropriate.
    """
    # Create a second user profile
    second_payload = {
        "email": "seconduser@example.com",
        "username": "seconduser",
    }
    second_response = client.post("/user-profiles/", json=second_payload)
    assert second_response.status_code == 201
    second_user_id = second_response.json()["id"]

    # Try to update first user's username to match second user
    update_payload = {
        "username": created_user_profile["username"],
    }
    response = client.put(f"/user-profiles/{second_user_id}", json=update_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


def test_update_user_profile_not_found(client: TestClient) -> None:
    """Test that updating a non-existent user profile returns 404.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    update_payload = {
        "email": "newemail@example.com",
    }

    response = client.put(f"/user-profiles/{NON_EXISTENT_ID}", json=update_payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "User profile not found"


def test_update_user_profile_same_email(client: TestClient, created_user_profile: dict) -> None:
    """Test that updating a field while keeping the same email doesn't cause conflict.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 200.
        - Update succeeds when email is not actually changed.
    """
    user_id = created_user_profile["id"]

    update_payload = {
        "email": created_user_profile["email"],
        "full_name": "Updated Name",
    }
    response = client.put(f"/user-profiles/{user_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == created_user_profile["email"]
    assert data["full_name"] == "Updated Name"


def test_delete_user_profile(client: TestClient, created_user_profile: dict) -> None:
    """Test that deleting a user profile removes it from the database.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Delete response status code is 204.
        - Subsequent GET for the user profile returns 404.
    """
    user_id = created_user_profile["id"]

    delete_response = client.delete(f"/user-profiles/{user_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/user-profiles/{user_id}")
    assert get_response.status_code == 404


def test_delete_user_profile_not_found(client: TestClient) -> None:
    """Test that deleting a non-existent user profile returns 404.

    Args:
        client: FastAPI test client fixture.

    Verifies:
        - Response status code is 404.
        - Response contains appropriate error detail.
    """
    response = client.delete(f"/user-profiles/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "User profile not found"


def test_list_user_profiles_with_data(client: TestClient, created_user_profile: dict) -> None:
    """Test that listing user profiles returns all created profiles.

    Args:
        client: FastAPI test client fixture.
        created_user_profile: Fixture providing a pre-created user profile via API.

    Verifies:
        - Response status code is 200.
        - Response contains the created user profile.
    """
    response = client.get("/user-profiles/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(p["id"] == created_user_profile["id"] for p in data)
