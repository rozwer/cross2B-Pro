# 出典リンク0件問題の修正

## 問題

生成された記事に出典リンク（参考文献URL）が含まれていなかった。
手動作成の参照記事では11件の出典リンクがあるのに対し、自動生成記事は0件だった。

## 原因

step7a（記事本文生成）がstep5（一次資料収集）のデータを読み込んでいなかった。

プロンプトには「参考文献URLを必ず記載」という指示があるが、実際に使用可能なURLデータ（primary_sources）がプロンプトに渡されていなかったため、LLMは出典を埋め込めなかった。

## 修正内容

### 1. apps/worker/activities/step7a.py

#### step5データの読み込みを追加

```python
# Load step data from storage
step6_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step6_5") or {}
step3_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3_5") or {}
step5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step5") or {}  # 追加
enable_step3_5 = config.get("enable_step3_5", True)

# Extract and format primary sources for citation embedding
primary_sources = self._format_primary_sources(step5_data.get("sources", []))  # 追加
```

#### _format_primary_sources メソッドを追加

```python
def _format_primary_sources(self, sources: list[dict[str, Any]]) -> str:
    """Format primary sources for citation embedding in article."""
    if not sources:
        return ""

    formatted_sources: list[str] = []
    for i, src in enumerate(sources[:15], start=1):  # 15件まで
        url = src.get("url", "")
        title = src.get("title", "")
        source_type = src.get("source_type", "other")
        excerpt = src.get("excerpt", "")[:200]
        phase = src.get("phase_alignment", "")

        source_entry = f"[{i}] {title}"
        if source_type != "other":
            source_entry += f" ({source_type})"
        source_entry += f"\n    URL: {url}"
        if excerpt:
            source_entry += f"\n    要約: {excerpt}"
        if phase:
            source_entry += f"\n    フェーズ: {phase}"

        # データポイントがあれば追加
        data_points = src.get("data_points", [])
        if data_points:
            dp_strs = []
            for dp in data_points[:3]:
                metric = dp.get("metric", "")
                value = dp.get("value", "")
                if metric and value:
                    dp_strs.append(f"{metric}: {value}")
            if dp_strs:
                source_entry += f"\n    データ: {', '.join(dp_strs)}"

        formatted_sources.append(source_entry)

    return "## 引用可能な一次資料\n以下の出典を記事内で脚注形式で引用してください。\n\n" + "\n\n".join(formatted_sources)
```

#### _generate_draft メソッドの引数に追加

```python
async def _generate_draft(
    self,
    config: dict[str, Any],
    keyword: str,
    integration_package: str,
    prompt_pack: Any,
    human_touch_elements: str,
    primary_sources: str = "",  # 追加
) -> str:
```

### 2. apps/api/prompts/packs/default.json

#### step7a変数にprimary_sourcesを追加

```json
"variables": {
  "keyword": { "required": true, "type": "string" },
  "integration_package": { "required": true, "type": "string" },
  "human_touch_elements": { "required": false, "type": "string", "default": "" },
  "primary_sources": { "required": false, "type": "string", "default": "" }  // 追加
}
```

#### step7aプロンプトに入力セクションを追加

```
## 人間味要素（工程7Bで追加）
{{human_touch_elements}}

## 引用可能な一次資料（工程5で収集）  // 追加
{{primary_sources}}                      // 追加

---

# タスク
```

#### バージョンを更新

```json
"step7a": {
  "step": "step7a",
  "version": 5,  // 4 → 5
  ...
}
```

## 関連コミット

- `6df9dc3 feat(worker): add primary source citation support to step7a`

## 確認方法

1. 新しいrunを作成して記事を生成
2. 生成された記事に出典リンク（脚注形式）が含まれていることを確認
3. 記事末尾の「参考文献・出典一覧」セクションにURLが記載されていることを確認

## 備考

step5で収集した一次資料（URL、タイトル、ソースタイプ、要約、データポイント）がstep7aのプロンプトに渡されるようになり、LLMが脚注形式で出典を埋め込めるようになった。
