"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

# Create test client
client = TestClient(app)


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities_returns_all_activities(self):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_activities_have_required_fields(self):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Basketball Team" in data["message"]

    def test_signup_adds_participant(self):
        """Test that signup actually adds the participant"""
        email = "newtestuser@mergington.edu"
        response = client.post(
            f"/activities/Tennis%20Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities = client.get("/activities").json()
        assert email in activities["Tennis Club"]["participants"]

    def test_signup_duplicate_fails(self):
        """Test that signing up twice fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Art%20Studio/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Art%20Studio/signup?email={email}"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]

    def test_signup_invalid_activity_fails(self):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_signup_existing_participants(self):
        """Test signup with activities that already have participants"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=alice@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify existing participants are still there
        activities = client.get("/activities").json()
        chess_participants = activities["Chess Club"]["participants"]
        assert "michael@mergington.edu" in chess_participants
        assert "daniel@mergington.edu" in chess_participants


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self):
        """Test successful unregistration from an activity"""
        email = "unregister_test@mergington.edu"
        
        # First sign up
        client.post(
            f"/activities/Drama%20Club/signup?email={email}"
        )
        
        # Then unregister
        response = client.post(
            f"/activities/Drama%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]

    def test_unregister_removes_participant(self):
        """Test that unregister actually removes the participant"""
        email = "removal_test@mergington.edu"
        
        # Sign up
        client.post(
            f"/activities/Debate%20Team/signup?email={email}"
        )
        
        # Verify participant is there
        activities = client.get("/activities").json()
        assert email in activities["Debate Team"]["participants"]
        
        # Unregister
        client.post(
            f"/activities/Debate%20Team/unregister?email={email}"
        )
        
        # Verify participant was removed
        activities = client.get("/activities").json()
        assert email not in activities["Debate Team"]["participants"]

    def test_unregister_not_registered_fails(self):
        """Test that unregistering someone not registered fails"""
        response = client.post(
            "/activities/Science%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_invalid_activity_fails(self):
        """Test that unregistering from non-existent activity fails"""
        response = client.post(
            "/activities/Fake%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_unregister_existing_participant(self):
        """Test unregistering an existing participant"""
        response = client.post(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify they were removed
        activities = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_signup_and_unregister_flow(self):
        """Test complete flow of signup and unregister"""
        email = "integration_test@mergington.edu"
        activity = "Programming%20Class"
        
        # Get initial state
        initial = client.get("/activities").json()
        initial_count = len(initial["Programming Class"]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify count increased
        after_signup = client.get("/activities").json()
        assert len(after_signup["Programming Class"]["participants"]) == initial_count + 1
        assert email in after_signup["Programming Class"]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify count is back to initial
        after_unregister = client.get("/activities").json()
        assert len(after_unregister["Programming Class"]["participants"]) == initial_count
        assert email not in after_unregister["Programming Class"]["participants"]

    def test_multiple_signups_and_unregisters(self):
        """Test multiple users signing up and unregistering"""
        activity = "Art%20Studio"
        emails = [
            "user1@mergington.edu",
            "user2@mergington.edu",
            "user3@mergington.edu",
        ]
        
        # Sign up multiple users
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are registered
        activities = client.get("/activities").json()
        for email in emails:
            assert email in activities["Art Studio"]["participants"]
        
        # Unregister one
        client.post(f"/activities/{activity}/unregister?email={emails[1]}")
        
        # Verify the right one was removed
        activities = client.get("/activities").json()
        assert emails[0] in activities["Art Studio"]["participants"]
        assert emails[1] not in activities["Art Studio"]["participants"]
        assert emails[2] in activities["Art Studio"]["participants"]


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirect(self):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
