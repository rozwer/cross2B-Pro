"""Step 11 schema tests.

Tests for blog.System Ver8.3 extended schemas:
- ImagePurpose
- EnhancedImageInsertionPosition
- ImagePurposeClassification
- PositionAnalysisEnhanced
- Step11OutputV2
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step11 import (
    EnhancedImageInsertionPosition,
    GeneratedImage,
    ImageGenerationRequest,
    ImageInsertionPosition,
    ImagePurpose,
    ImagePurposeClassification,
    PositionAnalysisEnhanced,
    PositionAnalysisResult,
    Step11Config,
    Step11Output,
    Step11OutputV2,
    Step11State,
    Step11SubStep,
)


class TestImageInsertionPositionBackwardCompatibility:
    """Test ImageInsertionPosition backward compatibility."""

    def test_image_insertion_position_minimal(self):
        """最小限のフィールドで作成可能."""
        position = ImageInsertionPosition(
            section_title="セクション1",
            section_index=0,
        )
        assert position.section_title == "セクション1"
        assert position.section_index == 0
        assert position.article_number is None
        assert position.position == "after"
        assert position.source_text == ""
        assert position.description == ""

    def test_image_insertion_position_full(self):
        """全フィールド指定で作成可能."""
        position = ImageInsertionPosition(
            article_number=1,
            section_title="SEOの基本",
            section_index=2,
            position="before",
            source_text="SEOとは検索エンジン最適化のことで...",
            description="SEOの概念を図解で説明",
        )
        assert position.article_number == 1
        assert position.section_title == "SEOの基本"
        assert position.section_index == 2
        assert position.position == "before"
        assert position.source_text == "SEOとは検索エンジン最適化のことで..."
        assert position.description == "SEOの概念を図解で説明"

    def test_image_insertion_position_invalid_position(self):
        """position は before/after のみ."""
        with pytest.raises(ValidationError):
            ImageInsertionPosition(
                section_title="セクション1",
                section_index=0,
                position="middle",  # Invalid
            )


class TestGeneratedImageBackwardCompatibility:
    """Test GeneratedImage backward compatibility."""

    def test_generated_image_minimal(self):
        """最小限のフィールドで作成可能."""
        position = ImageInsertionPosition(
            section_title="テスト",
            section_index=0,
        )
        request = ImageGenerationRequest(position=position)
        image = GeneratedImage(request=request)
        assert image.image_path == ""
        assert image.image_digest == ""
        assert image.mime_type == "image/png"
        assert image.accepted is False
        assert image.article_number is None

    def test_generated_image_full(self):
        """全フィールド指定で作成可能."""
        position = ImageInsertionPosition(
            section_title="テスト",
            section_index=0,
        )
        request = ImageGenerationRequest(
            position=position,
            user_instruction="明るい色調で",
            generated_prompt="A bright colorful illustration",
            alt_text="SEO概念図",
        )
        image = GeneratedImage(
            request=request,
            image_path="/storage/tenant/run/step11/image_1.png",
            image_digest="abc123",
            image_base64="base64encodeddata",
            mime_type="image/png",
            width=1024,
            height=768,
            file_size=102400,
            retry_count=0,
            accepted=True,
            article_number=1,
        )
        assert image.image_path == "/storage/tenant/run/step11/image_1.png"
        assert image.image_digest == "abc123"
        assert image.width == 1024
        assert image.height == 768
        assert image.file_size == 102400
        assert image.accepted is True
        assert image.article_number == 1


class TestStep11ConfigBackwardCompatibility:
    """Test Step11Config backward compatibility."""

    def test_step11_config_defaults(self):
        """デフォルト値で作成可能."""
        config = Step11Config()
        assert config.enabled is True
        assert config.image_count == 3
        assert config.position_request == ""
        assert config.max_retries_per_image == 3

    def test_step11_config_custom(self):
        """カスタム値で作成可能."""
        config = Step11Config(
            enabled=True,
            image_count=5,
            position_request="冒頭にアイキャッチを",
            max_retries_per_image=2,
        )
        assert config.image_count == 5
        assert config.position_request == "冒頭にアイキャッチを"
        assert config.max_retries_per_image == 2

    def test_step11_config_image_count_bounds(self):
        """image_count は 1-10 の範囲."""
        with pytest.raises(ValidationError):
            Step11Config(image_count=0)
        with pytest.raises(ValidationError):
            Step11Config(image_count=11)


class TestStep11OutputBackwardCompatibility:
    """Test Step11Output backward compatibility."""

    def test_step11_output_disabled(self):
        """画像生成無効時の出力."""
        output = Step11Output(
            step="step11",
            enabled=False,
        )
        assert output.step == "step11"
        assert output.enabled is False
        assert output.image_count == 0
        assert output.images == []
        assert output.markdown_with_images == ""
        assert output.html_with_images == ""

    def test_step11_output_enabled(self):
        """画像生成有効時の出力."""
        position = ImageInsertionPosition(
            section_title="テスト",
            section_index=0,
        )
        request = ImageGenerationRequest(position=position)
        image = GeneratedImage(request=request, accepted=True)

        output = Step11Output(
            step="step11",
            enabled=True,
            image_count=1,
            images=[image],
            markdown_with_images="# 記事\n\n![alt](image.png)",
            html_with_images="<h1>記事</h1><img src='image.png'>",
            model="gemini-2.5-flash-image",
            usage={"tokens": 1000},
        )
        assert output.enabled is True
        assert output.image_count == 1
        assert len(output.images) == 1
        assert output.model == "gemini-2.5-flash-image"


# =============================================================================
# blog.System Ver8.3 新規スキーマテスト
# =============================================================================


class TestImagePurpose:
    """Test ImagePurpose enum."""

    def test_all_purpose_values(self):
        """全ての目的値が定義されている."""
        assert ImagePurpose.HERO == "hero"
        assert ImagePurpose.ILLUSTRATION == "illustration"
        assert ImagePurpose.DATA_VIZ == "data_viz"
        assert ImagePurpose.BREAK == "break"
        assert ImagePurpose.CTA_SUPPORT == "cta_support"
        assert ImagePurpose.PROCESS == "process"
        assert ImagePurpose.COMPARISON == "comparison"

    def test_purpose_is_string_enum(self):
        """ImagePurpose は文字列として使用可能."""
        purpose = ImagePurpose.HERO
        assert purpose.value == "hero"
        assert f"目的: {purpose.value}" == "目的: hero"
        # ImagePurpose(str, Enum) なので文字列比較が可能
        assert purpose == "hero"


class TestEnhancedImageInsertionPosition:
    """Test EnhancedImageInsertionPosition (V2)."""

    def test_enhanced_position_minimal(self):
        """最小限のフィールドで作成可能."""
        position = EnhancedImageInsertionPosition(
            section_title="セクション1",
            section_index=0,
        )
        assert position.section_title == "セクション1"
        assert position.section_index == 0
        assert position.category == "content_gap"  # デフォルト
        assert position.priority == 1  # デフォルト
        assert position.recommendation_reason == ""

    def test_enhanced_position_full(self):
        """全フィールド指定で作成可能."""
        position = EnhancedImageInsertionPosition(
            article_number=2,
            section_title="データ分析",
            section_index=3,
            position="after",
            source_text="データによると...",
            description="グラフで可視化",
            category="data_visualization",
            priority=2,
            recommendation_reason="統計データを視覚的に表現するため",
        )
        assert position.article_number == 2
        assert position.category == "data_visualization"
        assert position.priority == 2
        assert position.recommendation_reason == "統計データを視覚的に表現するため"

    def test_enhanced_position_category_values(self):
        """category は3種類のみ."""
        # 有効な値
        for cat in ["content_gap", "visual_break", "data_visualization"]:
            pos = EnhancedImageInsertionPosition(
                section_title="テスト",
                section_index=0,
                category=cat,
            )
            assert pos.category == cat

        # 無効な値
        with pytest.raises(ValidationError):
            EnhancedImageInsertionPosition(
                section_title="テスト",
                section_index=0,
                category="invalid_category",
            )

    def test_enhanced_position_priority_bounds(self):
        """priority は 1-5 の範囲."""
        # 有効な値
        for p in [1, 3, 5]:
            pos = EnhancedImageInsertionPosition(
                section_title="テスト",
                section_index=0,
                priority=p,
            )
            assert pos.priority == p

        # 無効な値
        with pytest.raises(ValidationError):
            EnhancedImageInsertionPosition(
                section_title="テスト",
                section_index=0,
                priority=0,
            )
        with pytest.raises(ValidationError):
            EnhancedImageInsertionPosition(
                section_title="テスト",
                section_index=0,
                priority=6,
            )


class TestImagePurposeClassification:
    """Test ImagePurposeClassification (V2)."""

    def test_classification_minimal(self):
        """最小限のフィールドで作成可能."""
        classification = ImagePurposeClassification(
            image_index=0,
        )
        assert classification.image_index == 0
        assert classification.purpose == ImagePurpose.ILLUSTRATION  # デフォルト
        assert classification.section_context == ""
        assert classification.target_emotion == ""
        assert classification.four_pillar_relevance == []

    def test_classification_full(self):
        """全フィールド指定で作成可能."""
        classification = ImagePurposeClassification(
            image_index=2,
            purpose=ImagePurpose.DATA_VIZ,
            section_context="ユーザー行動データの分析結果",
            target_emotion="信頼・確信",
            four_pillar_relevance=["behavioral_economics", "kgi"],
        )
        assert classification.image_index == 2
        assert classification.purpose == ImagePurpose.DATA_VIZ
        assert classification.section_context == "ユーザー行動データの分析結果"
        assert classification.target_emotion == "信頼・確信"
        assert classification.four_pillar_relevance == ["behavioral_economics", "kgi"]

    def test_classification_all_purposes(self):
        """全ての ImagePurpose を設定可能."""
        for purpose in ImagePurpose:
            classification = ImagePurposeClassification(
                image_index=0,
                purpose=purpose,
            )
            assert classification.purpose == purpose


class TestPositionAnalysisEnhanced:
    """Test PositionAnalysisEnhanced (V2)."""

    def test_position_analysis_enhanced_defaults(self):
        """デフォルト値で作成可能."""
        analysis = PositionAnalysisEnhanced()
        assert analysis.content_gap_positions == []
        assert analysis.visual_break_positions == []
        assert analysis.data_visualization_positions == []
        assert analysis.total_recommended == 0
        assert analysis.analysis_summary == ""

    def test_position_analysis_enhanced_with_positions(self):
        """位置リストを含めて作成可能."""
        content_gap_pos = EnhancedImageInsertionPosition(
            section_title="概念説明",
            section_index=1,
            category="content_gap",
            priority=1,
        )
        visual_break_pos = EnhancedImageInsertionPosition(
            section_title="長文セクション後",
            section_index=3,
            category="visual_break",
            priority=2,
        )
        data_viz_pos = EnhancedImageInsertionPosition(
            section_title="データ分析",
            section_index=5,
            category="data_visualization",
            priority=3,
        )

        analysis = PositionAnalysisEnhanced(
            content_gap_positions=[content_gap_pos],
            visual_break_positions=[visual_break_pos],
            data_visualization_positions=[data_viz_pos],
            total_recommended=3,
            analysis_summary="コンテンツギャップ: 1件, 視覚的ブレーク: 1件, データ可視化: 1件",
        )
        assert len(analysis.content_gap_positions) == 1
        assert len(analysis.visual_break_positions) == 1
        assert len(analysis.data_visualization_positions) == 1
        assert analysis.total_recommended == 3
        assert "コンテンツギャップ" in analysis.analysis_summary


class TestStep11OutputV2:
    """Test Step11OutputV2 (blog.System Ver8.3)."""

    def test_step11_output_v2_backward_compatible(self):
        """既存フィールドのみで作成可能（後方互換性）."""
        output = Step11OutputV2(
            step="step11",
            enabled=True,
            image_count=2,
        )
        assert output.step == "step11"
        assert output.enabled is True
        assert output.image_count == 2
        assert output.images == []
        # V2 フィールドはデフォルト None
        assert output.position_analysis_enhanced is None
        assert output.image_purpose_classification is None

    def test_step11_output_v2_with_enhanced_analysis(self):
        """V2 拡張フィールドを含めて作成可能."""
        position_analysis = PositionAnalysisEnhanced(
            content_gap_positions=[
                EnhancedImageInsertionPosition(
                    section_title="概念説明",
                    section_index=1,
                    category="content_gap",
                )
            ],
            total_recommended=1,
            analysis_summary="分析完了",
        )

        classification = ImagePurposeClassification(
            image_index=0,
            purpose=ImagePurpose.ILLUSTRATION,
            section_context="SEOの基本概念",
            target_emotion="理解・納得",
            four_pillar_relevance=["llmo"],
        )

        output = Step11OutputV2(
            step="step11",
            enabled=True,
            image_count=1,
            position_analysis_enhanced=position_analysis,
            image_purpose_classification=[classification],
        )
        assert output.position_analysis_enhanced is not None
        assert output.position_analysis_enhanced.total_recommended == 1
        assert output.image_purpose_classification is not None
        assert len(output.image_purpose_classification) == 1
        assert output.image_purpose_classification[0].purpose == ImagePurpose.ILLUSTRATION

    def test_step11_output_v2_serialization(self):
        """model_dump でシリアライズ可能."""
        classification = ImagePurposeClassification(
            image_index=0,
            purpose=ImagePurpose.HERO,
            four_pillar_relevance=["neuroscience", "behavioral_economics"],
        )

        output = Step11OutputV2(
            step="step11",
            enabled=True,
            image_purpose_classification=[classification],
        )

        data = output.model_dump()
        assert data["step"] == "step11"
        assert data["enabled"] is True
        assert data["image_purpose_classification"] is not None
        assert len(data["image_purpose_classification"]) == 1
        assert data["image_purpose_classification"][0]["purpose"] == "hero"

    def test_step11_output_v2_full_workflow(self):
        """完全なワークフロー出力をシミュレート."""
        # 拡張位置分析
        position_analysis = PositionAnalysisEnhanced(
            content_gap_positions=[
                EnhancedImageInsertionPosition(
                    article_number=1,
                    section_title="SEOとは",
                    section_index=0,
                    category="content_gap",
                    priority=1,
                    recommendation_reason="hero画像として導入部の概念を視覚化",
                )
            ],
            visual_break_positions=[
                EnhancedImageInsertionPosition(
                    article_number=1,
                    section_title="詳細説明",
                    section_index=2,
                    category="visual_break",
                    priority=2,
                    recommendation_reason="長文後の視覚的休憩ポイント",
                )
            ],
            data_visualization_positions=[
                EnhancedImageInsertionPosition(
                    article_number=1,
                    section_title="効果測定",
                    section_index=4,
                    category="data_visualization",
                    priority=3,
                    recommendation_reason="数値データのグラフ化",
                )
            ],
            total_recommended=3,
            analysis_summary="コンテンツギャップ: 1件, 視覚的ブレーク: 1件, データ可視化: 1件",
        )

        # 画像目的分類
        classifications = [
            ImagePurposeClassification(
                image_index=0,
                purpose=ImagePurpose.HERO,
                section_context="SEOの基本概念を解説",
                target_emotion="興味・関心",
                four_pillar_relevance=["llmo"],
            ),
            ImagePurposeClassification(
                image_index=1,
                purpose=ImagePurpose.BREAK,
                section_context="詳細な技術解説後",
                target_emotion="休息・リフレッシュ",
                four_pillar_relevance=[],
            ),
            ImagePurposeClassification(
                image_index=2,
                purpose=ImagePurpose.DATA_VIZ,
                section_context="コンバージョン率の推移",
                target_emotion="信頼・確信",
                four_pillar_relevance=["kgi", "behavioral_economics"],
            ),
        ]

        # 生成画像
        position = ImageInsertionPosition(section_title="SEOとは", section_index=0)
        request = ImageGenerationRequest(position=position, alt_text="SEO概念図")
        images = [GeneratedImage(request=request, accepted=True)]

        output = Step11OutputV2(
            step="step11",
            enabled=True,
            image_count=3,
            images=images,
            markdown_with_images="# SEO記事\n\n![SEO概念図](image.png)\n\n本文...",
            html_with_images="<h1>SEO記事</h1><img src='image.png' alt='SEO概念図'>...",
            model="gemini-2.5-flash-image",
            usage={"analysis_tokens": 500, "image_tokens": 1500},
            position_analysis_enhanced=position_analysis,
            image_purpose_classification=classifications,
        )

        # 検証
        assert output.enabled is True
        assert output.image_count == 3
        assert len(output.images) == 1

        # 拡張分析の検証
        assert output.position_analysis_enhanced is not None
        assert len(output.position_analysis_enhanced.content_gap_positions) == 1
        assert len(output.position_analysis_enhanced.visual_break_positions) == 1
        assert len(output.position_analysis_enhanced.data_visualization_positions) == 1
        assert output.position_analysis_enhanced.total_recommended == 3

        # 目的分類の検証
        assert output.image_purpose_classification is not None
        assert len(output.image_purpose_classification) == 3
        assert output.image_purpose_classification[0].purpose == ImagePurpose.HERO
        assert output.image_purpose_classification[1].purpose == ImagePurpose.BREAK
        assert output.image_purpose_classification[2].purpose == ImagePurpose.DATA_VIZ

        # シリアライズ検証
        data = output.model_dump()
        assert data["position_analysis_enhanced"]["total_recommended"] == 3
        assert len(data["image_purpose_classification"]) == 3


class TestStep11StateBackwardCompatibility:
    """Test Step11State backward compatibility."""

    def test_step11_state_defaults(self):
        """デフォルト値で作成可能."""
        state = Step11State()
        assert state.current_substep == Step11SubStep.CONFIRM_IMAGE_GEN
        assert state.config is not None
        assert state.position_analysis is None
        assert state.confirmed_positions == []
        assert state.image_requests == []
        assert state.generated_images == []
        assert state.current_image_index == 0
        assert state.final_markdown == ""
        assert state.final_html == ""

    def test_step11_state_with_substep(self):
        """サブステップを指定して作成可能."""
        state = Step11State(
            current_substep=Step11SubStep.GENERATE_AND_REVIEW,
            current_image_index=2,
        )
        assert state.current_substep == Step11SubStep.GENERATE_AND_REVIEW
        assert state.current_image_index == 2


class TestPositionAnalysisResultBackwardCompatibility:
    """Test PositionAnalysisResult backward compatibility."""

    def test_position_analysis_result_defaults(self):
        """デフォルト値で作成可能."""
        result = PositionAnalysisResult()
        assert result.analysis_summary == ""
        assert result.positions == []
        assert result.model == ""
        assert result.token_usage == {}

    def test_position_analysis_result_with_positions(self):
        """位置リストを含めて作成可能."""
        positions = [
            ImageInsertionPosition(section_title="セクション1", section_index=0),
            ImageInsertionPosition(section_title="セクション2", section_index=1),
        ]
        result = PositionAnalysisResult(
            analysis_summary="2箇所の挿入位置を特定",
            positions=positions,
            model="gemini-2.5-flash",
            token_usage={"input_tokens": 100, "output_tokens": 50},
        )
        assert len(result.positions) == 2
        assert result.model == "gemini-2.5-flash"
        assert result.token_usage["input_tokens"] == 100
