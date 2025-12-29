# Step4: Strategic Outline - 改善案

## 概要

| 項目       | 内容                                           |
| ---------- | ---------------------------------------------- |
| ファイル   | `apps/worker/activities/step4.py`              |
| Activity名 | `step4_strategic_outline`                      |
| 使用LLM    | Gemini（デフォルト、model_config で変更可）    |
| 目的       | Step0-3 の分析を統合した戦略的アウトライン生成 |
| 特記       | Post-Approval フェーズの最初のステップ         |

---

## 現状分析

### リトライ戦略

**現状**:

- 汎用的な `Exception` キャッチで `RETRYABLE` 分類
- LLM エラーの詳細分類なし
- Temporal の RetryPolicy に依存

**問題点**:

1. **入力データの欠損チェック不十分**: step3a/3b/3c のいずれかが空でも続行
2. **アウトライン品質の検証なし**: 構造が適切か確認しない
3. **統合ロジックの欠如**: 3つの分析をどう統合するかの明示なし

### フォーマット整形機構

**現状**:

- `outline` として自由形式テキスト保存
- 前ステップのデータを単純に連結してプロンプトに渡す

**問題点**:

1. **アウトライン構造の定義なし**: 見出しレベル、セクション数が不定
2. **必須セクションの保証なし**: 導入、本論、結論の存在を確認しない
3. **キーワード配置の検証なし**: step3b のキーワードが反映されているか不明

### 中途開始機構

**現状**:

- ステップ全体の冪等性のみ
- 3ステップ分のデータロード後にチェックポイントなし

**問題点**:

1. **複数データロードのやり直し**: step3a/3b/3c のロードを毎回実行
2. **統合処理後の保存なし**: プロンプト生成の中間結果がない

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 入力データの品質チェック

```python
class Step4StrategicOutline(BaseActivity):
    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 前ステップのデータロード
        step3a_data = await load_step_data(...) or {}
        step3b_data = await load_step_data(...) or {}
        step3c_data = await load_step_data(...) or {}

        # 入力品質の検証
        input_quality = self._validate_inputs(step3a_data, step3b_data, step3c_data)

        if input_quality.critical_missing:
            raise ActivityError(
                f"Critical inputs missing: {input_quality.critical_missing}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": input_quality.critical_missing},
            )

        if input_quality.warnings:
            activity.logger.warning(
                f"Some inputs incomplete: {input_quality.warnings}"
            )

        # ... 処理続行 ...

    def _validate_inputs(
        self,
        step3a: dict,
        step3b: dict,
        step3c: dict,
    ) -> InputQualityResult:
        """入力データの品質検証"""
        critical_missing = []
        warnings = []

        # Step3a（検索意図・ペルソナ）は必須
        if not step3a.get("query_analysis"):
            critical_missing.append("step3a.query_analysis")

        # Step3b（共起キーワード）は必須
        if not step3b.get("cooccurrence_analysis"):
            critical_missing.append("step3b.cooccurrence_analysis")

        # Step3c（競合分析）は推奨だが必須ではない
        if not step3c.get("competitor_analysis"):
            warnings.append("step3c.competitor_analysis")

        return InputQualityResult(
            critical_missing=critical_missing,
            warnings=warnings,
        )
```

#### 1.2 アウトライン品質チェック

```python
def _validate_outline_quality(self, outline: str, keyword: str) -> QualityResult:
    """アウトラインの品質検証"""
    issues = []

    # 見出し構造のチェック
    h2_count = len(re.findall(r'^##\s', outline, re.M))
    h3_count = len(re.findall(r'^###\s', outline, re.M))

    if h2_count < 3:
        issues.append(f"too_few_h2_sections: {h2_count}")

    if h2_count > 0 and h3_count == 0:
        issues.append("no_h3_subsections")

    # キーワードの含有チェック
    if keyword.lower() not in outline.lower():
        issues.append("keyword_not_in_outline")

    # 必須セクションのチェック
    required_concepts = ["導入", "まとめ", "結論", "introduction", "conclusion"]
    has_intro_conclusion = any(c in outline.lower() for c in required_concepts)
    if not has_intro_conclusion:
        issues.append("no_intro_or_conclusion")

    return QualityResult(
        is_acceptable=len(issues) <= 2,
        issues=issues,
    )
```

#### 1.3 品質不足時のリトライ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # ... 準備処理 ...

    MAX_QUALITY_RETRIES = 1

    for attempt in range(MAX_QUALITY_RETRIES + 1):
        response = await llm.generate(...)

        quality = self._validate_outline_quality(response.content, keyword)

        if quality.is_acceptable:
            break

        if attempt < MAX_QUALITY_RETRIES:
            # 品質改善のためのプロンプト補強
            prompt = self._enhance_prompt_for_quality(prompt, quality.issues)
            activity.logger.warning(
                f"Outline quality retry {attempt + 1}: {quality.issues}"
            )

    return self._structure_output(response, quality)
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field
from typing import Literal

class OutlineSection(BaseModel):
    """アウトラインセクション"""
    level: int = Field(..., ge=1, le=4, description="見出しレベル")
    title: str
    description: str = Field(default="", description="セクション概要")
    target_word_count: int = Field(default=0, description="目標文字数")
    keywords_to_include: list[str] = Field(default_factory=list)
    subsections: list["OutlineSection"] = Field(default_factory=list)

class StrategicOutlineOutput(BaseModel):
    """Step4 の構造化出力"""
    keyword: str
    article_title: str
    meta_description: str = Field(..., max_length=160)
    target_audience: str
    article_type: Literal["how_to", "listicle", "comparison", "guide", "review"]
    estimated_total_words: int
    sections: list[OutlineSection] = Field(..., min_length=3)
    key_differentiators: list[str] = Field(..., min_length=1)
    seo_strategy: str
    content_tone: str
    raw_outline: str

OutlineSection.model_rebuild()  # 自己参照のための再構築
```

#### 2.2 プロンプトでの形式指定

````python
STEP4_OUTPUT_FORMAT = """
以下のJSON形式で戦略的アウトラインを出力してください：

```json
{
  "keyword": "ターゲットキーワード",
  "article_title": "記事タイトル（60文字以内推奨）",
  "meta_description": "メタディスクリプション（160文字以内）",
  "target_audience": "ターゲット読者の説明",
  "article_type": "how_to|listicle|comparison|guide|review",
  "estimated_total_words": 推定総文字数,
  "sections": [
    {
      "level": 2,
      "title": "セクションタイトル",
      "description": "このセクションで扱う内容",
      "target_word_count": 500,
      "keywords_to_include": ["含めるべきキーワード"],
      "subsections": [
        {
          "level": 3,
          "title": "サブセクションタイトル",
          "description": "内容説明",
          "keywords_to_include": []
        }
      ]
    }
  ],
  "key_differentiators": [
    "競合との差別化ポイント"
  ],
  "seo_strategy": "SEO戦略の説明",
  "content_tone": "コンテンツのトーン（専門的/親しみやすい等）",
  "raw_outline": "マークダウン形式の詳細アウトライン"
}
````

重要な制約:

- 最低3つのH2セクションを含める
- 各H2セクションには最低1つのH3サブセクションを推奨
- keywords_to_include には Step3b の共起キーワードを反映
- key_differentiators には Step3c の差別化戦略を反映
  """

````

#### 2.3 出力パーサー

```python
class Step4OutputParser:
    def parse(self, raw_content: str, keyword: str) -> StrategicOutlineOutput:
        """LLM出力をパースして構造化"""
        try:
            json_str = self._extract_json(raw_content)
            data = json.loads(json_str)

            if not data.get("keyword"):
                data["keyword"] = keyword

            return StrategicOutlineOutput(**data)
        except (json.JSONDecodeError, ValidationError):
            return self._extract_from_markdown(raw_content, keyword)

    def _extract_from_markdown(
        self,
        content: str,
        keyword: str,
    ) -> StrategicOutlineOutput:
        """マークダウン形式からアウトライン構造を抽出"""
        sections = self._parse_markdown_headings(content)

        if len(sections) < 3:
            raise OutputParseError(
                f"Too few sections: {len(sections)}",
                raw=content,
            )

        # タイトル抽出（H1 または最初の行）
        title_match = re.search(r'^#\s+(.+)$', content, re.M)
        title = title_match.group(1) if title_match else keyword

        return StrategicOutlineOutput(
            keyword=keyword,
            article_title=title,
            meta_description="",
            target_audience="",
            article_type="guide",
            estimated_total_words=0,
            sections=sections,
            key_differentiators=[],
            seo_strategy="",
            content_tone="",
            raw_outline=content,
        )

    def _parse_markdown_headings(self, content: str) -> list[OutlineSection]:
        """マークダウンの見出しを解析してセクション構造を構築"""
        sections = []
        current_h2 = None

        for line in content.split('\n'):
            h2_match = re.match(r'^##\s+(.+)$', line)
            h3_match = re.match(r'^###\s+(.+)$', line)

            if h2_match:
                if current_h2:
                    sections.append(current_h2)
                current_h2 = OutlineSection(
                    level=2,
                    title=h2_match.group(1),
                    subsections=[],
                )
            elif h3_match and current_h2:
                current_h2.subsections.append(OutlineSection(
                    level=3,
                    title=h3_match.group(1),
                ))

        if current_h2:
            sections.append(current_h2)

        return sections
````

### 3. 中途開始機構の実装

#### 3.1 入力データの統合キャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 統合データのチェックポイント確認
    integrated_checkpoint = await self._load_checkpoint(ctx, "integrated_inputs")

    if integrated_checkpoint:
        integrated_data = integrated_checkpoint["data"]
    else:
        # 各ステップからデータロード
        step3a_data = await load_step_data(...) or {}
        step3b_data = await load_step_data(...) or {}
        step3c_data = await load_step_data(...) or {}

        # 統合処理
        integrated_data = self._integrate_analysis_data(
            keyword=keyword,
            query_analysis=step3a_data.get("query_analysis", ""),
            cooccurrence=step3b_data.get("cooccurrence_analysis", ""),
            competitor=step3c_data.get("competitor_analysis", ""),
        )

        # チェックポイント保存
        await self._save_checkpoint(ctx, "integrated_inputs", {
            "data": integrated_data,
        })

    # ... プロンプト生成・LLM呼び出し ...
```

#### 3.2 統合処理ロジック

```python
def _integrate_analysis_data(
    self,
    keyword: str,
    query_analysis: str,
    cooccurrence: str,
    competitor: str,
) -> dict[str, Any]:
    """3つの分析データを戦略立案用に統合"""
    return {
        "keyword": keyword,
        "user_context": {
            "source": "step3a",
            "analysis": query_analysis,
            "summary": self._summarize_for_outline(query_analysis, 500),
        },
        "seo_context": {
            "source": "step3b",
            "analysis": cooccurrence,
            "keywords": self._extract_keyword_list(cooccurrence),
        },
        "competitive_context": {
            "source": "step3c",
            "analysis": competitor,
            "differentiators": self._extract_differentiators(competitor),
        },
    }

def _summarize_for_outline(self, text: str, max_length: int) -> str:
    """アウトライン用に要約"""
    if len(text) <= max_length:
        return text
    # 文単位で切り詰め
    sentences = text.split('。')
    result = ""
    for s in sentences:
        if len(result) + len(s) + 1 > max_length:
            break
        result += s + '。'
    return result or text[:max_length]

def _extract_keyword_list(self, cooccurrence: str) -> list[str]:
    """共起分析からキーワードリストを抽出"""
    keywords = []
    # リスト形式のキーワードを抽出
    patterns = [
        r'[・\-\*]\s*([^\n]+)',
        r'\d+\.\s*([^\n]+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, cooccurrence)
        for match in matches:
            if len(match) < 30:  # 短いものはキーワードと判断
                keywords.append(match.strip())
    return keywords[:20]  # 上位20件
```

---

## 統合ステップとしての役割

### 入力と出力の関係

```
[Step3a: 検索意図・ペルソナ] ─┐
                              │
[Step3b: 共起キーワード]    ─┼→ [Step4: 戦略的アウトライン]
                              │
[Step3c: 競合差別化]       ─┘
                                        ↓
                              [Step5-10: コンテンツ生成]
```

### Step4 の重要性

Step4 は**設計図**を作成するステップであり、以後のすべてのステップに影響します：

- **Step5**: アウトラインに基づいて一次資料を収集
- **Step6**: アウトラインを拡張・詳細化
- **Step7a**: アウトラインに沿ってドラフトを生成
- **Step8-10**: アウトラインの構造を維持して仕上げ

---

## 優先度と実装順序

| 優先度   | 改善項目                 | 工数見積 | 理由                       |
| -------- | ------------------------ | -------- | -------------------------- |
| **最高** | 構造化出力スキーマ       | 3h       | 後続全ステップの品質に直結 |
| **最高** | 入力品質チェック         | 2h       | ガベージイン防止           |
| **高**   | 出力パーサー             | 2h       | 構造化の基盤               |
| **高**   | アウトライン品質チェック | 2h       | 出力品質保証               |
| **中**   | 統合データキャッシュ     | 1h       | 再実行効率化               |
| **中**   | 統合処理ロジック         | 2h       | 分析活用の改善             |

---

## テスト観点

1. **正常系**: 構造化アウトラインが正しく生成される
2. **入力欠損**: step3a/3b 欠落でエラー、step3c 欠落で警告
3. **構造検証**: 最低3セクション、見出し階層の正当性
4. **キーワード反映**: step3b のキーワードがアウトラインに含まれる
5. **パース失敗**: マークダウン形式からも構造抽出可能
6. **品質リトライ**: 品質不足時にリトライが発動
