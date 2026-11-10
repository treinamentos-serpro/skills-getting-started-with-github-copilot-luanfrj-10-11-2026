from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["student@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore drawing, painting, and other visual arts",
        "schedule": "Mondays, 3:30 PM - 4:30 PM",
        "max_participants": 15,
        "participants": [],
    },
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(INITIAL_ACTIVITIES))

    with TestClient(app_module.app) as test_client:
        yield test_client


def test_root_redirects_to_frontend(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_data_and_no_store_header(client):
    # Arrange
    expected_activities = deepcopy(INITIAL_ACTIVITIES)

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == expected_activities


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Art Club"
    email = "newstudent@mergington.edu"

    # Act
    signup_response = client.post(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )
    activities_response = client.get("/activities")

    # Assert
    assert signup_response.status_code == 200
    assert signup_response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in activities_response.json()[activity_name]["participants"]


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_returns_not_found_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.post(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_delete_removes_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "student@mergington.edu"

    # Act
    delete_response = client.delete(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )
    activities_response = client.get("/activities")

    # Assert
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "message": f"Removed {email} from {activity_name}"
    }
    assert email not in activities_response.json()[activity_name]["participants"]


def test_delete_returns_not_found_for_unregistered_participant(client):
    # Arrange
    activity_name = "Art Club"
    email = "student@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_delete_returns_not_found_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.delete(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


@pytest.mark.parametrize("method", ["post", "delete"])
def test_signup_and_delete_require_email(client, method):
    # Arrange
    activity_name = "Art Club"
    request_path = f"/activities/{activity_name.replace(' ', '%20')}/signup"

    # Act
    response = getattr(client, method)(request_path)

    # Assert
    assert response.status_code == 422