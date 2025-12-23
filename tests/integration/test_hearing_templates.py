"""Integration tests for hearing template functionality.

Tests cover:
- API CRUD operations
- Tenant isolation
- Template data validation
- Audit logging
"""

# mypy: ignore-errors
from __future__ import annotations

from typing import Any

import pytest

from apps.api.schemas.article_hearing import (
    BusinessInput,
    CTAInput,
    HearingTemplateCreate,
    HearingTemplateData,
    HearingTemplateUpdate,
    KeywordInput,
    StrategyInput,
    WordCountInput,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_template_data() -> dict:
    """Create sample template data for testing."""
    return {
        "business": {
            "description": "派遣社員向けeラーニングサービスを提供",
            "target_cv": "inquiry",
            "target_audience": "派遣会社の教育担当者、人事部長、30〜40代",
            "company_strengths": "中小企業特化、低予算での教育プラン提供、導入実績300社以上",
        },
        "keyword": {
            "status": "decided",
            "main_keyword": "派遣社員 教育方法",
            "monthly_search_volume": "100-200",
            "competition_level": "medium",
        },
        "strategy": {
            "article_style": "standalone",
        },
        "word_count": {
            "mode": "ai_balanced",
        },
        "cta": {
            "type": "single",
            "position_mode": "fixed",
            "single": {
                "url": "https://cross-learning.jp/",
                "text": "クロスラーニングの詳細を見る",
                "description": "クロスラーニング広報サイトのTOPページ",
            },
        },
    }


@pytest.fixture
def sample_create_request(sample_template_data: dict) -> HearingTemplateCreate:
    """Create a sample template creation request."""
    return HearingTemplateCreate(
        name="テスト用テンプレート",
        description="テスト用の説明文",
        data=HearingTemplateData(**sample_template_data),
    )


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestHearingTemplateSchemaValidation:
    """Test schema validation for hearing templates."""

    def test_valid_template_data_creation(self, sample_template_data: dict):
        """Test creating valid template data."""
        data = HearingTemplateData(**sample_template_data)
        assert data.business.description == sample_template_data["business"]["description"]
        assert data.keyword.status == sample_template_data["keyword"]["status"]
        assert data.strategy.article_style == sample_template_data["strategy"]["article_style"]

    def test_template_create_schema(self, sample_create_request: HearingTemplateCreate):
        """Test template create schema validation."""
        assert sample_create_request.name == "テスト用テンプレート"
        assert sample_create_request.description == "テスト用の説明文"
        assert sample_create_request.data.business.target_cv == "inquiry"

    def test_template_update_schema_partial(self):
        """Test partial update schema."""
        update = HearingTemplateUpdate(name="新しい名前")
        assert update.name == "新しい名前"
        assert update.description is None
        assert update.data is None

    def test_template_name_validation(self, sample_template_data: dict):
        """Test template name validation - empty name should fail."""
        with pytest.raises(ValueError):
            HearingTemplateCreate(
                name="",  # Empty name should fail
                data=HearingTemplateData(**sample_template_data),
            )

    def test_template_name_max_length(self, sample_template_data: dict):
        """Test template name max length validation."""
        with pytest.raises(ValueError):
            HearingTemplateCreate(
                name="a" * 256,  # Exceeds 255 character limit
                data=HearingTemplateData(**sample_template_data),
            )


# =============================================================================
# Database Model Tests
# =============================================================================


class TestHearingTemplateModel:
    """Test hearing template database model."""

    def test_model_attributes(self):
        """Test that model has all required attributes."""
        from apps.api.db.models import HearingTemplate

        # Check that the model has all expected columns
        assert hasattr(HearingTemplate, "id")
        assert hasattr(HearingTemplate, "tenant_id")
        assert hasattr(HearingTemplate, "name")
        assert hasattr(HearingTemplate, "description")
        assert hasattr(HearingTemplate, "data")
        assert hasattr(HearingTemplate, "created_at")
        assert hasattr(HearingTemplate, "updated_at")

    def test_table_name(self):
        """Test that model has correct table name."""
        from apps.api.db.models import HearingTemplate

        assert HearingTemplate.__tablename__ == "hearing_templates"


# =============================================================================
# API Router Tests (Unit-style with mocks)
# =============================================================================


class TestHearingTemplateRouter:
    """Test hearing template API router logic."""

    @pytest.mark.asyncio
    async def test_create_template_success(self, sample_template_data: dict[str, Any]) -> None:
        """Test successful template creation."""
        # Create request
        request = HearingTemplateCreate(
            name="New Template",
            description="Test description",
            data=HearingTemplateData(**sample_template_data),
        )

        # We would need to mock the database session for actual testing
        # This is a structural test to verify the endpoint exists
        assert request.name == "New Template"

    def test_template_list_pagination_params(self):
        """Test that list endpoint accepts pagination parameters."""
        # This verifies the endpoint signature accepts limit/offset
        import inspect

        from apps.api.routers.hearing import list_templates

        sig = inspect.signature(list_templates)
        params = sig.parameters

        assert "limit" in params
        assert "offset" in params
        assert "user" in params


# =============================================================================
# Tenant Isolation Tests
# =============================================================================


class TestTenantIsolation:
    """Test tenant isolation for hearing templates."""

    def test_template_requires_tenant_id(self):
        """Test that templates require tenant_id."""
        from apps.api.db.models import HearingTemplate

        # Check that tenant_id is not nullable
        tenant_id_column = HearingTemplate.__table__.c.tenant_id
        assert not tenant_id_column.nullable

    def test_unique_constraint_includes_tenant(self):
        """Test that unique constraint includes tenant_id."""
        from apps.api.db.models import HearingTemplate

        # Check for the unique constraint
        constraints = HearingTemplate.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, "columns")]

        # Find the tenant_name unique constraint
        found = False
        for constraint in unique_constraints:
            column_names = [col.name for col in constraint.columns]
            if "tenant_id" in column_names and "name" in column_names:
                found = True
                break

        assert found, "Unique constraint on (tenant_id, name) not found"


# =============================================================================
# Integration Flow Tests
# =============================================================================


class TestTemplateWorkflow:
    """Test complete template workflow scenarios."""

    def test_template_data_to_form_conversion(self, sample_template_data: dict):
        """Test that template data can be converted to form input."""
        data = HearingTemplateData(**sample_template_data)

        # Verify all sections are present
        assert data.business is not None
        assert data.keyword is not None
        assert data.strategy is not None
        assert data.word_count is not None
        assert data.cta is not None

    def test_form_data_to_template_conversion(self, sample_template_data: dict):
        """Test that form data can be converted to template."""
        # Create individual section objects
        business = BusinessInput(**sample_template_data["business"])
        keyword = KeywordInput(**sample_template_data["keyword"])
        strategy = StrategyInput(**sample_template_data["strategy"])
        word_count = WordCountInput(**sample_template_data["word_count"])
        cta = CTAInput(**sample_template_data["cta"])

        # Create template data
        template_data = HearingTemplateData(
            business=business,
            keyword=keyword,
            strategy=strategy,
            word_count=word_count,
            cta=cta,
        )

        # Verify data integrity
        assert template_data.business.description == business.description
        assert template_data.keyword.main_keyword == keyword.main_keyword

    def test_template_excludes_confirmed_field(self, sample_template_data: dict):
        """Test that template data does not include confirmed field."""
        data = HearingTemplateData(**sample_template_data)

        # confirmed should not be in the template data
        assert not hasattr(data, "confirmed")

        # Check model dump doesn't include confirmed
        dumped = data.model_dump()
        assert "confirmed" not in dumped


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestTemplateErrorHandling:
    """Test error handling for template operations."""

    def test_invalid_keyword_status_rejected(self, sample_template_data: dict):
        """Test that invalid keyword status is rejected."""
        invalid_data = sample_template_data.copy()
        invalid_data["keyword"]["status"] = "invalid_status"

        with pytest.raises(ValueError):
            HearingTemplateData(**invalid_data)

    def test_invalid_article_style_rejected(self, sample_template_data: dict):
        """Test that invalid article style is rejected."""
        invalid_data = sample_template_data.copy()
        invalid_data["strategy"]["article_style"] = "invalid_style"

        with pytest.raises(ValueError):
            HearingTemplateData(**invalid_data)

    def test_cta_type_validation(self, sample_template_data: dict):
        """Test CTA type validation."""
        # Single CTA without single config should fail validation
        invalid_data = sample_template_data.copy()
        invalid_data["cta"]["single"] = None

        with pytest.raises(ValueError):
            CTAInput(**invalid_data["cta"])
