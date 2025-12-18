"""Tests for Step9 output validator."""

import pytest

from apps.api.validation import Step9OutputValidator, ValidationSeverity


def _generate_valid_content() -> str:
    """Generate valid content that passes all validations."""
    return """## Introduction

This is the introduction section with relevant content about the topic.
It provides an overview and sets the stage for the rest of the article.

## Main Topic One

Here we discuss the first main topic in detail. This section covers
important aspects that readers need to understand.

### Subtopic A

More detailed information about subtopic A.

### Subtopic B

More detailed information about subtopic B.

## Main Topic Two

The second main topic builds on the first and provides additional context.
This section is crucial for understanding the full picture.

### Another Subtopic

Additional details here.

## Main Topic Three

The third main topic rounds out our discussion with final key points.

## Conclusion

In conclusion, we've covered all the essential aspects of this topic.
Readers should now have a comprehensive understanding.

""" + "Additional content to meet minimum length requirements. " * 50


class TestStep9ValidatorBasicValidation:
    """Tests for basic step9 output validation."""

    def test_valid_step9_output_passes(self) -> None:
        """Valid step9 output should pass validation."""
        step9_data = {
            "final_content": _generate_valid_content(),
            "meta_description": "This is a valid meta description for SEO purposes with enough characters.",
            "internal_link_suggestions": ["Link to page A", "Link to page B"],
            "stats": {
                "word_count": 600,
                "char_count": 4000,
            },
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert report.format == "step9_output"
        assert report.error_count() == 0

    def test_empty_content_fails(self) -> None:
        """Empty final_content should fail validation."""
        step9_data = {
            "final_content": "",
            "meta_description": "Valid description",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is False
        assert any(
            issue.code == "STEP9_CONTENT_MISSING" for issue in report.issues
        )

    def test_missing_content_fails(self) -> None:
        """Missing final_content should fail validation."""
        step9_data = {
            "meta_description": "Valid description",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is False
        assert any(
            issue.code == "STEP9_CONTENT_MISSING" for issue in report.issues
        )

    def test_content_too_short_fails(self) -> None:
        """Content shorter than minimum should fail validation."""
        step9_data = {
            "final_content": "## Heading\n\nShort content.",
            "meta_description": "Valid description",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator(min_content_length=1000)
        report = validator.validate(step9_data)

        assert report.valid is False
        assert any(
            issue.code == "STEP9_CONTENT_TOO_SHORT" for issue in report.issues
        )

    def test_insufficient_h2_headings_fails(self) -> None:
        """Content with fewer than minimum H2 headings should fail."""
        # Only 2 H2 headings (default minimum is 3)
        content = """## First Heading

Some content here.

## Second Heading

More content here.

### Subheading

Additional content.
""" + "x" * 3000  # Pad to meet length requirement

        step9_data = {
            "final_content": content,
            "meta_description": "Valid description with enough characters for SEO.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator(min_content_length=100)
        report = validator.validate(step9_data)

        assert report.valid is False
        assert any(
            issue.code == "STEP9_INSUFFICIENT_H2" for issue in report.issues
        )

    def test_placeholder_detected_fails(self) -> None:
        """Content with placeholder text should fail validation."""
        content = _generate_valid_content()
        content += "\n\n[TODO: Add more content here]"

        step9_data = {
            "final_content": content,
            "meta_description": "Valid description with enough characters for SEO.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is False
        assert any(
            issue.code == "STEP9_PLACEHOLDER_FOUND" for issue in report.issues
        )


class TestStep9ValidatorDeterministicRepairs:
    """Tests for deterministic repair functionality."""

    def test_trailing_whitespace_repaired(self) -> None:
        """Trailing whitespace should be removed."""
        content = _generate_valid_content()
        content_with_trailing = content.replace("\n", "   \n")

        step9_data = {
            "final_content": content_with_trailing,
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert any(
            repair.code == "TRIM_TRAILING_WHITESPACE" for repair in report.repairs
        )
        # Content should be modified
        assert "   \n" not in step9_data["final_content"]

    def test_line_endings_normalized(self) -> None:
        """CRLF line endings should be normalized to LF."""
        content = _generate_valid_content()
        content_with_crlf = content.replace("\n", "\r\n")

        step9_data = {
            "final_content": content_with_crlf,
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert any(
            repair.code == "NORMALIZE_LINE_ENDINGS" for repair in report.repairs
        )
        assert "\r\n" not in step9_data["final_content"]
        assert "\r" not in step9_data["final_content"]

    def test_bom_removed(self) -> None:
        """UTF-8 BOM should be removed."""
        content = "\ufeff" + _generate_valid_content()

        step9_data = {
            "final_content": content,
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert any(repair.code == "REMOVE_BOM" for repair in report.repairs)
        assert not step9_data["final_content"].startswith("\ufeff")

    def test_excessive_heading_levels_normalized(self) -> None:
        """Heading levels deeper than ### should be normalized."""
        content = """## First Section

Some content.

## Second Section

More content.

## Third Section

Even more content.

#### This should become H3

Subsection content.

##### This too

More subsection content.

### Already H3

This is fine.
""" + "x" * 3000

        step9_data = {
            "final_content": content,
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert any(
            repair.code == "NORMALIZE_HEADING_LEVELS" for repair in report.repairs
        )
        # #### and ##### should now be ###
        assert "####" not in step9_data["final_content"]
        assert "#####" not in step9_data["final_content"]

    def test_auto_repair_disabled(self) -> None:
        """When auto_repair=False, no repairs should be applied."""
        content = "\ufeff" + _generate_valid_content()

        step9_data = {
            "final_content": content,
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data, auto_repair=False)

        assert report.valid is True
        assert len(report.repairs) == 0
        # BOM should still be present
        assert step9_data["final_content"].startswith("\ufeff")


class TestStep9ValidatorMetaDescription:
    """Tests for meta description validation."""

    def test_missing_meta_description_warning(self) -> None:
        """Missing meta description should generate a warning."""
        step9_data = {
            "final_content": _generate_valid_content(),
            "meta_description": "",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        # Should pass (warning only, not error)
        assert report.valid is True
        assert any(
            issue.code == "STEP9_META_MISSING"
            and issue.severity == ValidationSeverity.WARNING
            for issue in report.issues
        )

    def test_short_meta_description_warning(self) -> None:
        """Short meta description should generate a warning."""
        step9_data = {
            "final_content": _generate_valid_content(),
            "meta_description": "Too short",
            "internal_link_suggestions": [],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert any(
            issue.code == "STEP9_META_TOO_SHORT"
            and issue.severity == ValidationSeverity.WARNING
            for issue in report.issues
        )


class TestStep9ValidatorInternalLinks:
    """Tests for internal link suggestions validation."""

    def test_invalid_links_type_fails(self) -> None:
        """Non-list internal_link_suggestions should fail."""
        step9_data = {
            "final_content": _generate_valid_content(),
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": "not a list",
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is False
        assert any(
            issue.code == "STEP9_LINKS_INVALID_TYPE" for issue in report.issues
        )

    def test_non_string_link_warning(self) -> None:
        """Non-string link suggestions should generate a warning."""
        step9_data = {
            "final_content": _generate_valid_content(),
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": ["valid link", 123, {"invalid": "type"}],
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        # Should pass (warning only for non-string items)
        assert report.valid is True
        assert sum(
            1
            for issue in report.issues
            if issue.code == "STEP9_LINK_INVALID_FORMAT"
        ) == 2


class TestStep9ValidatorStatsConsistency:
    """Tests for stats consistency validation."""

    def test_stats_mismatch_warning(self) -> None:
        """Mismatched stats should generate a warning."""
        content = _generate_valid_content()
        step9_data = {
            "final_content": content,
            "meta_description": "Valid description with enough characters.",
            "internal_link_suggestions": [],
            "stats": {
                "word_count": 10,  # Very wrong
                "char_count": 50,  # Very wrong
            },
        }

        validator = Step9OutputValidator()
        report = validator.validate(step9_data)

        assert report.valid is True
        assert any(
            issue.code == "STEP9_STATS_MISMATCH"
            and issue.severity == ValidationSeverity.WARNING
            for issue in report.issues
        )
