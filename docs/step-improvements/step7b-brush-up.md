# Step7b: Brush Up - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step7b.py` |
| Activity名 | `step7b_brush_up` |
| 使用LLM | Gemini（デフォルト） |
| 目的 | ドラフトの自然言語ポリッシング・読みやすさ向上 |
| 特記 | max_tokens=16000（日本語対応）、temperature=0.8（創造性重視） |

---

## 現状分析

### リトライ戦略

**現状**:
- 汎用的な `Exception` キャッチで `RETRYABLE` 分類
- 空レスポンス時は `RETRYABLE`

**問題点**:
1. **ドラフト欠落時の対応不十分**: step7a が失敗していた場合の検出
2. **ポリッシング品質の検証なし**: 元より悪くなっていないか確認しない
3. **長文処理での切れ対応なし**: Gemini での長文生成も切れる可能性

### フォーマット整形機構

**現状**:
- プレーンマークダウン形式で出力
- コードブロック除去処理あり
- `changes_made` は空リスト（追跡なし）

**問題点**:
1. **変更点の追跡なし**: 何がどう変わったか不明
2. **品質改善の定量化なし**: ポリッシングの効果が測定できない
3. **元ドラフトとの差分不明**: 大幅な変更が入っても検出できない

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ

**問題点**:
1. **長文処理のやり直し**: max_tokens=16000 でも切れる可能性
2. **セクション単位の処理なし**: 一括処理のみ

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 入力品質チェック

```python
class Step7BBrushUp(BaseActivity):
    MIN_DRAFT_LENGTH = 500  # 最低500文字

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        step7a_data = await load_step_data(...) or {}
        draft = step7a_data.get("draft", "")

        if not draft:
            raise ActivityError(
                "Draft is required - run step7a first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if len(draft) < self.MIN_DRAFT_LENGTH:
            raise ActivityError(
                f"Draft too short for polishing: {len(draft)} chars "
                f"(minimum: {self.MIN_DRAFT_LENGTH})",
                category=ErrorCategory.NON_RETRYABLE,
                details={"draft_length": len(draft)},
            )

        # ... ポリッシング処理 ...
```

#### 1.2 ポリッシング品質チェック

```python
def _validate_polish_quality(
    self,
    original: str,
    polished: str,
) -> QualityResult:
    """ポリッシング品質の検証"""
    issues = []

    original_words = len(original.split())
    polished_words = len(polished.split())

    # 大幅な短縮は問題
    if polished_words < original_words * 0.7:
        issues.append(f"content_reduced: {polished_words}/{original_words}")

    # 大幅な増加も問題（水増し）
    if polished_words > original_words * 1.5:
        issues.append(f"content_inflated: {polished_words}/{original_words}")

    # 構造の維持
    original_h2 = len(re.findall(r'^##\s', original, re.M))
    polished_h2 = len(re.findall(r'^##\s', polished, re.M))

    if polished_h2 < original_h2 * 0.8:
        issues.append(f"sections_lost: {polished_h2}/{original_h2}")

    # 空セクションのチェック
    sections = re.split(r'^##\s', polished, flags=re.M)
    empty_sections = sum(1 for s in sections if len(s.strip()) < 50)
    if empty_sections > 1:
        issues.append(f"empty_sections: {empty_sections}")

    return QualityResult(
        is_acceptable=len(issues) == 0,
        issues=issues,
    )
```

#### 1.3 長文切れ対応

```python
def _check_polished_completeness(
    self,
    original: str,
    polished: str,
) -> bool:
    """ポリッシング結果の完全性チェック"""
    # 元の結論セクションが存在するか
    original_has_conclusion = any(
        ind in original.lower()
        for ind in ["まとめ", "結論", "おわり"]
    )

    polished_has_conclusion = any(
        ind in polished.lower()
        for ind in ["まとめ", "結論", "おわり"]
    )

    # 元にあった結論がなくなっている = 切れている可能性
    if original_has_conclusion and not polished_has_conclusion:
        return False

    # 文末チェック
    if polished.rstrip().endswith(("...", "…", "、")):
        return False

    return True
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class PolishChange(BaseModel):
    """ポリッシングによる変更"""
    change_type: str  # "wording", "flow", "clarity", "tone"
    original_snippet: str
    polished_snippet: str
    section: str = ""

class PolishMetrics(BaseModel):
    """ポリッシングメトリクス"""
    original_word_count: int
    polished_word_count: int
    word_diff: int
    word_diff_percent: float
    sections_preserved: int
    sections_modified: int
    readability_improvement: float = 0.0

class Step7bOutput(BaseModel):
    """Step7b の構造化出力"""
    keyword: str
    polished: str
    changes_summary: str = ""
    change_count: int = 0
    polish_metrics: PolishMetrics
    quality_warnings: list[str] = Field(default_factory=list)
```

#### 2.2 変更追跡の実装

```python
def _track_changes(
    self,
    original: str,
    polished: str,
) -> tuple[list[PolishChange], str]:
    """変更を追跡"""
    changes = []

    # セクション単位で比較
    original_sections = self._split_into_sections(original)
    polished_sections = self._split_into_sections(polished)

    for i, (orig_sec, pol_sec) in enumerate(zip(original_sections, polished_sections)):
        if orig_sec != pol_sec:
            # 変更があったセクション
            change_type = self._classify_change(orig_sec, pol_sec)
            changes.append(PolishChange(
                change_type=change_type,
                original_snippet=orig_sec[:100] + "...",
                polished_snippet=pol_sec[:100] + "...",
                section=f"section_{i}",
            ))

    # サマリー生成
    summary = self._generate_change_summary(changes)

    return changes, summary

def _classify_change(self, original: str, polished: str) -> str:
    """変更タイプを分類"""
    len_diff = abs(len(polished) - len(original))
    len_ratio = len_diff / max(len(original), 1)

    if len_ratio > 0.3:
        return "restructure"
    elif "。" in polished and polished.count("。") != original.count("。"):
        return "flow"
    else:
        return "wording"
```

#### 2.3 メトリクス計算

```python
def _calculate_polish_metrics(
    self,
    original: str,
    polished: str,
) -> PolishMetrics:
    """ポリッシングメトリクスを計算"""
    original_words = len(original.split())
    polished_words = len(polished.split())
    word_diff = polished_words - original_words

    original_sections = len(re.findall(r'^##\s', original, re.M))
    polished_sections = len(re.findall(r'^##\s', polished, re.M))

    return PolishMetrics(
        original_word_count=original_words,
        polished_word_count=polished_words,
        word_diff=word_diff,
        word_diff_percent=(word_diff / max(original_words, 1)) * 100,
        sections_preserved=min(original_sections, polished_sections),
        sections_modified=abs(polished_sections - original_sections),
    )
```

### 3. 中途開始機構の実装

#### 3.1 セクション単位のポリッシング（オプション）

```python
async def _polish_by_sections(
    self,
    llm,
    draft: str,
    keyword: str,
) -> str:
    """セクション単位でポリッシング（長文対応）"""
    sections = self._split_into_sections(draft)
    polished_sections = []

    for i, section in enumerate(sections):
        activity.heartbeat(f"Polishing section {i+1}/{len(sections)}")

        # 短いセクションはそのまま
        if len(section) < 200:
            polished_sections.append(section)
            continue

        # セクション単位でポリッシング
        section_prompt = self._render_section_polish_prompt(section, keyword)
        response = await llm.generate(
            messages=[{"role": "user", "content": section_prompt}],
            system_prompt="Polish the following section.",
            config=LLMRequestConfig(max_tokens=4000, temperature=0.8),
        )

        polished_sections.append(response.content)

    return "\n\n".join(polished_sections)
```

---

## ポリッシングの役割

### Step7a → Step7b の流れ

```
[Step7a: 構造・内容重視]
    ↓ ドラフト
[Step7b: 自然さ・読みやすさ重視] ← このステップ
    ↓ ポリッシュ済み
[Step8: ファクトチェック]
```

### ポリッシングの焦点

1. **文章の自然さ**: 硬い表現を柔らかく
2. **読みやすさ**: 長すぎる文を分割
3. **流れ**: セクション間のつながり
4. **トーン**: 一貫した文体

### やってはいけないこと

1. **内容の大幅な変更**: ファクトを変えない
2. **構造の破壊**: セクションを削除しない
3. **過度な短縮**: 重要な情報を削らない
4. **過度な装飾**: 本質を薄めない

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **高** | 品質検証 | 2h | ポリッシング品質保証 |
| **高** | 完全性チェック | 1h | 切れ検出 |
| **中** | メトリクス計算 | 1h | 効果の可視化 |
| **中** | 変更追跡 | 2h | トレーサビリティ |
| **低** | セクション単位処理 | 3h | 長文対応 |

---

## テスト観点

1. **正常系**: ドラフトがポリッシュされる
2. **入力チェック**: 短すぎるドラフトでエラー
3. **品質検証**: 大幅な短縮で警告
4. **構造維持**: セクション数が維持される
5. **完全性**: 結論セクションが維持される
6. **メトリクス**: word_diff が正しく計算される
