"""Tests for Step 3.5: Human Touch Generation."""

from apps.worker.activities.schemas.step3_5 import (
    EmotionalAnalysis,
    ExperienceEpisode,
    HumanTouchMetadata,
    HumanTouchPattern,
    Step3_5Output,
)


class TestEmotionalAnalysis:
    """EmotionalAnalysis schema tests."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        analysis = EmotionalAnalysis()

        assert analysis.primary_emotion == ""
        assert analysis.secondary_emotions == []
        assert analysis.pain_points == []
        assert analysis.desires == []

    def test_with_all_fields(self) -> None:
        """All fields can be set."""
        analysis = EmotionalAnalysis(
            primary_emotion="anxiety",
            secondary_emotions=["hope", "curiosity"],
            pain_points=["time constraints", "lack of knowledge"],
            desires=["success", "recognition"],
        )

        assert analysis.primary_emotion == "anxiety"
        assert len(analysis.secondary_emotions) == 2
        assert "hope" in analysis.secondary_emotions
        assert len(analysis.pain_points) == 2
        assert len(analysis.desires) == 2


class TestHumanTouchPattern:
    """HumanTouchPattern schema tests."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        pattern = HumanTouchPattern()

        assert pattern.type == "experience"
        assert pattern.content == ""
        assert pattern.placement_suggestion == ""

    def test_experience_type(self) -> None:
        """Experience type pattern."""
        pattern = HumanTouchPattern(
            type="experience",
            content="I remember when I first started...",
            placement_suggestion="introduction",
        )

        assert pattern.type == "experience"
        assert "remember" in pattern.content
        assert pattern.placement_suggestion == "introduction"

    def test_emotion_type(self) -> None:
        """Emotion type pattern."""
        pattern = HumanTouchPattern(
            type="emotion",
            content="You might feel overwhelmed at first",
            placement_suggestion="problem section",
        )

        assert pattern.type == "emotion"

    def test_empathy_type(self) -> None:
        """Empathy type pattern."""
        pattern = HumanTouchPattern(
            type="empathy",
            content="We understand your frustration",
            placement_suggestion="before solution",
        )

        assert pattern.type == "empathy"


class TestExperienceEpisode:
    """ExperienceEpisode schema tests."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        episode = ExperienceEpisode()

        assert episode.scenario == ""
        assert episode.narrative == ""
        assert episode.lesson == ""

    def test_with_all_fields(self) -> None:
        """All fields can be set."""
        episode = ExperienceEpisode(
            scenario="Starting a new project without proper planning",
            narrative="I once jumped into a project without understanding the requirements...",
            lesson="Always take time to understand the full scope before starting",
        )

        assert "project" in episode.scenario
        assert "jumped" in episode.narrative
        assert "understand" in episode.lesson


class TestHumanTouchMetadata:
    """HumanTouchMetadata schema tests."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        metadata = HumanTouchMetadata()

        assert metadata.model == ""
        assert metadata.input_files == []
        # generated_at has a default_factory

    def test_with_all_fields(self) -> None:
        """All fields can be set."""
        metadata = HumanTouchMetadata(
            model="gemini-2.5-flash",
            input_files=["step0", "step1", "step3a", "step3b", "step3c"],
        )

        assert metadata.model == "gemini-2.5-flash"
        assert len(metadata.input_files) == 5
        assert "step0" in metadata.input_files


class TestStep3_5Output:
    """Step3_5Output schema tests."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        output = Step3_5Output(
            step="step3_5",
            keyword="test keyword",
        )

        assert output.step == "step3_5"
        assert output.keyword == "test keyword"
        assert output.emotional_analysis.primary_emotion == ""
        assert output.human_touch_patterns == []
        assert output.experience_episodes == []
        assert output.emotional_hooks == []
        assert output.raw_output == ""
        assert output.parsed_data is None

    def test_with_full_output(self) -> None:
        """Full output with all fields."""
        output = Step3_5Output(
            step="step3_5",
            keyword="SEO tips",
            emotional_analysis=EmotionalAnalysis(
                primary_emotion="curiosity",
                pain_points=["lack of traffic"],
            ),
            human_touch_patterns=[
                HumanTouchPattern(
                    type="experience",
                    content="When I started blogging...",
                    placement_suggestion="intro",
                ),
            ],
            experience_episodes=[
                ExperienceEpisode(
                    scenario="First blog post",
                    narrative="I wrote my first post without any SEO knowledge...",
                    lesson="Learn SEO basics before writing",
                ),
            ],
            emotional_hooks=[
                "Ever wondered why your content isn't ranking?",
                "You're not alone in this struggle",
            ],
            raw_output='{"emotional_analysis": {...}}',
            parsed_data={"emotional_analysis": {"primary_emotion": "curiosity"}},
            metadata=HumanTouchMetadata(
                model="gemini-2.5-flash",
                input_files=["step0", "step3a"],
            ),
        )

        assert output.step == "step3_5"
        assert output.keyword == "SEO tips"
        assert output.emotional_analysis.primary_emotion == "curiosity"
        assert len(output.human_touch_patterns) == 1
        assert len(output.experience_episodes) == 1
        assert len(output.emotional_hooks) == 2
        assert output.metadata.model == "gemini-2.5-flash"

    def test_optional_step1_5_not_required(self) -> None:
        """Step1.5 is optional - output works without it."""
        # This tests the acceptance criteria: step1_5がない場合でもエラーにならない
        output = Step3_5Output(
            step="step3_5",
            keyword="test",
            metadata=HumanTouchMetadata(
                input_files=["step0", "step1", "step3a", "step3b", "step3c"],
                # Note: step1_5 is NOT in the list - this is valid
            ),
        )

        assert "step1_5" not in output.metadata.input_files
        assert len(output.metadata.input_files) == 5

    def test_required_fields_present(self) -> None:
        """Required output fields are present (acceptance criteria check)."""
        output = Step3_5Output(
            step="step3_5",
            keyword="test",
            emotional_analysis=EmotionalAnalysis(primary_emotion="hope"),
            human_touch_patterns=[HumanTouchPattern(type="experience")],
            experience_episodes=[ExperienceEpisode(scenario="test")],
            emotional_hooks=["hook1"],
        )

        # Verify all required fields exist
        assert hasattr(output, "emotional_analysis")
        assert hasattr(output, "human_touch_patterns")
        assert hasattr(output, "experience_episodes")
        assert hasattr(output, "emotional_hooks")
        assert hasattr(output, "metadata")

        # Verify they have content
        assert output.emotional_analysis.primary_emotion == "hope"
        assert len(output.human_touch_patterns) > 0
        assert len(output.experience_episodes) > 0
        assert len(output.emotional_hooks) > 0
