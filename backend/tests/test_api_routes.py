import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class TestAuthRoutes:

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @pytest.fixture
    def valid_token(self, client):
        from config import settings
        response = client.post(
            "/api/v1/auth/token",
            json={"app_secret": settings.api_token}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        return "test-token"

    def test_token_generation_success(self, client):
        from config import settings
        response = client.post(
            "/api/v1/auth/token",
            json={"app_secret": settings.api_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_token_generation_invalid_secret(self, client):
        response = client.post(
            "/api/v1/auth/token",
            json={"app_secret": "wrong-secret"}
        )
        assert response.status_code == 401

    def test_auth_status_endpoint(self, client, valid_token):
        response = client.get(
            "/api/v1/auth/status",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "authenticated" in data


class TestSecurityRoutes:

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @pytest.fixture
    def valid_token(self, client):
        from config import settings
        response = client.post(
            "/api/v1/auth/token",
            json={"app_secret": settings.api_token}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        return "test-token"

    def test_security_levels_endpoint(self, client, valid_token):
        response = client.get(
            "/api/v1/security/levels",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "levels" in data
        assert len(data["levels"]) == 4

    def test_security_levels_contain_required_info(self, client, valid_token):
        response = client.get(
            "/api/v1/security/levels",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        data = response.json()
        for level in data["levels"]:
            assert "level" in level
            assert "name" in level
            assert "description" in level
            assert "quantum_safe" in level


class TestEmailRoutes:

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @pytest.fixture
    def valid_token(self, client):
        from config import settings
        response = client.post(
            "/api/v1/auth/token",
            json={"app_secret": settings.api_token}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        return "test-token"

    def test_list_emails_requires_auth(self, client):
        response = client.get("/api/v1/emails")
        assert response.status_code in [401, 403]

    def test_send_email_requires_auth(self, client):
        response = client.post(
            "/api/v1/emails/send",
            data={
                "to": ["test@example.com"],
                "subject": "Test",
                "body": "Test body",
                "security_level": 4,
            }
        )
        assert response.status_code in [401, 403, 422]


class TestAPIValidation:

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @pytest.fixture
    def valid_token(self, client):
        from config import settings
        response = client.post(
            "/api/v1/auth/token",
            json={"app_secret": settings.api_token}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        return "test-token"

    def test_invalid_security_level_rejected(self, client, valid_token):
        response = client.post(
            "/api/v1/emails/send",
            headers={"Authorization": f"Bearer {valid_token}"},
            data={
                "to": ["test@example.com"],
                "subject": "Test",
                "body": "Test body",
                "security_level": 5,
            }
        )
        assert response.status_code in [400, 422]

    def test_security_refresh_invalid_type(self, client, valid_token):
        response = client.post(
            "/api/v1/security/refresh-keys",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"key_type": "invalid", "size": 100}
        )
        assert response.status_code == 400


class TestHealthCheck:

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
