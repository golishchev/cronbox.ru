"""Tests for custom exceptions."""
import pytest
from fastapi import status

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PlanLimitError,
    RateLimitError,
    UnauthorizedError,
)


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_default_message(self):
        """Test default error message."""
        error = NotFoundError()

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.detail == "Resource not found"

    def test_custom_message(self):
        """Test custom error message."""
        error = NotFoundError("Task not found")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.detail == "Task not found"


class TestUnauthorizedError:
    """Tests for UnauthorizedError."""

    def test_default_message(self):
        """Test default error message."""
        error = UnauthorizedError()

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.detail == "Could not validate credentials"

    def test_custom_message(self):
        """Test custom error message."""
        error = UnauthorizedError("Invalid token")

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.detail == "Invalid token"

    def test_www_authenticate_header(self):
        """Test WWW-Authenticate header is set."""
        error = UnauthorizedError()

        assert error.headers is not None
        assert error.headers.get("WWW-Authenticate") == "Bearer"


class TestForbiddenError:
    """Tests for ForbiddenError."""

    def test_default_message(self):
        """Test default error message."""
        error = ForbiddenError()

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Access forbidden"

    def test_custom_message(self):
        """Test custom error message."""
        error = ForbiddenError("You cannot access this workspace")

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "You cannot access this workspace"


class TestBadRequestError:
    """Tests for BadRequestError."""

    def test_default_message(self):
        """Test default error message."""
        error = BadRequestError()

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.detail == "Bad request"

    def test_custom_message(self):
        """Test custom error message."""
        error = BadRequestError("Invalid schedule format")

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.detail == "Invalid schedule format"


class TestConflictError:
    """Tests for ConflictError."""

    def test_default_message(self):
        """Test default error message."""
        error = ConflictError()

        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.detail == "Resource already exists"

    def test_custom_message(self):
        """Test custom error message."""
        error = ConflictError("Email already registered")

        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.detail == "Email already registered"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_default_message(self):
        """Test default error message."""
        error = RateLimitError()

        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.detail == "Rate limit exceeded"

    def test_custom_message(self):
        """Test custom error message."""
        error = RateLimitError("Too many login attempts")

        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.detail == "Too many login attempts"


class TestPlanLimitError:
    """Tests for PlanLimitError."""

    def test_default_message(self):
        """Test default error message."""
        error = PlanLimitError()

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Plan limit exceeded"

    def test_custom_message(self):
        """Test custom error message."""
        error = PlanLimitError("Maximum tasks reached for free plan")

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Maximum tasks reached for free plan"


class TestExceptionsAreHTTPException:
    """Test all custom exceptions inherit from HTTPException."""

    def test_all_exceptions_are_http_exception(self):
        """Test all exceptions are HTTPException subclasses."""
        from fastapi import HTTPException

        exceptions = [
            NotFoundError,
            UnauthorizedError,
            ForbiddenError,
            BadRequestError,
            ConflictError,
            RateLimitError,
            PlanLimitError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, HTTPException)

    def test_exceptions_are_raisable(self):
        """Test exceptions can be raised and caught."""
        with pytest.raises(NotFoundError):
            raise NotFoundError("Test")

        with pytest.raises(UnauthorizedError):
            raise UnauthorizedError("Test")

        with pytest.raises(ForbiddenError):
            raise ForbiddenError("Test")

        with pytest.raises(BadRequestError):
            raise BadRequestError("Test")

        with pytest.raises(ConflictError):
            raise ConflictError("Test")

        with pytest.raises(RateLimitError):
            raise RateLimitError("Test")

        with pytest.raises(PlanLimitError):
            raise PlanLimitError("Test")
