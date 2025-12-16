"""Step 2: CSV Validation Activity.

Validates the competitor data from step 1 and prepares it for analysis.
Uses Validation module for data integrity checks.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.validation.csv_validator import CsvValidator
from apps.api.validation.schemas import ValidationSeverity

from .base import ActivityError, BaseActivity, ValidationError


class Step2CSVValidation(BaseActivity):
    """Activity for CSV validation of competitor data."""

    @property
    def step_id(self) -> str:
        return "step2"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute CSV validation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with validation results
        """
        config = ctx.config

        # Get step1 output from storage (via config or state)
        step1_data = config.get("step1_data")

        if not step1_data:
            raise ActivityError(
                "step1_data is required - run step1 first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        competitors = step1_data.get("competitors", [])

        if not competitors:
            raise ActivityError(
                "No competitor data to validate",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Validate competitor data structure
        validator = CsvValidator()
        validated_records = []
        validation_issues = []

        required_fields = ["url", "title", "content"]

        for idx, competitor in enumerate(competitors):
            record_issues = []

            # Check required fields
            for field in required_fields:
                if field not in competitor or not competitor[field]:
                    record_issues.append({
                        "field": field,
                        "issue": "missing_or_empty",
                        "severity": ValidationSeverity.ERROR.value,
                    })

            # Check content length
            content = competitor.get("content", "")
            if len(content) < 100:
                record_issues.append({
                    "field": "content",
                    "issue": "content_too_short",
                    "severity": ValidationSeverity.WARNING.value,
                    "value": len(content),
                })

            if record_issues:
                validation_issues.append({
                    "index": idx,
                    "url": competitor.get("url", "unknown"),
                    "issues": record_issues,
                })
            else:
                validated_records.append(competitor)

        # Determine overall validity
        error_count = sum(
            1 for issue in validation_issues
            for i in issue["issues"]
            if i["severity"] == ValidationSeverity.ERROR.value
        )

        is_valid = error_count == 0 and len(validated_records) > 0

        # Build result
        result = {
            "step": self.step_id,
            "is_valid": is_valid,
            "total_records": len(competitors),
            "valid_records": len(validated_records),
            "validation_issues": validation_issues,
            "validated_data": validated_records,
        }

        # If not valid, raise validation error
        if not is_valid:
            raise ActivityError(
                f"Validation failed: {error_count} errors, {len(validated_records)} valid records",
                category=ErrorCategory.VALIDATION_FAIL,
                details={"issues": validation_issues},
            )

        return result


@activity.defn(name="step2_csv_validation")
async def step2_csv_validation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 2."""
    step = Step2CSVValidation()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
