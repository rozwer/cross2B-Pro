"""Tests for database models."""

from apps.api.db.models import (
    Artifact,
    AuditLog,
    LLMModel,
    LLMProvider,
    Prompt,
    Run,
    Step,
    StepLLMDefault,
    Tenant,
)


class TestTenant:
    """Tests for Tenant model."""

    def test_tenant_fields(self) -> None:
        """Test Tenant model has correct fields."""
        tenant = Tenant(
            id="tenant-123",
            name="Test Company",
            database_url="postgresql://localhost/test",
            is_active=True,
        )
        assert tenant.id == "tenant-123"
        assert tenant.name == "Test Company"
        assert tenant.is_active is True


class TestLLMModels:
    """Tests for LLM-related models."""

    def test_llm_provider(self) -> None:
        """Test LLMProvider model."""
        provider = LLMProvider(
            id="claude",
            display_name="Claude",
            api_base_url="https://api.anthropic.com",
            is_active=True,
        )
        assert provider.id == "claude"
        assert provider.display_name == "Claude"

    def test_llm_model(self) -> None:
        """Test LLMModel model."""
        model = LLMModel(
            provider_id="claude",
            model_name="claude-3-opus",
            model_class="pro",
            is_active=True,
        )
        assert model.model_name == "claude-3-opus"
        assert model.model_class == "pro"

    def test_step_llm_default(self) -> None:
        """Test StepLLMDefault model."""
        default = StepLLMDefault(
            step="step_2_draft",
            provider_id="claude",
            model_class="pro",
        )
        assert default.step == "step_2_draft"
        assert default.provider_id == "claude"


class TestRun:
    """Tests for Run model."""

    def test_run_creation(self) -> None:
        """Test Run model creation."""
        run = Run(
            id="550e8400-e29b-41d4-a716-446655440000",
            tenant_id="tenant-123",
            status="pending",
            current_step="init",
            config={"model": "claude-3"},
        )
        assert run.status == "pending"
        assert run.config["model"] == "claude-3"
        assert run.tenant_id == "tenant-123"


class TestStep:
    """Tests for Step model."""

    def test_step_creation(self) -> None:
        """Test Step model creation."""
        step = Step(
            id="660e8400-e29b-41d4-a716-446655440001",
            run_id="550e8400-e29b-41d4-a716-446655440000",
            step_name="step_1",
            status="running",
        )
        assert step.step_name == "step_1"
        assert step.status == "running"


class TestArtifact:
    """Tests for Artifact model."""

    def test_artifact_creation(self) -> None:
        """Test Artifact model creation."""
        artifact = Artifact(
            id="770e8400-e29b-41d4-a716-446655440002",
            run_id="550e8400-e29b-41d4-a716-446655440000",
            artifact_type="json",
            ref_path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123def456",
        )
        assert artifact.artifact_type == "json"
        assert "output.json" in artifact.ref_path


class TestAuditLog:
    """Tests for AuditLog model."""

    def test_audit_log_creation(self) -> None:
        """Test AuditLog model creation."""
        log = AuditLog(
            user_id="user-123",
            action="step.started",
            resource_type="step",
            resource_id="step_1",
            details={"attempt": 1},
            prev_hash=None,
            entry_hash="abc123def456" * 4,  # SHA256 hex (64 chars)
        )
        assert log.action == "step.started"
        assert log.details["attempt"] == 1
        assert log.entry_hash is not None


class TestPrompt:
    """Tests for Prompt model."""

    def test_prompt_creation(self) -> None:
        """Test Prompt model creation."""
        prompt = Prompt(
            step="step_1",
            version=1,
            content="Analyze the keyword: {{keyword}}",
            variables={"keyword": {"required": True}},
            is_active=True,
        )
        assert prompt.step == "step_1"
        assert prompt.version == 1
        assert "{{keyword}}" in prompt.content
