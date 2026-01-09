"""Tests for authentication API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    """Tests for user registration."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert "id" in data["user"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "anotherpassword123",
                "name": "Another User",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123",
                "name": "Test User",
            },
        )
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "test2@example.com",
                "password": "short",
                "name": "Test User",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for user login."""

    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword123",
            },
        )
        assert response.status_code == 401


class TestMe:
    """Tests for current user endpoint."""

    async def test_get_current_user(self, authenticated_client: AsyncClient, test_user):
        """Test getting current user info."""
        response = await authenticated_client.get("/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without auth."""
        response = await client.get("/v1/auth/me")
        assert response.status_code == 401


class TestRefreshToken:
    """Tests for token refresh."""

    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = await client.post(
            "/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Refresh the token
        response = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
