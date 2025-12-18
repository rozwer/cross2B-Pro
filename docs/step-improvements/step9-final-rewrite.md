# Step9: Final Rewrite - 改善案

## 概要

| 項目       | 内容                                            |
| ---------- | ----------------------------------------------- |
| ファイル   | `apps/worker/activities/step9.py`               |
| Activity名 | `step9_final_rewrite`                           |
| 使用LLM    | Claude（デフォルト: anthropic）                 |
| 目的       | ファクトチェック結果とFAQを反映した最終リライト |
| 特記       | max_tokens=16000（日本語対応）                  |

---

## 現状分析

### リトライ戦略

**現状**:

- 汎用的な `Exception` キャッチで `RETRYABLE`
- 空レスポンス時は `RETRYABLE`

**問題点**:

1. **入力品質チェック不十分**: step7b/step8 のデータ欠落時の対応
2. **リライト品質の検証なし**: ファクトチェック指摘が反映されたか確認しない
3. **FAQ統合の検証なし**: FAQが適切に組み込まれたか確認しない

### フォーマット整形機構

**現状**:

- プレーンマークダウン形式で出力
- コードブロック除去処理あり
- `meta_description`, `internal_link_suggestions` は空（未使用）

**問題点**:

1. **ファクトチェック反映の追跡なし**: 修正箇所が分からない
2. **FAQ配置の検証なし**: FAQセクションの存在を確認しない
3. **品質メトリクスなし**: step7b からの変更量が不明

### 中途開始機構

**現状**:

- ステップ全体の冪等性のみ

**問題点**:

1. **入力データロードのやり直し**: step7b/step8 データを毎回ロード

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 入力品質チェック

```python
class Step9FinalRewrite(BaseActivity):
    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        step7b_data = await load_step_data(...) or {}
        step8_data = await load_step_data(...) or {}

        polished_content = step7b_data.get("polished", "")
        faq_content = step8_data.get("faq", "")
        verification = step8_data.get("verification", "")

        # 必須入力チェック
        if not polished_content:
            raise ActivityError(
                "Polished content required - run step7b first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # 推奨入力チェック
        if not faq_content:
            activity.logger.warning("No FAQ content - proceeding without FAQ")

        if not verification:
            activity.logger.warning("No verification notes - proceeding without corrections")

        # ファクトチェックで矛盾があった場合の警告
        if step8_data.get("has_contradictions"):
            activity.logger.warning(
                "Content has contradictions - ensure corrections are applied"
            )

        # ... リライト処理 ...
```

#### 1.2 リライト品質検証

```python
def _validate_rewrite_quality(
    self,
    polished: str,
    final: str,
    step8_data: dict,
) -> QualityResult:
    """リライト品質の検証"""
    issues = []

    # 長さチェック（大幅な変化は問題）
    polished_len = len(polished)
    final_len = len(final)

    if final_len < polished_len * 0.8:
        issues.append(f"content_reduced: {final_len}/{polished_len}")

    # FAQ セクションの存在チェック
    faq_content = step8_data.get("faq", "")
    if faq_content:
        faq_indicators = ["FAQ", "よくある質問", "Q&A", "Q:", "A:"]
        has_faq = any(ind in final for ind in faq_indicators)
        if not has_faq:
            issues.append("faq_not_integrated")

    # 構造維持チェック
    polished_h2 = len(re.findall(r'^##\s', polished, re.M))
    final_h2 = len(re.findall(r'^##\s', final, re.M))

    if final_h2 < polished_h2:
        issues.append(f"sections_reduced: {final_h2}/{polished_h2}")

    # 矛盾修正の反映チェック（簡易）
    if step8_data.get("has_contradictions"):
        # 検証コメントに言及されたキーワードが修正されたか
        # （完全な検証は困難なので警告のみ）
        issues.append("contradiction_correction_unverified")

    return QualityResult(
        is_acceptable=len(issues) <= 1,
        issues=issues,
    )
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class RewriteChange(BaseModel):
    """リライトによる変更"""
    change_type: str  # "factcheck_correction", "faq_addition", "style", "structure"
    section: str = ""
    description: str = ""

class RewriteMetrics(BaseModel):
    """リライトメトリクス"""
    original_word_count: int
    final_word_count: int
    word_diff: int
    sections_count: int
    faq_integrated: bool = False
    factcheck_corrections_applied: int = 0

class Step9Output(BaseModel):
    """Step9 の構造化出力"""
    keyword: str
    final_content: str
    meta_description: str = Field(
        default="",
        max_length=160,
        description="SEO用メタディスクリプション"
    )
    changes_summary: list[RewriteChange] = Field(default_factory=list)
    rewrite_metrics: RewriteMetrics
    internal_link_suggestions: list[str] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)
```

#### 2.2 プロンプトでの形式指定

```python
STEP9_INSTRUCTIONS = """
以下の記事を最終リライトしてください。

## 入力
1. ポリッシュ済み記事
2. ファクトチェック結果と修正指示
3. FAQ（記事末尾に統合）

## リライト指示
1. ファクトチェックで指摘された問題を修正
2. FAQセクションを記事末尾に適切に配置
3. 全体の流れと一貫性を確認
4. メタディスクリプション（160文字以内）を生成

## 出力形式
マークダウン形式で記事全文を出力してください。
記事の最後には必ず「## よくある質問」または「## FAQ」セクションを含めてください。

最後に以下の形式でメタディスクリプションを追加：
<!--META_DESCRIPTION: ここにメタディスクリプション -->
"""
```

#### 2.3 メタディスクリプション抽出

```python
def _extract_meta_description(self, content: str) -> str:
    """コンテンツからメタディスクリプションを抽出"""
    # 明示的なメタディスクリプションタグ
    meta_match = re.search(
        r'<!--\s*META_DESCRIPTION:\s*(.+?)\s*-->',
        content,
        re.IGNORECASE,
    )
    if meta_match:
        return meta_match.group(1)[:160]

    # なければ最初の段落から生成
    paragraphs = content.split('\n\n')
    for p in paragraphs:
        # 見出しでない段落
        if not p.startswith('#') and len(p) > 50:
            # 句点で区切って160文字以内に
            sentences = p.split('。')
            description = ""
            for s in sentences:
                if len(description) + len(s) + 1 <= 160:
                    description += s + '。'
                else:
                    break
            return description or p[:160]

    return ""
```

### 3. 中途開始機構の実装

#### 3.1 入力データのキャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 入力データのチェックポイント
    input_checkpoint = await self._load_checkpoint(ctx, "inputs_loaded")

    if input_checkpoint:
        polished_content = input_checkpoint["polished"]
        faq_content = input_checkpoint["faq"]
        verification = input_checkpoint["verification"]
    else:
        step7b_data = await load_step_data(...) or {}
        step8_data = await load_step_data(...) or {}

        polished_content = step7b_data.get("polished", "")
        faq_content = step8_data.get("faq", "")
        verification = step8_data.get("verification", "")

        await self._save_checkpoint(ctx, "inputs_loaded", {
            "polished": polished_content,
            "faq": faq_content,
            "verification": verification,
            "has_contradictions": step8_data.get("has_contradictions", False),
        })

    # ... LLM呼び出し ...
```

---

## リライトの役割

### Step7b → Step9 の変更点

| 観点 | Step7b          | Step9             |
| ---- | --------------- | ----------------- |
| 目的 | 読みやすさ向上  | 品質完成          |
| 入力 | step7a ドラフト | step7b + step8    |
| 変更 | 文体・流れ      | 内容修正・FAQ追加 |
| LLM  | Gemini          | Claude            |

### 品質完成としての責務

1. **ファクトチェック反映**: 矛盾・誤りの修正
2. **FAQ統合**: 適切な位置への配置
3. **最終確認**: 構造・流れの最終チェック
4. **メタデータ生成**: SEO用メタディスクリプション

---

## 優先度と実装順序

| 優先度 | 改善項目                   | 工数見積 | 理由             |
| ------ | -------------------------- | -------- | ---------------- |
| **高** | FAQ統合検証                | 1h       | FAQ配置の保証    |
| **高** | 入力品質チェック           | 1h       | 欠落データ対応   |
| **中** | メタディスクリプション抽出 | 1h       | SEO対応          |
| **中** | リライトメトリクス         | 1h       | 変更量の可視化   |
| **低** | 変更追跡                   | 2h       | トレーサビリティ |
| **低** | 入力キャッシュ             | 1h       | 効率化           |

---

## テスト観点

1. **正常系**: ファクトチェック結果を反映した最終コンテンツ
2. **FAQ統合**: FAQセクションが記事末尾に存在
3. **入力欠落**: step7b なしでエラー、step8 なしで警告
4. **メタディスクリプション**: 160文字以内で生成
5. **構造維持**: セクション数が減少しない
6. **矛盾警告**: has_contradictions 時に警告ログ
