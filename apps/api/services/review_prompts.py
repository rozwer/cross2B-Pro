"""Review prompt templates for Claude Code integration.

Provides structured prompts for different review perspectives:
- Fact check: Verify accuracy and currency of information
- SEO: Analyze keyword density, heading structure, meta info
- Quality: Check readability, typos, tone consistency
- All: Combined review with all perspectives
"""

from enum import Enum


class ReviewType(str, Enum):
    """Review type enumeration."""

    FACT_CHECK = "fact_check"
    SEO = "seo"
    QUALITY = "quality"
    ALL = "all"


# Base instruction for output format
OUTPUT_INSTRUCTION = """
**出力形式:** JSON

結果を以下のJSON形式で `{output_path}` に保存してください:

```json
{{
  "review_type": "{review_type}",
  "issues": [
    {{
      "severity": "high|medium|low",
      "category": "カテゴリ名",
      "location": "問題箇所（見出しや段落番号）",
      "original": "元のテキスト",
      "issue": "問題の説明",
      "suggestion": "修正案"
    }}
  ],
  "summary": {{
    "total_issues": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "overall_assessment": "全体評価コメント"
  }},
  "passed": true|false
}}
```

レビュー完了後、このIssueにコメントで結果のサマリーを投稿してください。
"""

FACT_CHECK_PROMPT = """@claude

## レビュー依頼: ファクトチェック（事実確認）

**対象ファイル:** `{file_path}`

**レビュー観点:**
1. **事実の正確性**: 記載された情報が事実と異なっていないか
2. **情報の鮮度**: 統計データや日付が古くなっていないか（現在は2026年1月）
3. **出典の信頼性**: 引用元が明示されているか、信頼できる情報源か
4. **数値の妥当性**: 数字や統計が現実的で整合性があるか

**チェック項目:**
- [ ] 固有名詞（会社名、製品名、人名）の正確性
- [ ] 法律・制度に関する記述の正確性
- [ ] 統計データの出典と更新日
- [ ] URL・リンク先の有効性（存在確認のみ）
- [ ] 専門用語の正確な使用

{output_instruction}

---
*Run ID: {run_id}*
*Step: {step}*
"""

SEO_PROMPT = """@claude

## レビュー依頼: SEO最適化チェック

**対象ファイル:** `{file_path}`

**レビュー観点:**
1. **キーワード配置**: 主要キーワードがタイトル、見出し、本文に適切に配置されているか
2. **見出し構造**: H1〜H6の階層が論理的で、SEO効果的か
3. **メタ情報**: タイトルタグ、メタディスクリプションの最適化
4. **内部リンク**: 関連コンテンツへのリンク構造
5. **読了性**: 段落の長さ、箇条書きの活用

**チェック項目:**
- [ ] タイトルに主要キーワードが含まれているか
- [ ] H1が1つだけ存在し、適切な内容か
- [ ] H2-H3の構造が論理的か
- [ ] 本文中のキーワード密度（目安: 1-3%）
- [ ] 画像のalt属性（存在する場合）
- [ ] メタディスクリプションの長さ（120-160文字）

{output_instruction}

---
*Run ID: {run_id}*
*Step: {step}*
"""

QUALITY_PROMPT = """@claude

## レビュー依頼: 文章品質チェック

**対象ファイル:** `{file_path}`

**レビュー観点:**
1. **可読性**: 文章が読みやすく、理解しやすいか
2. **誤字脱字**: タイポや変換ミスがないか
3. **文体統一**: 敬体・常体が混在していないか
4. **論理構成**: 導入→本論→結論の流れが明確か
5. **冗長性**: 無駄な繰り返しや回りくどい表現がないか

**チェック項目:**
- [ ] 誤字・脱字・変換ミス
- [ ] 句読点の適切な使用
- [ ] 文体（です・ます調 or だ・である調）の統一
- [ ] 一文の長さ（目安: 60文字以内）
- [ ] 段落の適切な分割
- [ ] 専門用語の説明が適切か

{output_instruction}

---
*Run ID: {run_id}*
*Step: {step}*
"""

ALL_REVIEW_PROMPT = """@claude

## 総合レビュー依頼: 全観点チェック

**対象ファイル:** `{file_path}`

この記事を以下の3つの観点から総合的にレビューしてください。

---

### 1. ファクトチェック（事実確認）

**チェック項目:**
- 事実の正確性（固有名詞、数値、法律など）
- 情報の鮮度（統計データ、日付）
- 出典の信頼性

---

### 2. SEO最適化

**チェック項目:**
- キーワード配置（タイトル、見出し、本文）
- 見出し構造（H1-H6の階層）
- メタ情報の最適化

---

### 3. 文章品質

**チェック項目:**
- 可読性と理解しやすさ
- 誤字脱字
- 文体統一
- 論理構成

---

{output_instruction}

---
*Run ID: {run_id}*
*Step: {step}*
"""


def get_review_prompt(
    review_type: ReviewType,
    file_path: str,
    output_path: str,
    run_id: str,
    step: str,
) -> str:
    """Get the appropriate review prompt for the given type.

    Args:
        review_type: Type of review to perform
        file_path: Path to the file being reviewed
        output_path: Path where review results should be saved
        run_id: Run ID for tracking
        step: Step name for tracking

    Returns:
        Formatted prompt string
    """
    output_instruction = OUTPUT_INSTRUCTION.format(
        output_path=output_path,
        review_type=review_type.value,
    )

    prompts = {
        ReviewType.FACT_CHECK: FACT_CHECK_PROMPT,
        ReviewType.SEO: SEO_PROMPT,
        ReviewType.QUALITY: QUALITY_PROMPT,
        ReviewType.ALL: ALL_REVIEW_PROMPT,
    }

    template = prompts[review_type]
    return template.format(
        file_path=file_path,
        output_instruction=output_instruction,
        run_id=run_id,
        step=step,
    )


def get_review_title(review_type: ReviewType, step: str, dir_path: str) -> str:
    """Get the issue title for the review.

    Args:
        review_type: Type of review
        step: Step name
        dir_path: Directory path in the repository

    Returns:
        Issue title string
    """
    type_labels = {
        ReviewType.FACT_CHECK: "ファクトチェック",
        ReviewType.SEO: "SEO最適化",
        ReviewType.QUALITY: "文章品質",
        ReviewType.ALL: "総合レビュー",
    }
    label = type_labels[review_type]
    return f"[Claude Code Review] {label} - {step} ({dir_path})"
