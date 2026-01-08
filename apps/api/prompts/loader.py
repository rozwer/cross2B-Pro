"""Prompt pack loading and management.

IMPORTANT: Auto-execution without explicit pack_id is forbidden.
All prompt loading requires an explicit pack_id parameter.

Prompts are loaded from JSON files in the packs/ directory.

blog.System Ver8.3 対応:
- unified_knowledge.json の読み込みサポート
- knowledge_path フィールドによる外部知識注入
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PromptPackError(Exception):
    """Error in prompt pack operations."""

    pass


class PromptPackNotFoundError(PromptPackError):
    """Prompt pack does not exist."""

    pass


class PromptNotFoundError(PromptPackError):
    """Prompt for step does not exist in pack."""

    pass


# Directory containing prompt pack JSON files
PACKS_DIR = Path(__file__).parent / "packs"


@dataclass
class PromptTemplate:
    """A single prompt template with variables."""

    step: str
    version: int
    content: str
    variables: dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs: Any) -> str:
        """Render the prompt with provided variables.

        Args:
            **kwargs: Variable values to substitute

        Returns:
            Rendered prompt string

        Raises:
            PromptPackError: If required variable is missing
        """
        result = self.content

        # Check for required variables
        for var_name, var_info in self.variables.items():
            if var_info.get("required", False) and var_name not in kwargs:
                raise PromptPackError(f"Missing required variable: {var_name}")

        # Substitute variables
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"  # {{variable}}
            result = result.replace(placeholder, str(value))

        return result


@dataclass
class PromptPack:
    """Collection of prompts for a workflow.

    A prompt pack contains all prompts needed for a complete workflow run.
    Each step has exactly one prompt template.

    blog.System Ver8.3 対応:
    - knowledge_path: 外部知識ファイルへのパス（unified_knowledge.json等）
    - unified_knowledge: 読み込まれた知識データ（辞書形式）
    """

    pack_id: str
    prompts: dict[str, PromptTemplate] = field(default_factory=dict)
    knowledge_path: str | None = None
    unified_knowledge: dict[str, Any] | None = None

    def get_prompt(self, step: str) -> PromptTemplate:
        """Get prompt template for a step.

        Args:
            step: Step identifier

        Returns:
            PromptTemplate for the step

        Raises:
            PromptNotFoundError: If no prompt exists for the step
        """
        if step not in self.prompts:
            raise PromptNotFoundError(f"No prompt found for step '{step}' in pack '{self.pack_id}'")
        return self.prompts[step]

    def render_prompt(self, step: str, **kwargs: Any) -> str:
        """Render a prompt for a step with variables.

        Args:
            step: Step identifier
            **kwargs: Variable values

        Returns:
            Rendered prompt string
        """
        template = self.get_prompt(step)
        return template.render(**kwargs)

    def list_steps(self) -> list[str]:
        """List all steps with prompts in this pack."""
        return list(self.prompts.keys())


class PromptPackLoader:
    """Loads prompt packs from JSON files.

    CRITICAL: Auto-execution without explicit pack_id is FORBIDDEN.
    All load operations require a non-None pack_id.

    Packs are loaded from apps/api/prompts/packs/{pack_id}.json
    """

    def __init__(self, packs_dir: Path | None = None) -> None:
        """Initialize loader.

        Args:
            packs_dir: Directory containing prompt pack JSON files.
                      Defaults to apps/api/prompts/packs/
        """
        self._packs_dir = packs_dir or PACKS_DIR
        self._cache: dict[str, PromptPack] = {}

    def load(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack by ID from JSON file.

        CRITICAL: pack_id is REQUIRED. Auto-execution is forbidden.

        Args:
            pack_id: Prompt pack identifier (corresponds to {pack_id}.json)

        Returns:
            PromptPack instance

        Raises:
            ValueError: If pack_id is None
            PromptPackNotFoundError: If pack does not exist
        """
        if pack_id is None:
            raise ValueError("pack_id is required. Auto-execution without explicit pack_id is forbidden.")

        # Check cache
        if pack_id in self._cache:
            return self._cache[pack_id]

        # Handle mock pack for testing
        if pack_id == "mock_pack":
            pack = self._load_mock_pack()
            self._cache[pack_id] = pack
            return pack

        # Load from JSON file
        pack = self._load_from_json(pack_id)
        self._cache[pack_id] = pack
        return pack

    async def load_async(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack by ID (async wrapper).

        CRITICAL: pack_id is REQUIRED. Auto-execution is forbidden.

        This is an async wrapper for compatibility. JSON file loading
        is synchronous but wrapped for API consistency.

        Args:
            pack_id: Prompt pack identifier

        Returns:
            PromptPack instance

        Raises:
            ValueError: If pack_id is None
            PromptPackNotFoundError: If pack does not exist
        """
        return self.load(pack_id)

    def _load_from_json(self, pack_id: str) -> PromptPack:
        """Load prompt pack from JSON file.

        Args:
            pack_id: Pack identifier (filename without .json)

        Returns:
            PromptPack instance

        Raises:
            PromptPackNotFoundError: If JSON file not found
            PromptPackError: If JSON is invalid
        """
        json_path = self._packs_dir / f"{pack_id}.json"

        if not json_path.exists():
            raise PromptPackNotFoundError(f"Prompt pack '{pack_id}' not found at {json_path}")

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PromptPackError(f"Invalid JSON in pack '{pack_id}': {e}") from e

        # Parse prompts from JSON
        prompts: dict[str, PromptTemplate] = {}
        prompts_data = data.get("prompts", {})

        for step_id, prompt_data in prompts_data.items():
            prompts[step_id] = PromptTemplate(
                step=prompt_data.get("step", step_id),
                version=prompt_data.get("version", 1),
                content=prompt_data.get("content", ""),
                variables=prompt_data.get("variables", {}),
            )

        # blog.System Ver8.3: knowledge_path の取得
        knowledge_path = data.get("knowledge_path")

        return PromptPack(pack_id=pack_id, prompts=prompts, knowledge_path=knowledge_path)

    def _load_mock_pack(self) -> PromptPack:
        """Load mock prompt pack for testing.

        Prompt structure follows workflow.md specification:
        - Pre-approval: step0, step1, step2, step3a/3b/3c (parallel)
        - Post-approval: step4 → step5 → step6 → step6_5 → step7a → step7b → step8 → step9 → step10

        REVIEW-005: キー名を step_id と一致させる
        Worker/Graph が参照する step0, step1, step3a 等に統一
        """
        return PromptPack(
            pack_id="mock_pack",
            prompts={
                # ========================================
                # Pre-approval steps (工程0-3)
                # ========================================
                "step0": PromptTemplate(
                    step="step0",
                    version=1,
                    content="""# 工程0: キーワード選定

## 入力
- メインキーワード: {{keyword}}
- ターゲットオーディエンス: {{target_audience}}
- 目標CV: {{target_cv}}

## タスク
1. キーワードの検索意図を分析
2. 検索ボリュームと競合度を評価
3. 関連キーワード候補を抽出
4. ターゲット文字数と記事戦略を決定

## 出力形式
JSON形式で以下を出力:
- main_keyword: メインキーワード
- search_volume: 推定検索ボリューム
- difficulty: 競合度(low/medium/high)
- related_keywords: 関連キーワードリスト
- target_word_count: 推奨文字数
- strategy: 記事戦略(standard/pillar/cluster)""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "target_audience": {"required": False, "type": "string"},
                        "target_cv": {"required": False, "type": "string"},
                    },
                ),
                "step1": PromptTemplate(
                    step="step1",
                    version=1,
                    content="""# 工程1: 競合記事本文取得

## 入力
- キーワード: {{keyword}}
- 取得件数上限: {{num_results}}

## タスク
1. SERP検索で上位記事URLを取得
2. 各URLからコンテンツをフェッチ
3. 競合記事のタイトル・見出し・本文を抽出
4. CSV形式で整形

## 注意
- フェッチ失敗時はスキップ（ログ必須）
- 全URL失敗時は即座にエラー終了（フォールバック禁止）""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "num_results": {"required": False, "type": "integer"},
                    },
                ),
                "step2": PromptTemplate(
                    step="step2",
                    version=1,
                    content="""# 工程2: CSV読み込み・検証

## 入力
- 競合データCSV: {{competitor_csv}}

## タスク
1. CSVのスキーマ検証
2. 必須フィールドの存在確認
3. データ整合性チェック
4. 不正データの検出とレポート

## 検証項目
- URL形式の妥当性
- タイトルの文字数制限
- 本文の最低文字数
- 重複データの検出""",
                    variables={
                        "competitor_csv": {"required": True, "type": "string"},
                    },
                ),
                # Step3 parallel tasks
                "step3a": PromptTemplate(
                    step="step3a",
                    version=1,
                    content="""# 工程3A: クエリ分析・ペルソナ

## 入力
- キーワード: {{keyword}}
- キーワード分析: {{keyword_analysis}}
- 競合記事数: {{competitor_count}}

## タスク
1. 検索クエリの意図分析（情報/比較/購買）
2. ターゲットペルソナの設定
3. ユーザーの課題・悩みを特定
4. 解決すべき疑問点のリストアップ

## 4本柱の適用
- 神経科学: 認知負荷を3概念以内に抑制
- 行動経済学: 損失回避・社会的証明を意識

## 出力形式
JSON形式で以下を出力:
- query_intent: 検索意図分類
- persona: ペルソナ情報
- pain_points: 課題・悩みリスト
- questions: 解決すべき疑問リスト""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "keyword_analysis": {"required": False, "type": "string"},
                        "competitor_count": {"required": False, "type": "integer"},
                    },
                ),
                "step3b": PromptTemplate(
                    step="step3b",
                    version=1,
                    content="""# 工程3B: 共起語・関連KW抽出（心臓部）

## 入力
- キーワード: {{keyword}}
- 競合記事要約: {{competitor_summaries}}

## タスク（最重要工程）
1. 共起語の抽出と重要度スコアリング
2. 関連キーワードのクラスタリング
3. LSIキーワードの特定
4. 検索エンジン最適化キーワードの選定

## LLMO最適化
- 各セクション400-600トークン目安
- セクション独立性を確保
- 自然な文脈での共起語配置

## 出力形式
JSON形式で以下を出力:
- cooccurrence_keywords: 共起語リスト（重要度順）
- related_clusters: 関連キーワードクラスター
- lsi_keywords: LSIキーワード
- seo_keywords: SEO最適化キーワード""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "competitor_summaries": {"required": False, "type": "array"},
                    },
                ),
                "step3c": PromptTemplate(
                    step="step3c",
                    version=1,
                    content="""# 工程3C: 競合分析・差別化

## 入力
- キーワード: {{keyword}}
- 競合記事データ: {{competitors}}

## タスク
1. 競合記事の構成分析
2. 各記事の強み・弱みを評価
3. 差別化ポイントの特定
4. 自社記事の勝ち筋を策定

## 分析観点
- コンテンツの網羅性
- 一次情報の有無
- CTA配置の効果
- ユーザー体験（UX）

## 出力形式
JSON形式で以下を出力:
- competitor_analysis: 競合分析結果
- strengths: 競合の強み
- weaknesses: 競合の弱み
- differentiation: 差別化戦略""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "competitors": {"required": False, "type": "array"},
                    },
                ),
                # ========================================
                # Post-approval steps (工程4-10)
                # ========================================
                "step4": PromptTemplate(
                    step="step4",
                    version=1,
                    content="""# 工程4: 戦略的アウトライン

## 入力
- キーワード: {{keyword}}
- クエリ分析: {{query_analysis}}
- 共起語: {{cooccurrence_keywords}}
- 競合分析: {{competitor_analysis}}
- 人間味要素: {{human_touch_elements}}

## タスク
1. 記事全体の構成設計
2. H2/H3見出し階層の決定
3. 各セクションの目的と概要を定義
4. CTA配置箇所の決定（Early/Mid/Final）

## 4本柱の適用
- 神経科学: 3フェーズ構成（Anxiety→Understanding→Action）
- 行動経済学: 6原則を各セクションに配置
- LLMO: 400-600 tokens/section
- KGI: CTA配置（650字/2800字/末尾）

## 出力形式
JSON形式で以下を出力:
- outline: 構成案（H2/H3階層）
- section_purposes: 各セクションの目的
- cta_placements: CTA配置計画
- word_count_targets: セクション別目標文字数""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "query_analysis": {"required": False, "type": "string"},
                        "cooccurrence_keywords": {"required": False, "type": "array"},
                        "competitor_analysis": {"required": False, "type": "string"},
                        "human_touch_elements": {"required": False, "type": "string"},
                    },
                ),
                "step5": PromptTemplate(
                    step="step5",
                    version=1,
                    content="""# 工程5: 一次情報収集

## 入力
- キーワード: {{keyword}}
- 構成案: {{outline}}

## タスク
1. 公的機関データの検索・収集
2. 業界レポートの参照
3. 統計データの取得
4. エビデンスの信頼性評価

## 一次情報ソース例
- 厚生労働省、国土交通省等の政府統計
- 業界団体の調査レポート
- 学術論文・研究データ

## 注意
- 一部URL失敗は許容（成功分で続行、ログ必須）
- 全URL失敗時は即座にエラー終了

## 出力形式
JSON形式で以下を出力:
- sources: 一次情報リスト（source_id, organization, title, date, findings）
- evidence_refs: エビデンス参照情報""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "outline": {"required": False, "type": "string"},
                    },
                ),
                "step6": PromptTemplate(
                    step="step6",
                    version=1,
                    content="""# 工程6: アウトライン強化版

## 入力
- 構成案: {{outline}}
- 一次情報: {{primary_sources}}

## タスク
1. 一次情報を各セクションに配置
2. データアンカーの挿入箇所を決定
3. 出典表記の形式統一
4. セクション間の論理的つながりを強化

## 配置ルール
- 導入部にインパクトのあるデータ
- 各H2に最低1つのエビデンス
- まとめに総括データ

## 出力形式
JSON形式で以下を出力:
- enhanced_outline: 強化版構成案
- source_placements: 一次情報配置マップ
- data_anchors: データアンカー一覧""",
                    variables={
                        "outline": {"required": True, "type": "string"},
                        "primary_sources": {"required": False, "type": "array"},
                    },
                ),
                "step6_5": PromptTemplate(
                    step="step6_5",
                    version=1,
                    content="""# 工程6.5: 統合パッケージ化

## 入力
- キーワード: {{keyword}}
- 強化版構成: {{enhanced_outline}}
- クエリ分析: {{query_analysis}}
- 共起語: {{cooccurrence_keywords}}
- 一次情報: {{primary_sources}}
- 人間味要素: {{human_touch_elements}}
- CTA設定: {{cta_specification}}

## タスク（ファイル集約）
1. 工程0-6の全成果物を統合
2. 執筆指示書の作成
3. セクション別の詳細論理展開を定義
4. 視覚要素（図表）の配置指示

## 統合パッケージ構成
- パート1: 構成案（概要）
- パート2: 参照用データ（工程7以降で使用）

## 出力形式
Markdown形式で統合パッケージを出力""",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "enhanced_outline": {"required": True, "type": "string"},
                        "query_analysis": {"required": False, "type": "string"},
                        "cooccurrence_keywords": {"required": False, "type": "array"},
                        "primary_sources": {"required": False, "type": "array"},
                        "human_touch_elements": {"required": False, "type": "string"},
                        "cta_specification": {"required": False, "type": "object"},
                    },
                ),
                "step7a": PromptTemplate(
                    step="step7a",
                    version=1,
                    content="""# 工程7A: 本文生成 初稿

## 入力
- 統合パッケージ: {{integration_package}}
- 人間味要素: {{human_touch_elements}}

## タスク（最長工程）
1. 統合パッケージに基づき本文を生成
2. 各セクションの論理展開に従って執筆
3. 一次情報を適切に引用・配置
4. CTAを指定位置に挿入

## 執筆ルール
- 1セクション400-600トークン
- 結論ファースト（PREP法）
- データアンカーで信頼性担保
- 行動経済学原則を自然に組み込む

## 4本柱チェック
- 神経科学: 認知負荷3概念以内
- 行動経済学: 6原則の適用
- LLMO: セクション独立性
- KGI: CTA配置確認

## 出力形式
Markdown形式で本文初稿を出力""",
                    variables={
                        "integration_package": {"required": True, "type": "string"},
                        "human_touch_elements": {"required": False, "type": "string"},
                    },
                ),
                "step7b": PromptTemplate(
                    step="step7b",
                    version=1,
                    content="""# 工程7B: ブラッシュアップ

## 入力
- 本文初稿: {{draft}}

## タスク
1. 文体の統一・調整
2. 読みやすさの向上
3. 冗長表現の削除
4. 自然な文章フローの確保

## 調整観点
- 語尾の統一（です・ます調）
- 一文の長さ最適化（40-60文字目安）
- 接続詞の適切な使用
- 専門用語の解説追加

## 出力形式
Markdown形式でブラッシュアップ版を出力""",
                    variables={
                        "draft": {"required": True, "type": "string"},
                    },
                ),
                "step8": PromptTemplate(
                    step="step8",
                    version=1,
                    content="""# 工程8: ファクトチェック・FAQ

## 入力
- ブラッシュアップ版: {{polished_draft}}
- 一次情報: {{primary_sources}}

## タスク
1. 引用データの正確性検証
2. 出典との整合性確認
3. 矛盾点の検出
4. FAQ（よくある質問）の生成

## ファクトチェック項目
- 数値データの正確性
- 出典情報の妥当性
- 時系列の整合性
- 論理的矛盾の有無

## 注意
- 矛盾検出時は却下推奨フラグを立てる
- 自動修正は禁止（人間判断に委ねる）

## 出力形式
JSON形式で以下を出力:
- verification_result: 検証結果
- has_contradictions: 矛盾の有無
- contradiction_details: 矛盾詳細（ある場合）
- faq_items: FAQ項目リスト
- recommend_rejection: 却下推奨フラグ""",
                    variables={
                        "polished_draft": {"required": True, "type": "string"},
                        "primary_sources": {"required": False, "type": "array"},
                    },
                ),
                "step9": PromptTemplate(
                    step="step9",
                    version=1,
                    content="""# 工程9: 最終リライト

## 入力
- ブラッシュアップ版: {{polished_draft}}
- ファクトチェック結果: {{factcheck_result}}
- FAQ: {{faq_items}}

## タスク
1. ファクトチェック結果に基づく修正
2. FAQセクションの統合
3. 全体の最終調整
4. SEO最終チェック

## 最終調整項目
- メタディスクリプション用サマリー
- 見出しのSEO最適化
- 内部リンク候補の提案
- 画像ALTテキスト案

## 出力形式
Markdown形式で最終版本文を出力""",
                    variables={
                        "polished_draft": {"required": True, "type": "string"},
                        "factcheck_result": {"required": False, "type": "object"},
                        "faq_items": {"required": False, "type": "array"},
                    },
                ),
                "step10": PromptTemplate(
                    step="step10",
                    version=1,
                    content="""# 工程10: 最終出力

## 入力
- 最終版本文: {{final_content}}
- CTA設定: {{cta_specification}}

## タスク
1. HTML形式への変換
2. 構造化データ（JSON-LD）の生成
3. 公開前チェックリストの作成
4. 成果物の最終パッケージ化

## HTML生成ルール
- セマンティックHTML5
- 見出しの階層構造を維持
- CTAボタンの適切なマークアップ
- 画像プレースホルダーの挿入

## 出力成果物
- final_article.html: 最終記事HTML
- structured_data.json: 構造化データ
- publication_checklist.md: 公開前チェックリスト
- meta_info.json: メタ情報（タイトル、ディスクリプション等）

## バリデーション
- HTML構文検証必須
- 検証失敗時は即座にエラー終了（壊れたHTML出力禁止）""",
                    variables={
                        "final_content": {"required": True, "type": "string"},
                        "cta_specification": {"required": False, "type": "object"},
                    },
                ),
            },
        )

    def list_packs(self) -> list[str]:
        """List available prompt pack IDs."""
        if not self._packs_dir.exists():
            return []
        return [p.stem for p in self._packs_dir.glob("*.json")]

    def clear_cache(self) -> None:
        """Clear the prompt pack cache."""
        self._cache.clear()

    def invalidate(self, pack_id: str) -> None:
        """Remove a specific pack from cache."""
        self._cache.pop(pack_id, None)

    def load_unified_knowledge(self, pack: PromptPack, base_dir: Path | None = None) -> dict[str, Any] | None:
        """Load unified knowledge from external JSON file.

        blog.System Ver8.3 対応:
        プロンプトパックの knowledge_path が指定されている場合、
        外部の unified_knowledge.json を読み込んでプロンプトに注入可能にする。

        Args:
            pack: PromptPack instance with optional knowledge_path
            base_dir: Base directory for resolving relative paths.
                     Defaults to project root (3 levels up from this file).

        Returns:
            dict[str, Any] | None: Loaded knowledge data, or None if not available

        Example:
            loader = PromptPackLoader()
            pack = loader.load("v2_blog_system")
            knowledge = loader.load_unified_knowledge(pack)
            if knowledge:
                # Use knowledge in prompt rendering
                prompt = pack.render_prompt("step0", keyword="SEO", **knowledge)
        """
        if not pack.knowledge_path:
            return None

        # Already loaded
        if pack.unified_knowledge is not None:
            return pack.unified_knowledge

        # Resolve base directory
        if base_dir is None:
            # Default: project root (apps/api/prompts/loader.py -> 3 levels up)
            base_dir = Path(__file__).parent.parent.parent.parent

        knowledge_path = base_dir / pack.knowledge_path

        if not knowledge_path.exists():
            logger.warning(
                f"Unified knowledge file not found: {knowledge_path} (pack: {pack.pack_id}, knowledge_path: {pack.knowledge_path})"
            )
            return None

        try:
            with open(knowledge_path, encoding="utf-8") as f:
                data = json.load(f)
            # Cache in pack
            pack.unified_knowledge = data
            logger.info(f"Loaded unified knowledge for pack '{pack.pack_id}' from {knowledge_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in unified knowledge file: {knowledge_path}: {e}")
            return None
        except OSError as e:
            logger.error(f"Failed to read unified knowledge file: {knowledge_path}: {e}")
            return None

    def get_pack_with_knowledge(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack and its unified knowledge in one call.

        Convenience method that loads the pack and automatically loads
        unified knowledge if knowledge_path is specified.

        Args:
            pack_id: Prompt pack identifier

        Returns:
            PromptPack with unified_knowledge populated (if available)

        Raises:
            ValueError: If pack_id is None
            PromptPackNotFoundError: If pack does not exist
        """
        pack = self.load(pack_id)
        if pack.knowledge_path:
            self.load_unified_knowledge(pack)
        return pack
