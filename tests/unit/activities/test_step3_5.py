"""Tests for Step 3.5: Human Touch Generation."""

import pytest

from apps.worker.activities.schemas.step3_5 import (
    BehavioralEconomicsHooks,
    EmotionalAnalysis,
    ExperienceEpisode,
    HumanTouchMetadata,
    HumanTouchPattern,
    PhaseEmotionalData,
    PhaseEmotionalMap,
    PlacementInstruction,
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


# ============================================================
# blog.System Ver8.3 Extension Tests
# ============================================================


class TestPhaseEmotionalData:
    """PhaseEmotionalData schema tests for blog.System integration."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        data = PhaseEmotionalData()

        assert data.dominant_emotion == ""
        assert data.empathy_statements == []
        assert data.experience_episodes == []

    def test_with_all_fields(self) -> None:
        """All fields can be set with proper data."""
        data = PhaseEmotionalData(
            dominant_emotion="不安",
            empathy_statements=[
                "初めてのことは誰でも不安になります",
                "「本当に大丈夫かな」と思うのは自然なことです",
                "あなたの気持ちはよく分かります",
            ],
            experience_episodes=[
                ExperienceEpisode(
                    scenario="初めての挑戦",
                    narrative="私も最初は何も分からない状態でした...",
                    lesson="一歩踏み出す勇気が大切",
                ),
                ExperienceEpisode(
                    scenario="失敗からの学び",
                    narrative="最初の試みは完全に失敗しました...",
                    lesson="失敗は成功の母",
                ),
            ],
        )

        assert data.dominant_emotion == "不安"
        assert len(data.empathy_statements) == 3
        assert len(data.experience_episodes) == 2
        assert data.experience_episodes[0].scenario == "初めての挑戦"

    def test_target_empathy_statements_count(self) -> None:
        """Target is 3 empathy statements per phase."""
        data = PhaseEmotionalData(
            dominant_emotion="焦り",
            empathy_statements=["共感1", "共感2", "共感3"],
        )
        assert len(data.empathy_statements) == 3

    def test_target_episodes_count(self) -> None:
        """Target is 2-3 episodes per phase."""
        data = PhaseEmotionalData(
            dominant_emotion="危機感",
            experience_episodes=[
                ExperienceEpisode(scenario="s1"),
                ExperienceEpisode(scenario="s2"),
            ],
        )
        assert 2 <= len(data.experience_episodes) <= 3


class TestPhaseEmotionalMap:
    """PhaseEmotionalMap schema tests for three-phase mapping."""

    def test_default_values(self) -> None:
        """Default values create empty phases."""
        pem = PhaseEmotionalMap()

        assert pem.phase1.dominant_emotion == ""
        assert pem.phase2.dominant_emotion == ""
        assert pem.phase3.dominant_emotion == ""

    def test_three_phase_structure(self) -> None:
        """Three phases with distinct emotional characteristics."""
        pem = PhaseEmotionalMap(
            phase1=PhaseEmotionalData(
                dominant_emotion="不安/焦り/危機感",
                empathy_statements=["phase1の共感文"],
            ),
            phase2=PhaseEmotionalData(
                dominant_emotion="冷静/分析的",
                empathy_statements=["phase2の共感文"],
            ),
            phase3=PhaseEmotionalData(
                dominant_emotion="期待/決意",
                empathy_statements=["phase3の共感文"],
            ),
        )

        # Phase 1: 認知 (Awareness)
        assert "不安" in pem.phase1.dominant_emotion
        # Phase 2: 検討 (Consideration)
        assert "冷静" in pem.phase2.dominant_emotion
        # Phase 3: 行動 (Action)
        assert "期待" in pem.phase3.dominant_emotion

    def test_full_phase_emotional_map(self) -> None:
        """Full map with episodes per phase."""
        episode1 = ExperienceEpisode(scenario="認知フェーズの体験")
        episode2 = ExperienceEpisode(scenario="検討フェーズの体験")
        episode3 = ExperienceEpisode(scenario="行動フェーズの体験")

        pem = PhaseEmotionalMap(
            phase1=PhaseEmotionalData(
                dominant_emotion="不安",
                empathy_statements=["共感1-1", "共感1-2", "共感1-3"],
                experience_episodes=[episode1],
            ),
            phase2=PhaseEmotionalData(
                dominant_emotion="分析的",
                empathy_statements=["共感2-1", "共感2-2", "共感2-3"],
                experience_episodes=[episode2],
            ),
            phase3=PhaseEmotionalData(
                dominant_emotion="決意",
                empathy_statements=["共感3-1", "共感3-2", "共感3-3"],
                experience_episodes=[episode3],
            ),
        )

        # Each phase has episodes
        assert len(pem.phase1.experience_episodes) >= 1
        assert len(pem.phase2.experience_episodes) >= 1
        assert len(pem.phase3.experience_episodes) >= 1


class TestBehavioralEconomicsHooks:
    """BehavioralEconomicsHooks schema tests."""

    def test_default_values(self) -> None:
        """Default values are empty strings."""
        hooks = BehavioralEconomicsHooks()

        assert hooks.loss_aversion_hook == ""
        assert hooks.social_proof_hook == ""
        assert hooks.authority_hook == ""
        assert hooks.scarcity_hook == ""

    def test_all_four_principles(self) -> None:
        """All four behavioral economics principles are supported."""
        hooks = BehavioralEconomicsHooks(
            loss_aversion_hook="今行動しないと、競合に先を越されるリスクがあります",
            social_proof_hook="すでに1万人以上のユーザーが成功しています",
            authority_hook="業界トップの専門家も推奨している方法です",
            scarcity_hook="この特別価格は今月限定です",
        )

        # Loss aversion (損失回避)
        assert "リスク" in hooks.loss_aversion_hook
        # Social proof (社会的証明)
        assert "1万人" in hooks.social_proof_hook
        # Authority (権威)
        assert "専門家" in hooks.authority_hook
        # Scarcity (希少性)
        assert "限定" in hooks.scarcity_hook

    def test_partial_hooks(self) -> None:
        """Can set only some hooks."""
        hooks = BehavioralEconomicsHooks(
            loss_aversion_hook="損失を避けるために",
            social_proof_hook="多くの人が使っています",
        )

        assert hooks.loss_aversion_hook != ""
        assert hooks.social_proof_hook != ""
        assert hooks.authority_hook == ""
        assert hooks.scarcity_hook == ""


class TestPlacementInstruction:
    """PlacementInstruction schema tests."""

    def test_empathy_placement(self) -> None:
        """Empathy content placement."""
        pi = PlacementInstruction(
            content_type="empathy",
            target_section="導入部分",
            content="あなたの悩みはよく分かります",
        )

        assert pi.content_type == "empathy"
        assert pi.target_section == "導入部分"
        assert "悩み" in pi.content

    def test_episode_placement(self) -> None:
        """Episode content placement."""
        pi = PlacementInstruction(
            content_type="episode",
            target_section="具体的な方法（H2）",
            content="私が実際に試した体験談をお話しします...",
        )

        assert pi.content_type == "episode"
        assert "H2" in pi.target_section

    def test_hook_placement(self) -> None:
        """Hook content placement."""
        pi = PlacementInstruction(
            content_type="hook",
            target_section="まとめ",
            content="今すぐ始めないと機会を逃すかもしれません",
        )

        assert pi.content_type == "hook"
        assert pi.target_section == "まとめ"

    def test_content_type_validation(self) -> None:
        """Content type must be one of empathy, episode, hook."""
        # Valid types
        for content_type in ["empathy", "episode", "hook"]:
            pi = PlacementInstruction(
                content_type=content_type,  # type: ignore
                target_section="test",
                content="test",
            )
            assert pi.content_type == content_type

        # Invalid type should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            PlacementInstruction(
                content_type="invalid",  # type: ignore
                target_section="test",
                content="test",
            )


class TestStep3_5OutputExtensions:
    """Step3_5Output extension tests for blog.System integration."""

    def test_new_fields_exist(self) -> None:
        """New blog.System fields exist in output."""
        output = Step3_5Output(
            step="step3_5",
            keyword="テストキーワード",
        )

        # New fields should exist with defaults
        assert hasattr(output, "phase_emotional_map")
        assert hasattr(output, "behavioral_economics_hooks")
        assert hasattr(output, "placement_instructions")

        # Defaults should be empty/default instances
        assert output.phase_emotional_map.phase1.dominant_emotion == ""
        assert output.behavioral_economics_hooks.loss_aversion_hook == ""
        assert output.placement_instructions == []

    def test_full_blog_system_output(self) -> None:
        """Full output with all blog.System extensions."""
        output = Step3_5Output(
            step="step3_5",
            keyword="SEO対策",
            # Existing fields
            emotional_analysis=EmotionalAnalysis(primary_emotion="curiosity"),
            human_touch_patterns=[HumanTouchPattern(type="experience")],
            experience_episodes=[ExperienceEpisode(scenario="test")],
            emotional_hooks=["hook1"],
            # blog.System extensions
            phase_emotional_map=PhaseEmotionalMap(
                phase1=PhaseEmotionalData(
                    dominant_emotion="不安",
                    empathy_statements=["共感1", "共感2", "共感3"],
                    experience_episodes=[ExperienceEpisode(scenario="phase1体験")],
                ),
                phase2=PhaseEmotionalData(
                    dominant_emotion="冷静",
                    empathy_statements=["共感1", "共感2", "共感3"],
                ),
                phase3=PhaseEmotionalData(
                    dominant_emotion="期待",
                    empathy_statements=["共感1", "共感2", "共感3"],
                ),
            ),
            behavioral_economics_hooks=BehavioralEconomicsHooks(
                loss_aversion_hook="損失回避フック",
                social_proof_hook="社会的証明フック",
                authority_hook="権威フック",
                scarcity_hook="希少性フック",
            ),
            placement_instructions=[
                PlacementInstruction(
                    content_type="empathy",
                    target_section="導入",
                    content="共感コンテンツ",
                ),
                PlacementInstruction(
                    content_type="hook",
                    target_section="まとめ",
                    content="CTAフック",
                ),
            ],
        )

        # Verify phase emotional map
        assert output.phase_emotional_map.phase1.dominant_emotion == "不安"
        assert len(output.phase_emotional_map.phase1.empathy_statements) == 3
        assert len(output.phase_emotional_map.phase1.experience_episodes) == 1

        # Verify behavioral economics hooks
        assert output.behavioral_economics_hooks.loss_aversion_hook != ""
        assert output.behavioral_economics_hooks.social_proof_hook != ""
        assert output.behavioral_economics_hooks.authority_hook != ""
        assert output.behavioral_economics_hooks.scarcity_hook != ""

        # Verify placement instructions
        assert len(output.placement_instructions) == 2
        assert output.placement_instructions[0].content_type == "empathy"
        assert output.placement_instructions[1].content_type == "hook"

    def test_backward_compatibility(self) -> None:
        """Existing fields still work (backward compatibility)."""
        # Create output without new fields - should work
        output = Step3_5Output(
            step="step3_5",
            keyword="test",
            emotional_analysis=EmotionalAnalysis(primary_emotion="hope"),
            human_touch_patterns=[HumanTouchPattern()],
            experience_episodes=[ExperienceEpisode()],
            emotional_hooks=["hook"],
        )

        # Old fields work
        assert output.emotional_analysis.primary_emotion == "hope"
        assert len(output.human_touch_patterns) == 1

        # New fields have defaults
        assert output.phase_emotional_map is not None
        assert output.behavioral_economics_hooks is not None
        assert output.placement_instructions == []
