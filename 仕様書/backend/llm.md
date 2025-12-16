# LLM 仕様

## プロバイダー

| プロバイダー | 用途 |
|--------------|------|
| Gemini | 分析、検索、自然な表現 |
| Claude | 構造化、統合、品質制御 |
| OpenAI | 予備/比較用 |

## 工程別デフォルト

| 工程 | プロバイダー | 選定理由 |
|------|-------------|----------|
| 0 | Gemini | キーワード分析精度 |
| 1 | - | GAS/Tool実行 |
| 2 | Gemini | CSV処理の安定性 |
| 3A/3B/3C | Gemini | 並列分析 |
| 4 | Claude | 構造化出力の品質 |
| 5 | Gemini+Web | Web検索連携 |
| 6 | Claude | 統合・再構成の品質 |
| 6.5 | Claude | 構成案の品質 |
| 7A | Claude | 長文生成の品質 |
| 7B | Gemini | ブラッシュアップ |
| 8 | Gemini+Web | ファクトチェック |
| 9 | Claude | 最終リライト品質 |
| 10 | Claude | 最終出力品質 |

## インターフェース

```python
class LLMInterface(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_json(
        self,
        messages: list[dict],
        system_prompt: str,
        schema: dict,
    ) -> dict:
        """JSON出力を保証"""
        pass
```

## レスポンス

```python
class LLMResponse(BaseModel):
    content: str
    token_usage: dict  # {"input": int, "output": int}
    model: str
```

## フォールバック禁止

```
❌ 禁止：別モデル/別プロバイダへの自動切替
✅ 許容：同一条件でのリトライ（上限3回、ログ必須）
```

## APIキー管理

- 暗号化して保存
- 復号は最小権限で実行
- 平文保存・平文ログは禁止
