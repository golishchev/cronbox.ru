"""Tests for TemplateService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestTemplateServiceGetTemplate:
    """Tests for TemplateService.get_template."""

    @pytest.mark.asyncio
    async def test_get_template_found(self):
        """Test get_template returns template when found."""
        from app.models.notification_template import NotificationChannel
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_template = MagicMock()
        mock_template.code = "task_failure"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_template
        mock_db.execute.return_value = mock_result

        result = await service.get_template(mock_db, "task_failure", "en", NotificationChannel.EMAIL)

        assert result == mock_template

    @pytest.mark.asyncio
    async def test_get_template_fallback_to_english(self):
        """Test get_template falls back to English."""
        from app.models.notification_template import NotificationChannel
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_english_template = MagicMock()
        mock_english_template.code = "task_failure"
        mock_english_template.language = "en"

        # First call for Russian returns None, second for English returns template
        mock_result_ru = MagicMock()
        mock_result_ru.scalar_one_or_none.return_value = None

        mock_result_en = MagicMock()
        mock_result_en.scalar_one_or_none.return_value = mock_english_template

        mock_db.execute.side_effect = [mock_result_ru, mock_result_en]

        result = await service.get_template(mock_db, "task_failure", "ru", NotificationChannel.EMAIL)

        assert result == mock_english_template
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test get_template returns None when not found."""
        from app.models.notification_template import NotificationChannel
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_template(mock_db, "nonexistent", "en", NotificationChannel.EMAIL)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_template_channel_as_string(self):
        """Test get_template accepts channel as string."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_template = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_template
        mock_db.execute.return_value = mock_result

        result = await service.get_template(mock_db, "task_failure", "en", "email")

        assert result == mock_template


class TestTemplateServiceRender:
    """Tests for TemplateService.render."""

    def test_render_with_template(self):
        """Test render returns rendered content."""
        from app.services.template_service import TemplateService

        service = TemplateService()

        mock_template = MagicMock()
        mock_template.body = "Hello {name}, task {task_name} failed."
        mock_template.subject = "[CronBox] Task Failed: {task_name}"
        mock_template.code = "task_failure"

        variables = {"name": "John", "task_name": "My Task"}

        subject, body = service.render(mock_template, variables)

        assert subject == "[CronBox] Task Failed: My Task"
        assert body == "Hello John, task My Task failed."

    def test_render_without_template(self):
        """Test render with None template returns empty."""
        from app.services.template_service import TemplateService

        service = TemplateService()

        subject, body = service.render(None, {})

        assert subject is None
        assert body == ""

    def test_render_no_subject(self):
        """Test render with no subject (Telegram)."""
        from app.services.template_service import TemplateService

        service = TemplateService()

        mock_template = MagicMock()
        mock_template.body = "Task {task_name} failed."
        mock_template.subject = None
        mock_template.code = "task_failure"

        subject, body = service.render(mock_template, {"task_name": "Test"})

        assert subject is None
        assert body == "Task Test failed."

    def test_render_missing_variable_in_body(self):
        """Test render with missing variable in body."""
        from app.services.template_service import TemplateService

        service = TemplateService()

        mock_template = MagicMock()
        mock_template.body = "Task {task_name} in {workspace_name} failed."
        mock_template.subject = None
        mock_template.code = "task_failure"

        # Missing workspace_name
        subject, body = service.render(mock_template, {"task_name": "Test"})

        # Should return original template body when variable is missing
        assert body == mock_template.body

    def test_render_missing_variable_in_subject(self):
        """Test render with missing variable in subject."""
        from app.services.template_service import TemplateService

        service = TemplateService()

        mock_template = MagicMock()
        mock_template.body = "Body text"
        mock_template.subject = "[CronBox] Task Failed: {task_name}"
        mock_template.code = "task_failure"

        # Missing task_name
        subject, body = service.render(mock_template, {})

        # Should return original template subject when variable is missing
        assert subject == mock_template.subject


class TestTemplateServiceGetUserLanguage:
    """Tests for TemplateService.get_user_language."""

    @pytest.mark.asyncio
    async def test_get_user_language_from_workspace_owner(self):
        """Test get_user_language returns owner's language."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_workspace = MagicMock()
        mock_workspace.owner = MagicMock()
        mock_workspace.owner.preferred_language = "ru"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace
        mock_db.execute.return_value = mock_result

        result = await service.get_user_language(mock_db, workspace_id)

        assert result == "ru"

    @pytest.mark.asyncio
    async def test_get_user_language_no_workspace(self):
        """Test get_user_language returns 'en' when no workspace."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_user_language(mock_db, uuid4())

        assert result == "en"

    @pytest.mark.asyncio
    async def test_get_user_language_no_owner_preference(self):
        """Test get_user_language returns 'en' when no preference."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_workspace = MagicMock()
        mock_workspace.owner = MagicMock()
        mock_workspace.owner.preferred_language = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace
        mock_db.execute.return_value = mock_result

        result = await service.get_user_language(mock_db, uuid4())

        assert result == "en"


class TestTemplateServiceSeedDefaultTemplates:
    """Tests for TemplateService.seed_default_templates."""

    @pytest.mark.asyncio
    async def test_seed_creates_new_templates(self):
        """Test seed creates templates that don't exist."""
        from app.services.template_service import DEFAULT_TEMPLATES, TemplateService

        service = TemplateService()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        # Simulate all templates not existing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.seed_default_templates(mock_db)

        assert result == len(DEFAULT_TEMPLATES)
        assert mock_db.add.call_count == len(DEFAULT_TEMPLATES)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_skips_existing_templates(self):
        """Test seed skips templates that exist."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        # Simulate all templates existing
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_db.execute.return_value = mock_result

        result = await service.seed_default_templates(mock_db)

        assert result == 0
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()


class TestTemplateServiceGetAllTemplates:
    """Tests for TemplateService.get_all_templates."""

    @pytest.mark.asyncio
    async def test_get_all_templates(self):
        """Test get_all_templates returns all templates."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_templates = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_templates
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_all_templates(mock_db)

        assert len(result) == 2


class TestTemplateServiceGetTemplateById:
    """Tests for TemplateService.get_template_by_id."""

    @pytest.mark.asyncio
    async def test_get_template_by_id_found(self):
        """Test get_template_by_id returns template."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        template_id = uuid4()
        mock_template = MagicMock()
        mock_db.get.return_value = mock_template

        result = await service.get_template_by_id(mock_db, template_id)

        assert result == mock_template

    @pytest.mark.asyncio
    async def test_get_template_by_id_not_found(self):
        """Test get_template_by_id returns None when not found."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_db.get.return_value = None

        result = await service.get_template_by_id(mock_db, uuid4())

        assert result is None


class TestTemplateServiceUpdateTemplate:
    """Tests for TemplateService.update_template."""

    @pytest.mark.asyncio
    async def test_update_template_subject(self):
        """Test update_template updates subject."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_template = MagicMock()
        mock_template.subject = "Old Subject"

        result = await service.update_template(mock_db, mock_template, subject="New Subject")

        assert mock_template.subject == "New Subject"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_template)

    @pytest.mark.asyncio
    async def test_update_template_body(self):
        """Test update_template updates body."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_template = MagicMock()
        mock_template.body = "Old Body"

        result = await service.update_template(mock_db, mock_template, body="New Body")

        assert mock_template.body == "New Body"

    @pytest.mark.asyncio
    async def test_update_template_is_active(self):
        """Test update_template updates is_active."""
        from app.services.template_service import TemplateService

        service = TemplateService()
        mock_db = AsyncMock()

        mock_template = MagicMock()
        mock_template.is_active = True

        result = await service.update_template(mock_db, mock_template, is_active=False)

        assert mock_template.is_active is False


class TestTemplateServiceGetDefaultTemplate:
    """Tests for TemplateService.get_default_template."""

    def test_get_default_template_found(self):
        """Test get_default_template returns template data."""
        from app.models.notification_template import NotificationChannel
        from app.services.template_service import TemplateService

        service = TemplateService()

        result = service.get_default_template("task_failure", "en", NotificationChannel.EMAIL)

        assert result is not None
        assert result["code"] == "task_failure"
        assert result["language"] == "en"

    def test_get_default_template_not_found(self):
        """Test get_default_template returns None when not found."""
        from app.models.notification_template import NotificationChannel
        from app.services.template_service import TemplateService

        service = TemplateService()

        result = service.get_default_template("nonexistent", "xx", NotificationChannel.EMAIL)

        assert result is None

    def test_get_default_template_channel_as_string(self):
        """Test get_default_template accepts channel as string."""
        from app.services.template_service import TemplateService

        service = TemplateService()

        result = service.get_default_template("task_failure", "en", "email")

        assert result is not None
        assert result["code"] == "task_failure"


class TestDefaultTemplates:
    """Tests for DEFAULT_TEMPLATES constant."""

    def test_default_templates_not_empty(self):
        """Test DEFAULT_TEMPLATES is not empty."""
        from app.services.template_service import DEFAULT_TEMPLATES

        assert len(DEFAULT_TEMPLATES) > 0

    def test_default_templates_have_required_fields(self):
        """Test all default templates have required fields."""
        from app.services.template_service import DEFAULT_TEMPLATES

        required_fields = ["code", "language", "channel", "body"]

        for template in DEFAULT_TEMPLATES:
            for field in required_fields:
                assert field in template, f"Missing {field} in template"

    def test_default_templates_have_both_languages(self):
        """Test templates exist for both English and Russian."""
        from app.services.template_service import DEFAULT_TEMPLATES

        codes = set(t["code"] for t in DEFAULT_TEMPLATES)

        for code in codes:
            languages = [t["language"] for t in DEFAULT_TEMPLATES if t["code"] == code]
            assert "en" in languages, f"Missing English template for {code}"
            assert "ru" in languages, f"Missing Russian template for {code}"
