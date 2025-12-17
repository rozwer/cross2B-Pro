# Step10: Final Output - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step10.py` |
| Activity名 | `step10_final_output` |
| 使用LLM | Claude（デフォルト: anthropic） |
| 目的 | 最終記事のHTML生成と出版チェックリスト作成 |
| 特記 | ワークフロー最終ステップ、2回のLLM呼び出し |

---

## 現状分析

### リトライ戦略

**現状**:
- HTML生成失敗は `RETRYABLE`
- チェックリスト生成失敗は**黙殺**（Line 125-127）
- 汎用的な `Exception` キャッチ

**問題点**:
1. **チェックリスト失敗の黙殺**: 重要な品質チェック項目が欠落しても続行
2. **HTML生成のリトライ条件不明**: どのような失敗でリトライするか不明瞭
3. **入力品質チェック不十分**: step9 データの品質確認なし

**重大な問題** (Line 125-127):
```python
except Exception:
    # Checklist is nice-to-have, continue if fails
    checklist = "Publication checklist generation failed."
```
→ **フォールバック禁止ルール違反の可能性**。失敗をダミー文字列で置換している。

### フォーマット整形機構

**現状**:
- `markdown` と `html` の両形式で出力
- 基本的なHTML構造検証のみ（`_validate_html`）
- `stats` で文字数・単語数を計算

**問題点**:
1. **HTML検証が粗い**: タグの開閉数カウントのみ
2. **SEOメタデータの検証なし**: title, description, OGP 等
3. **アクセシビリティチェックなし**: alt, heading階層等
4. **出力形式の統一性なし**: HTML構造がLLM依存

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ
- HTML生成とチェックリスト生成に分離なし

**問題点**:
1. **部分結果の保存なし**: HTML生成成功→チェックリスト失敗で全やり直し
2. **最終検証前のチェックポイントなし**: 長時間処理のリカバリ困難

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 入力品質チェック

```python
class Step10FinalOutput(BaseActivity):
    MIN_CONTENT_LENGTH = 1000  # 最低1000文字

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        step9_data = await load_step_data(...) or {}
        final_content = step9_data.get("final_content", "")

        # 入力品質検証
        if not final_content:
            raise ActivityError(
                "Final content required - run step9 first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if len(final_content) < self.MIN_CONTENT_LENGTH:
            raise ActivityError(
                f"Content too short for final output: {len(final_content)} chars "
                f"(minimum: {self.MIN_CONTENT_LENGTH})",
                category=ErrorCategory.NON_RETRYABLE,
                details={"content_length": len(final_content)},
            )

        # 構造チェック（見出しが存在するか）
        has_headings = any(line.startswith('#') for line in final_content.split('\n'))
        if not has_headings:
            activity.logger.warning("Content has no markdown headings")

        # ... 処理続行 ...
```

#### 1.2 チェックリスト生成の改善

```python
async def _generate_checklist(
    self,
    llm,
    prompt_pack,
    keyword: str,
) -> tuple[str, int]:
    """チェックリスト生成（失敗時は明示的に空）"""
    MAX_CHECKLIST_RETRIES = 1

    for attempt in range(MAX_CHECKLIST_RETRIES + 1):
        try:
            checklist_prompt = prompt_pack.get_prompt("step10_checklist")
            checklist_request = checklist_prompt.render(keyword=keyword)
            response = await llm.generate(
                messages=[{"role": "user", "content": checklist_request}],
                system_prompt="You are a publication checklist expert.",
                config=LLMRequestConfig(max_tokens=1000, temperature=0.3),
            )

            # チェックリストの品質検証
            if self._validate_checklist(response.content):
                return response.content, response.token_usage.output

            if attempt < MAX_CHECKLIST_RETRIES:
                activity.logger.warning(
                    f"Checklist quality insufficient, retrying: {attempt + 1}"
                )

        except Exception as e:
            if attempt < MAX_CHECKLIST_RETRIES:
                activity.logger.warning(f"Checklist generation error, retrying: {e}")
            else:
                activity.logger.error(f"Checklist generation failed: {e}")

    # 失敗時は空リストを返す（ダミー文字列ではなく）
    return "", 0

def _validate_checklist(self, checklist: str) -> bool:
    """チェックリストの品質検証"""
    if len(checklist) < 100:
        return False

    # チェックリスト項目の存在確認
    checklist_indicators = ["□", "☐", "[ ]", "✓", "・", "-", "*", "1.", "2."]
    has_items = any(ind in checklist for ind in checklist_indicators)

    return has_items
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class HTMLValidationResult(BaseModel):
    """HTML検証結果"""
    is_valid: bool
    has_required_tags: bool = False
    has_meta_tags: bool = False
    has_proper_heading_hierarchy: bool = False
    has_alt_attributes: bool = False
    issues: list[str] = Field(default_factory=list)

class ArticleStats(BaseModel):
    """記事統計"""
    word_count: int
    char_count: int
    paragraph_count: int
    heading_count: int
    image_count: int = 0
    link_count: int = 0

class PublicationReadiness(BaseModel):
    """出版準備状態"""
    is_ready: bool
    checklist_completed: int
    checklist_total: int
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class Step10Output(BaseModel):
    """Step10 の構造化出力"""
    keyword: str
    article_title: str
    markdown_content: str
    html_content: str
    meta_description: str = ""
    publication_checklist: str
    html_validation: HTMLValidationResult
    stats: ArticleStats
    publication_readiness: PublicationReadiness
```

#### 2.2 HTML検証の強化

```python
def _validate_html_comprehensive(self, html_content: str) -> HTMLValidationResult:
    """包括的なHTML検証"""
    issues = []

    # 必須タグチェック
    required_tags = {
        "<html": "html tag missing",
        "<head": "head tag missing",
        "<body": "body tag missing",
        "<title": "title tag missing",
    }

    has_required = True
    for tag, error in required_tags.items():
        if tag not in html_content.lower():
            issues.append(error)
            has_required = False

    # メタタグチェック
    meta_tags = ["<meta name=\"description\"", "<meta property=\"og:"]
    has_meta = any(tag in html_content.lower() for tag in meta_tags)
    if not has_meta:
        issues.append("SEO meta tags missing")

    # 見出し階層チェック
    import re
    h1_count = len(re.findall(r'<h1[^>]*>', html_content, re.I))
    h2_count = len(re.findall(r'<h2[^>]*>', html_content, re.I))

    has_proper_hierarchy = h1_count == 1 and h2_count > 0
    if h1_count != 1:
        issues.append(f"H1 count should be 1, found {h1_count}")
    if h2_count == 0:
        issues.append("No H2 headings found")

    # alt属性チェック
    img_tags = re.findall(r'<img[^>]*>', html_content, re.I)
    imgs_without_alt = [img for img in img_tags if 'alt=' not in img.lower()]
    has_alt = len(imgs_without_alt) == 0

    if imgs_without_alt:
        issues.append(f"{len(imgs_without_alt)} images without alt attribute")

    return HTMLValidationResult(
        is_valid=len(issues) <= 2,  # 軽微な問題は許容
        has_required_tags=has_required,
        has_meta_tags=has_meta,
        has_proper_heading_hierarchy=has_proper_hierarchy,
        has_alt_attributes=has_alt,
        issues=issues,
    )
```

#### 2.3 記事統計の計算

```python
def _calculate_article_stats(
    self,
    markdown: str,
    html: str,
) -> ArticleStats:
    """記事統計を計算"""
    import re

    # 単語数（日本語対応）
    # 日本語は文字数ベース、英語は単語数ベース
    japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', markdown))
    english_words = len(re.findall(r'[a-zA-Z]+', markdown))
    word_count = japanese_chars + english_words

    # 文字数
    char_count = len(markdown)

    # 段落数
    paragraphs = [p for p in markdown.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    # 見出し数
    heading_count = len(re.findall(r'^#+\s', markdown, re.M))

    # 画像数
    image_count = len(re.findall(r'!\[', markdown))

    # リンク数
    link_count = len(re.findall(r'\[([^\]]+)\]\([^\)]+\)', markdown))

    return ArticleStats(
        word_count=word_count,
        char_count=char_count,
        paragraph_count=paragraph_count,
        heading_count=heading_count,
        image_count=image_count,
        link_count=link_count,
    )
```

#### 2.4 出版準備状態の評価

```python
def _evaluate_publication_readiness(
    self,
    html_validation: HTMLValidationResult,
    stats: ArticleStats,
    checklist: str,
) -> PublicationReadiness:
    """出版準備状態を評価"""
    blocking_issues = []
    warnings = []

    # ブロッキング条件
    if not html_validation.is_valid:
        blocking_issues.extend(
            f"HTML: {issue}" for issue in html_validation.issues[:3]
        )

    if stats.char_count < 1000:
        blocking_issues.append(f"Content too short: {stats.char_count} chars")

    if stats.heading_count < 3:
        blocking_issues.append(f"Too few headings: {stats.heading_count}")

    # 警告条件
    if not html_validation.has_meta_tags:
        warnings.append("SEO meta tags missing")

    if not html_validation.has_alt_attributes:
        warnings.append("Some images missing alt attributes")

    if not checklist:
        warnings.append("Publication checklist not generated")

    # チェックリスト完了率
    checklist_items = len(re.findall(r'[□☐\[\s*\]]', checklist))
    checklist_completed = len(re.findall(r'[✓☑\[x\]]', checklist))

    return PublicationReadiness(
        is_ready=len(blocking_issues) == 0,
        checklist_completed=checklist_completed,
        checklist_total=checklist_items,
        blocking_issues=blocking_issues,
        warnings=warnings,
    )
```

### 3. 中途開始機構の実装

#### 3.1 HTML生成のチェックポイント

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # HTML生成のチェックポイント確認
    html_checkpoint = await self._load_checkpoint(ctx, "html_generated")

    if html_checkpoint:
        html_content = html_checkpoint["html"]
        html_tokens = html_checkpoint["tokens"]
    else:
        # HTML生成
        html_content, html_tokens = await self._generate_html(
            llm, prompt_pack, keyword, final_content
        )

        # チェックポイント保存
        await self._save_checkpoint(ctx, "html_generated", {
            "html": html_content,
            "tokens": html_tokens,
        })

    # チェックリスト生成（別チェックポイント）
    checklist_checkpoint = await self._load_checkpoint(ctx, "checklist_generated")

    if checklist_checkpoint:
        checklist = checklist_checkpoint["checklist"]
        checklist_tokens = checklist_checkpoint["tokens"]
    else:
        checklist, checklist_tokens = await self._generate_checklist(
            llm, prompt_pack, keyword
        )

        await self._save_checkpoint(ctx, "checklist_generated", {
            "checklist": checklist,
            "tokens": checklist_tokens,
        })

    # 最終出力構築
    return self._build_final_output(
        keyword, final_content, html_content,
        checklist, html_tokens, checklist_tokens
    )
```

#### 3.2 HTML生成の分離

```python
async def _generate_html(
    self,
    llm,
    prompt_pack,
    keyword: str,
    content: str,
) -> tuple[str, int]:
    """HTML生成（リトライ付き）"""
    MAX_HTML_RETRIES = 1

    for attempt in range(MAX_HTML_RETRIES + 1):
        try:
            html_prompt = prompt_pack.get_prompt("step10_html")
            html_request = html_prompt.render(
                keyword=keyword,
                content=content,
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": html_request}],
                system_prompt="You are an HTML formatting expert.",
                config=LLMRequestConfig(max_tokens=8000, temperature=0.3),
            )

            # HTML品質検証
            validation = self._validate_html_comprehensive(response.content)
            if validation.is_valid:
                return response.content, response.token_usage.output

            if attempt < MAX_HTML_RETRIES:
                activity.logger.warning(
                    f"HTML quality insufficient, retrying: {validation.issues}"
                )

        except Exception as e:
            if attempt >= MAX_HTML_RETRIES:
                raise ActivityError(
                    f"HTML generation failed: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e
            activity.logger.warning(f"HTML generation error, retrying: {e}")

    # 最後の試行結果を返す（警告付き）
    activity.logger.warning("HTML validation issues remain, proceeding with warnings")
    return response.content, response.token_usage.output
```

---

## 最終ステップとしての役割

### ワークフロー完了の責務

```
[Step9: Final Rewrite]
    ↓ final_content (Markdown)
[Step10: Final Output] ← このステップ
    ↓
    ├── Markdown記事
    ├── HTML記事
    ├── 出版チェックリスト
    └── 品質レポート
```

### 品質ゲートとしての機能

Step10 は最終ゲートとして以下を保証すべき：

1. **コンテンツ完全性**: 必要な要素がすべて揃っている
2. **HTML有効性**: 構造的に正しいHTML
3. **SEO対応**: 必要なメタタグの存在
4. **アクセシビリティ**: 基本的なa11y要件
5. **出版準備**: チェックリストの完了状態

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **最高** | チェックリスト失敗の修正 | 1h | フォールバック禁止違反 |
| **高** | 入力品質チェック | 1h | ガベージイン防止 |
| **高** | HTML検証強化 | 2h | 出力品質保証 |
| **中** | 出版準備状態評価 | 1h | 品質ゲート機能 |
| **中** | 記事統計計算 | 1h | メトリクス可視化 |
| **低** | HTML/チェックリストのチェックポイント | 2h | 効率化 |

---

## テスト観点

1. **正常系**: HTML + チェックリストが正しく生成される
2. **入力チェック**: step9 データ欠落でエラー
3. **HTML検証**: 必須タグ欠落で警告
4. **チェックリスト失敗**: 失敗時は空文字列（ダミー文字列ではない）
5. **出版準備状態**: blocking_issues がある場合 is_ready=false
6. **統計計算**: 日本語文字数が正しく計算される
7. **冪等性**: 同一入力で同一HTML/チェックリスト

---

## 緊急修正項目

### チェックリスト生成のフォールバック修正

**現状** (Line 125-127):
```python
except Exception:
    # Checklist is nice-to-have, continue if fails
    checklist = "Publication checklist generation failed."
```

**問題**: ダミー文字列での置換はフォールバック禁止ルールに抵触する可能性

**修正案**:
```python
except Exception as e:
    activity.logger.error(f"Checklist generation failed: {e}")
    # 失敗時は空文字列を設定し、出力で明示
    checklist = ""
    # is_checklist_generated フラグで区別
```

または、チェックリストを必須化：
```python
except Exception as e:
    raise ActivityError(
        f"Checklist generation failed: {e}",
        category=ErrorCategory.RETRYABLE,
    ) from e
```
