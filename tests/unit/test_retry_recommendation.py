"""Tests for retry recommendation feature.

リトライ推奨表示機能のテスト。
エラーカテゴリに基づいて適切なリトライ方法を推奨することを検証。
"""

from datetime import datetime
from unittest.mock import MagicMock

from apps.api.constants import RESUME_STEP_ORDER
from apps.api.services.runs import (
    CONFIG_DISABLED_STEPS,
    STEP_INPUT_MAP,
    get_retry_recommendation,
    get_valid_target_step,
    is_step_enabled,
)


class TestIsStepEnabled:
    """is_step_enabled関数のテスト。"""

    def test_step_without_config_flag_is_always_enabled(self) -> None:
        """config無効化対象でないステップは常に有効。"""
        assert is_step_enabled("step1", {}) is True
        assert is_step_enabled("step2", {"options": {}}) is True
        assert is_step_enabled("step4", {"options": {"enable_step1_5": False}}) is True

    def test_step1_5_enabled_by_default(self) -> None:
        """step1_5はデフォルトで有効。"""
        assert is_step_enabled("step1_5", {}) is True
        assert is_step_enabled("step1_5", {"options": {}}) is True

    def test_step1_5_disabled_when_flag_is_false(self) -> None:
        """step1_5はenable_step1_5=Falseで無効。"""
        config = {"options": {"enable_step1_5": False}}
        assert is_step_enabled("step1_5", config) is False

    def test_step3_5_enabled_by_default(self) -> None:
        """step3_5はデフォルトで有効。"""
        assert is_step_enabled("step3_5", {}) is True

    def test_step3_5_disabled_when_flag_is_false(self) -> None:
        """step3_5はenable_step3_5=Falseで無効。"""
        config = {"options": {"enable_step3_5": False}}
        assert is_step_enabled("step3_5", config) is False

    def test_step11_disabled_when_images_disabled(self) -> None:
        """step11はenable_images=Falseで無効。"""
        config = {"options": {"enable_images": False}}
        assert is_step_enabled("step11", config) is False

    def test_step12_disabled_when_flag_is_false(self) -> None:
        """step12はenable_step12=Falseで無効。"""
        config = {"options": {"enable_step12": False}}
        assert is_step_enabled("step12", config) is False


class TestGetValidTargetStep:
    """get_valid_target_step関数のテスト。"""

    def test_step4_returns_step3_5_by_default(self) -> None:
        """step4の入力元はデフォルトでstep3_5。"""
        target = get_valid_target_step("step4", {})
        assert target == "step3_5"

    def test_step4_returns_step3a_when_step3_5_disabled(self) -> None:
        """step3_5無効時はstep3aを返す。"""
        config = {"options": {"enable_step3_5": False}}
        target = get_valid_target_step("step4", config)
        assert target == "step3a"

    def test_step2_returns_step1_5_by_default(self) -> None:
        """step2の入力元はデフォルトでstep1_5。"""
        target = get_valid_target_step("step2", {})
        assert target == "step1_5"

    def test_step2_returns_step1_when_step1_5_disabled(self) -> None:
        """step1_5無効時はstep1を返す。"""
        config = {"options": {"enable_step1_5": False}}
        target = get_valid_target_step("step2", config)
        assert target == "step1"

    def test_step_without_candidates_returns_none(self) -> None:
        """候補がないステップはNoneを返す。"""
        target = get_valid_target_step("step0", {})
        assert target is None

    def test_target_step_is_in_resume_step_order(self) -> None:
        """返されるターゲットステップはRESUME_STEP_ORDERに含まれる。"""
        for step, candidates in STEP_INPUT_MAP.items():
            target = get_valid_target_step(step, {})
            if target is not None:
                assert target in RESUME_STEP_ORDER, f"{target} not in RESUME_STEP_ORDER for {step}"


class TestGetRetryRecommendation:
    """get_retry_recommendation関数のテスト。"""

    def _create_mock_run(
        self,
        status: str = "failed",
        config: dict | None = None,
        steps: list | None = None,
    ) -> MagicMock:
        """テスト用のモックRunを作成。"""
        run = MagicMock()
        run.status = status
        run.config = config or {}
        run.steps = steps or []
        return run

    def _create_mock_step(
        self,
        step_name: str,
        status: str = "completed",
        error_code: str | None = None,
        completed_at: datetime | None = None,
    ) -> MagicMock:
        """テスト用のモックStepを作成。"""
        step = MagicMock()
        step.step_name = step_name
        step.status = status
        step.error_code = error_code
        step.completed_at = completed_at or datetime.now()
        return step

    def test_returns_none_for_non_failed_run(self) -> None:
        """failed状態でないRunはNoneを返す。"""
        run = self._create_mock_run(status="running")
        result = get_retry_recommendation(run)
        assert result is None

    def test_returns_none_for_empty_steps(self) -> None:
        """ステップがない場合はNoneを返す。"""
        run = self._create_mock_run(steps=[])
        result = get_retry_recommendation(run)
        assert result is None

    def test_returns_none_when_no_failed_step(self) -> None:
        """失敗ステップがない場合はNoneを返す。"""
        run = self._create_mock_run(
            steps=[
                self._create_mock_step("step1", status="completed"),
                self._create_mock_step("step2", status="completed"),
            ]
        )
        result = get_retry_recommendation(run)
        assert result is None

    def test_validation_fail_recommends_previous_step(self) -> None:
        """validation_fail時は入力元ステップを推奨。"""
        run = self._create_mock_run(
            steps=[
                self._create_mock_step("step3_5", status="completed"),
                self._create_mock_step(
                    "step4",
                    status="failed",
                    error_code="validation_fail",
                    completed_at=datetime(2024, 1, 2),
                ),
            ]
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_previous"
        assert result.target_step == "step3_5"
        assert "入力データ品質問題" in result.reason

    def test_retryable_recommends_same_step(self) -> None:
        """retryable時は同一ステップを推奨。"""
        run = self._create_mock_run(
            steps=[
                self._create_mock_step(
                    "step4",
                    status="failed",
                    error_code="retryable",
                    completed_at=datetime(2024, 1, 1),
                ),
            ]
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_same"
        assert result.target_step == "step4"
        assert "一時的障害" in result.reason

    def test_non_retryable_recommends_same_step(self) -> None:
        """non_retryable時は同一ステップを推奨。"""
        run = self._create_mock_run(
            steps=[
                self._create_mock_step(
                    "step4",
                    status="failed",
                    error_code="non_retryable",
                    completed_at=datetime(2024, 1, 1),
                ),
            ]
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_same"
        assert result.target_step == "step4"
        assert "設定変更後" in result.reason

    def test_step3_5_disabled_falls_back_to_step3a(self) -> None:
        """step3_5無効時はstep3aを推奨。"""
        run = self._create_mock_run(
            config={"options": {"enable_step3_5": False}},
            steps=[
                self._create_mock_step(
                    "step4",
                    status="failed",
                    error_code="validation_fail",
                    completed_at=datetime(2024, 1, 1),
                ),
            ],
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_previous"
        assert result.target_step == "step3a"

    def test_step1_5_disabled_falls_back_to_step1(self) -> None:
        """step1_5無効時はstep1を推奨。"""
        run = self._create_mock_run(
            config={"options": {"enable_step1_5": False}},
            steps=[
                self._create_mock_step(
                    "step2",
                    status="failed",
                    error_code="validation_fail",
                    completed_at=datetime(2024, 1, 1),
                ),
            ],
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_previous"
        assert result.target_step == "step1"

    def test_step12_validation_fail_with_images_disabled(self) -> None:
        """step12でvalidation_fail、enable_images=False時はstep10を推奨。"""
        run = self._create_mock_run(
            config={"options": {"enable_images": False}},
            steps=[
                self._create_mock_step(
                    "step12",
                    status="failed",
                    error_code="validation_fail",
                    completed_at=datetime(2024, 1, 1),
                ),
            ],
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_previous"
        assert result.target_step == "step10"

    def test_latest_failed_step_is_used(self) -> None:
        """複数の失敗ステップがある場合、最新のものを使用。"""
        run = self._create_mock_run(
            steps=[
                self._create_mock_step(
                    "step2",
                    status="failed",
                    error_code="retryable",
                    completed_at=datetime(2024, 1, 1),
                ),
                self._create_mock_step(
                    "step4",
                    status="failed",
                    error_code="validation_fail",
                    completed_at=datetime(2024, 1, 2),  # より新しい
                ),
            ],
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.target_step == "step3_5"  # step4の入力元
        assert result.action == "retry_previous"

    def test_unknown_error_code_recommends_same_step(self) -> None:
        """不明なエラーコードの場合は同一ステップを推奨。"""
        run = self._create_mock_run(
            steps=[
                self._create_mock_step(
                    "step4",
                    status="failed",
                    error_code="unknown_error",
                    completed_at=datetime(2024, 1, 1),
                ),
            ]
        )
        result = get_retry_recommendation(run)
        assert result is not None
        assert result.action == "retry_same"
        assert result.target_step == "step4"


class TestStepInputMap:
    """STEP_INPUT_MAPの整合性テスト。"""

    def test_all_candidates_in_resume_step_order(self) -> None:
        """全ての候補ステップがRESUME_STEP_ORDERに含まれる。"""
        for step, candidates in STEP_INPUT_MAP.items():
            for candidate in candidates:
                assert candidate in RESUME_STEP_ORDER, f"Candidate {candidate} for {step} not in RESUME_STEP_ORDER"

    def test_config_disabled_steps_have_correct_keys(self) -> None:
        """CONFIG_DISABLED_STEPSのキーが正しい。"""
        expected_keys = {"step1_5", "step3_5", "step11", "step12"}
        assert set(CONFIG_DISABLED_STEPS.keys()) == expected_keys

    def test_config_disabled_steps_have_correct_values(self) -> None:
        """CONFIG_DISABLED_STEPSの値が正しい。"""
        assert CONFIG_DISABLED_STEPS["step1_5"] == "enable_step1_5"
        assert CONFIG_DISABLED_STEPS["step3_5"] == "enable_step3_5"
        assert CONFIG_DISABLED_STEPS["step11"] == "enable_images"
        assert CONFIG_DISABLED_STEPS["step12"] == "enable_step12"
