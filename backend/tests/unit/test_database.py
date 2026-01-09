"""Tests for database module."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestEngineConfiguration:
    """Tests for database engine configuration."""

    def test_engine_exists(self):
        """Test database engine is created."""
        from app.db.database import engine

        assert engine is not None

    def test_async_session_local_exists(self):
        """Test AsyncSessionLocal is created."""
        from app.db.database import AsyncSessionLocal

        assert AsyncSessionLocal is not None

    def test_async_session_factory_alias(self):
        """Test async_session_factory is alias for AsyncSessionLocal."""
        from app.db.database import AsyncSessionLocal, async_session_factory

        assert async_session_factory is AsyncSessionLocal


class TestGetDb:
    """Tests for get_db dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields a session."""
        from app.db.database import get_db

        mock_session = AsyncMock()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_class:
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None

            gen = get_db()
            session = await gen.__anext__()

            # Verify we get the mocked session
            assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_db_commits_on_success(self):
        """Test get_db commits session on success."""
        from app.db.database import get_db

        mock_session = AsyncMock()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_class:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context

            async for session in get_db():
                pass

            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_exception(self):
        """Test get_db rolls back on exception."""
        from app.db.database import get_db

        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("DB Error")

        with patch("app.db.database.AsyncSessionLocal") as mock_session_class:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context

            with pytest.raises(Exception):
                async for session in get_db():
                    pass

            mock_session.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_get_db_closes_session(self):
        """Test get_db closes session."""
        from app.db.database import get_db

        mock_session = AsyncMock()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_class:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context

            async for session in get_db():
                pass

            mock_session.close.assert_called()
