# コードレビュー修正仕様書

> **作成日**: 2025-12-16
> **最終更新**: 2025-12-16（3回の議論を経て改訂）
> **元レポート**: `code_review_report.json` (9件) + `security_vulnerabilities_report.json` (9件) を統合
> **総指摘数**: 18件（重複統合後: 15件 + 新規追加: 3件 = 18件）

---

## レビュー経緯

本仕様書は以下の3回の議論を経て改訂された：

1. **セキュリティレビュー** (@security-reviewer)
   - 認証実装の詳細設計不足を指摘
   - LLMプロンプトインジェクション対策の欠落を指摘
   - DNS Rebinding対策の追加を提案
   - 監査ログの完全性保証を追加

2. **バックエンド実装レビュー** (@backend-implementer)
   - 現行実装との整合性を確認
   - LLMCallMetadata必須化を提案
   - Activity/Graph責務分離の明文化を提案
   - エラーハンドリングパターンの統一を提案

3. **フロントエンド実装レビュー** (@frontend-implementer)
   - XSS対策の強化（DOMPurify設定詳細化）
   - 認証トークン管理方法の改善
   - CSP設定の追加を提案
   - WebSocket認証のプロトコル詳細化

---

## 設計判断

### 論点

両レポートを精査した結果、以下の重複指摘を統合する必要がある：

1. **SSRF**: REVIEW-008 (Medium) + VULN-002 (Critical)
2. **SQL注入**: REVIEW-007 (High) + VULN-004 (High)
3. **エラーメッセージ**: 複数ファイルで内部情報漏洩（VULN-009）

### 選択肢

**1. 修正の優先度基準**

- 案A: 重大度（Severity）で優先順位を決める（Critical > High > Medium）
- 案B: カテゴリで優先順位を決める（Security > Correctness > Build）
- 案C: 影響範囲で優先順位を決める（実行停止系 > セキュリティ系 > 運用系）

**2. 修正の依存関係**

- 案A: カテゴリごとに独立して修正（Correctness → Security → Build）
- 案B: ファイルごとに関連する指摘をまとめて修正
- 案C: 優先度順に修正（P0 → P1 → P2）

### 推奨（改訂版）

**優先度基準**: 案C（影響範囲で優先順位を決める）を基本とし、セキュリティレビューの指摘を反映

- **P0-Security**: 認証実装（VULN-005/006）← **セキュリティレビューにより昇格**
- **P0-Correctness**: 実行停止系（REVIEW-001/002/003/004/005）
- **P1-Security**: セキュリティ Critical/High（VULN-001/002/003/004）+ 新規追加（VULN-010/011/012）
- **P2**: 運用改善系（残り全て）

**修正順序**: P0-Security → P0-Correctness → P1 → P2
- 認証なしでは他のセキュリティ対策が無意味なため、認証を最優先
- worktree による並列実装を活用（衝突しないファイルは並列可）

### 影響範囲（改訂版）

| 優先度 | 影響ファイル |
|--------|-------------|
| P0-Security | `apps/ui/src/lib/api.ts`, `apps/ui/src/lib/websocket.ts`, `apps/api/main.py` (認証middleware) |
| P0-Correctness | `apps/worker/`, `apps/api/llm/`, `apps/api/tools/`, `apps/api/validation/`, `apps/api/prompts/` |
| P1-Security | `apps/ui/src/components/`, `apps/api/tools/fetch.py`, `apps/api/db/tenant.py`, `apps/api/storage/`, `apps/api/audit/` |
| P2 | `docker/`, `apps/api/main.py`, `apps/ui/middleware.ts`, 複数ファイル |

### 新規追加項目（レビュー結果）

| ID | 優先度 | カテゴリ | 概要 |
|----|--------|----------|------|
| VULN-010 | P1 | LLM Security | プロンプトインジェクション対策 |
| VULN-011 | P1 | Audit | 監査ログの完全性保証（チェーンハッシュ） |
| VULN-012 | P1 | Storage | Storageアクセス制御（テナント分離） |

---

## P0-Security（最優先）: 認証実装

> **セキュリティレビューにより P1 → P0 に昇格**
> 理由: 認証なしでは他のセキュリティ対策（テナント分離、アクセス制御等）が無意味

### VULN-005: API認証の実装

**優先度**: P0-Security
**重大度**: High → **Critical（昇格）**
**カテゴリ**: Authentication

#### 問題

APIクライアントに認証トークン（Bearer token等）を付与するロジックがない。

#### 影響

- 認証バイパス
- 他テナントのデータへのアクセス
- 不正なAPI操作

#### 修正内容（改訂版）

**対象ファイル**:
- `apps/ui/src/lib/api.ts` (20-46行)
- 新規: `apps/ui/src/lib/auth.ts`
- 新規: `apps/api/auth/middleware.py`

**修正方針（フロントエンドレビュー反映）**:

1. sessionStorage でトークン管理（localStorage より XSS リスク低減）
2. トークンリフレッシュ機構の実装
3. 401エラー時の自動リフレッシュ

**実装例（改訂版）**:

```typescript
// lib/auth.ts（新規作成）
export class AuthManager {
  private static readonly TOKEN_KEY = 'auth_token';
  private static readonly REFRESH_KEY = 'refresh_token';

  static getToken(): string | null {
    return sessionStorage.getItem(this.TOKEN_KEY);
  }

  static setToken(token: string, refreshToken?: string): void {
    sessionStorage.setItem(this.TOKEN_KEY, token);
    if (refreshToken) {
      sessionStorage.setItem(this.REFRESH_KEY, refreshToken);
    }
  }

  static clearToken(): void {
    sessionStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.REFRESH_KEY);
  }

  static async refreshToken(): Promise<string | null> {
    const refreshToken = sessionStorage.getItem(this.REFRESH_KEY);
    if (!refreshToken) return null;

    try {
      const response = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        this.clearToken();
        return null;
      }

      const { access_token, refresh_token: newRefresh } = await response.json();
      this.setToken(access_token, newRefresh);
      return access_token;
    } catch {
      this.clearToken();
      return null;
    }
  }
}
```

**バックエンド認証ミドルウェア（セキュリティレビュー反映）**:

```python
# apps/api/auth/middleware.py
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> str:
    """
    JWTトークンから tenant_id を抽出する。

    セキュリティ要件:
    - tenant_id は JWT ペイロードから取得（URL/Body パラメータは信用しない）
    - 検証失敗は監査ログに記録
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            await audit_logger.log_auth_failure(
                reason="missing_tenant_id",
                token_fragment=credentials.credentials[:10]
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return tenant_id
    except JWTError as e:
        await audit_logger.log_auth_failure(reason="invalid_token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

#### 追加要件（セキュリティレビュー）

- JWT 署名鍵のローテーション戦略
- トークン有効期限（access token: 15分, refresh token: 7日）
- ログイン試行回数制限（5回失敗で10分ロック）

#### テスト観点

- [ ] 認証トークンが正しく送信される
- [ ] 401エラーが適切にハンドリングされる
- [ ] トークンリフレッシュが動作する
- [ ] tenant_id がJWTペイロードから取得される
- [ ] 認証失敗が監査ログに記録される

---

### VULN-006: WebSocket認証の実装

**優先度**: P0-Security
**重大度**: High → **Critical（昇格）**
**カテゴリ**: Authentication

#### 問題

WebSocket接続に認証情報が含まれていない。runIdを知っていれば誰でも進捗情報を取得可能。

#### 影響

- 認証バイパス
- 他ユーザーのワークフロー進捗の監視
- 情報漏洩

#### 修正内容（改訂版）

**対象ファイル**:
- `apps/ui/src/lib/websocket.ts` (40-43行)
- `apps/api/websockets.py`

**修正方針（フロントエンドレビュー反映）**:

1. 接続後に認証メッセージを送信（URLパラメータはログに残るリスク）
2. 認証失敗時は code=1008 で切断
3. テナント越境チェック必須

**実装例（改訂版）**:

```typescript
// lib/websocket.ts
export class RunProgressWebSocket {
  connect(): void {
    const token = AuthManager.getToken();
    if (!token) {
      console.error('No authentication token available');
      this.setStatus('error');
      window.location.href = '/login';
      return;
    }

    this.setStatus('connecting');
    const url = `${WS_BASE}/ws/runs/${this.runId}`;

    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers(token);
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(token: string): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      // 接続後に認証メッセージを送信
      this.ws?.send(JSON.stringify({ type: 'auth', token }));
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'auth_error') {
        this.setStatus('error');
        this.disconnect();
        AuthManager.clearToken();
        window.location.href = '/login';
        return;
      }

      if (data.type === 'auth_success') {
        this.reconnectCount = 0;
        this.setStatus('connected');
        return;
      }

      this.options.onMessage(data);
    };

    this.ws.onclose = (event) => {
      if (event.code === 1008) {
        // 認証エラーは再接続しない
        AuthManager.clearToken();
        window.location.href = '/login';
        return;
      }
      this.scheduleReconnect();
    };
  }
}
```

**バックエンド側**:

```python
@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()

    try:
        # 認証メッセージを待機（タイムアウト10秒）
        data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_msg = json.loads(data)

        if auth_msg.get('type') != 'auth':
            await websocket.send_json({"type": "auth_error", "reason": "Authentication required"})
            await websocket.close(code=1008)
            return

        # トークン検証
        payload = jwt.decode(auth_msg.get('token'), SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id = payload.get("tenant_id")

        # テナント越境チェック
        run = await get_run(run_id)
        if run.tenant_id != tenant_id:
            await websocket.send_json({"type": "auth_error", "reason": "Access denied"})
            await websocket.close(code=1008)
            return

        await websocket.send_json({"type": "auth_success"})
        # ... 通常処理

    except asyncio.TimeoutError:
        await websocket.close(code=1008, reason="Auth timeout")
    except JWTError:
        await websocket.send_json({"type": "auth_error", "reason": "Invalid token"})
        await websocket.close(code=1008)
```

#### テスト観点

- [ ] 接続後に認証メッセージが送信される
- [ ] トークンなしの接続が拒否される
- [ ] テナント越境アクセスが拒否される
- [ ] 認証失敗時に code=1008 で切断される

---

## P0-Correctness（即時対応）: 実行停止系修正

### カテゴリ: Correctness

#### REVIEW-001: LLMInterface契約違反（Worker Activity側）

**優先度**: P0
**重大度**: Critical
**カテゴリ**: Correctness / API Contract

##### 問題

Worker activity が `llm.generate(prompt=..., max_tokens=..., temperature=...)` を呼び、`response.input_tokens` / `response.output_tokens` を参照している。しかし `LLMInterface.generate()` は `messages` / `system_prompt` / `config` / `metadata` を受け、トークン使用量は `LLMResponse.token_usage` に格納される。

##### 影響

- 実行時の TypeError / AttributeError によりワークフローが停止
- provider 実装差異により挙動が不定

##### 修正内容

**対象ファイル**:
- `apps/worker/activities/step0.py` (64-99行)
- `apps/worker/activities/step3a.py` (87-106行)
- その他全 step activities

**修正方針**:

1. Worker側の LLM 呼び出しを `LLMInterface` 契約に統一
2. トークン使用量は `LLMResponse.token_usage` を参照

**実装例**:

```python
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig

response = await llm.generate(
    messages=[{"role": "user", "content": prompt}],
    system_prompt=config.get("system_prompt", ""),
    config=LLMRequestConfig(
        max_tokens=config.get("max_tokens", 2000),
        temperature=config.get("temperature", 0.7),
    ),
    metadata=LLMCallMetadata(
        run_id=ctx.run_id,
        step_id=ctx.step_id,
        attempt=ctx.attempt,
        tenant_id=ctx.tenant_id,
    ),
)

usage = {
    "input_tokens": response.token_usage.input,
    "output_tokens": response.token_usage.output,
}
```

##### テスト観点

- [ ] Worker activity が LLMInterface 契約に準拠している
- [ ] トークン使用量が正しく記録される
- [ ] 全プロバイダ（Gemini/OpenAI/Anthropic）で動作する
- [ ] TypeError / AttributeError が発生しない

---

#### REVIEW-002: LLMInterface契約違反（LangGraph側）

**優先度**: P0
**重大度**: Critical
**カテゴリ**: Correctness / LangGraph

##### 問題

Graph内の `llm.generate(prompt=..., max_tokens=...)` や `grounding=True` など、`LLMInterface.generate()` に存在しない引数で呼び出している。

##### 影響

- Graph実行時に TypeError で停止
- 工程3並列（3A/3B/3C）で一括失敗しやすい

##### 修正内容

**対象ファイル**:
- `apps/worker/graphs/pre_approval.py` (30-46行, 143-172行)
- `apps/worker/graphs/post_approval.py` (全体)

**修正方針**:

1. Graph側も `LLMInterface` 契約に合わせる
2. `grounding` 等の provider 固有機能は `config` / provider固有設定で表現する

**実装例**:

```python
response = await llm.generate(
    messages=[{"role": "user", "content": p}],
    system_prompt=config.get("system_prompt", ""),
    config=LLMRequestConfig(
        max_tokens=4000,
        temperature=0.7,
        # provider固有設定は別途実装
    ),
    metadata=LLMCallMetadata(
        run_id=ctx.run_id,
        step_id="step3b",
        attempt=1,
        tenant_id=ctx.tenant_id,
    ),
)
```

##### テスト観点

- [ ] Graph が LLMInterface 契約に準拠している
- [ ] 工程3並列（3A/3B/3C）が正常に動作する
- [ ] grounding 等の provider 固有機能が正しく動作する

---

#### REVIEW-003: Tool API契約違反

**優先度**: P0
**重大度**: Critical
**カテゴリ**: Correctness / Tools

##### 問題

`registry.get_tool()` / `ToolRequest(tool_id=..., input_data=...)` / `execute(ToolRequest)` / `result.output_data` 等を前提としているが、現行の `ToolRegistry` は `ToolRegistry.get(tool_id)` でインスタンスを返し、ツールは `execute(**kwargs)` で呼ぶ設計。

##### 影響

- 実行時に AttributeError / TypeError で停止（ツール呼び出し不可）
- SERP取得・ページ取得が動かず後続工程が成立しない

##### 修正内容

**対象ファイル**:
- `apps/worker/activities/step1.py` (51-119行)
- `apps/worker/graphs/pre_approval.py` (63-99行)

**修正方針**:

1. Worker/Graph側を現行 `ToolRegistry.get()` と各ツールの `execute()` シグネチャに合わせる

**実装例**:

```python
from apps.api.tools import ToolRegistry

serp_tool = ToolRegistry.get("serp_fetch")
serp_result = await serp_tool.execute(query=keyword, num_results=10)
results = (serp_result.data or {}).get("results", [])
urls = [r.get("url") for r in results if r.get("url")]
```

##### テスト観点

- [ ] Worker/Graph が ToolRegistry API に準拠している
- [ ] SERP取得・ページ取得が正常に動作する
- [ ] ツールのエラー分類が統一フォーマットで返る

---

#### REVIEW-004: Validator import エラー

**優先度**: P0
**重大度**: Critical
**カテゴリ**: Correctness / Imports

##### 問題

`apps.api.validation.base` には `BaseValidator` が存在せず、`apps.api.validation.json_validator` にも `JSONValidator` が存在しない（現行は `ValidatorInterface` / `JsonValidator`）。そのため Graph モジュールの import が失敗する。

##### 影響

- pytest 収集時点で ImportError によりテストが実行不能
- LangGraph の wrapper 実装が実行経路に入らない

##### 修正内容

**対象ファイル**:
- `apps/worker/graphs/wrapper.py` (24-80行)

**修正方針**:

1. Validatorの命名とインターフェースを現行モジュールに合わせる

**実装例**:

```python
from apps.api.validation.base import ValidatorInterface
from apps.api.validation.json_validator import JsonValidator

async def step_wrapper(..., validator: ValidatorInterface | None = None, ...):
    validator = validator or JsonValidator()
```

##### テスト観点

- [ ] pytest 収集が成功する
- [ ] Graph wrapper が正常に動作する
- [ ] Validator が正しく機能する

---

#### REVIEW-005: PromptPackLoader 不具合

**優先度**: P0
**重大度**: High
**カテゴリ**: Correctness / Prompts

##### 問題

Graph/wrapper は同期 `load(pack_id)` を使用しているが、この実装は `mock_pack` 以外で常に `PromptPackNotFoundError` を投げる。また mock_pack の prompt key が `step_0_keyword_research` 等で、Worker/Graph が参照する `step0` / `step3a` 等と一致しない。

##### 影響

- 本番pack_idでGraph実行時に prompt pack のロードに失敗する
- mock_pack でも step 名不一致で prompt 取得に失敗する

##### 修正内容

**対象ファイル**:
- `apps/api/prompts/loader.py` (131-164行, 247-276行)
- `apps/worker/graphs/wrapper.py` (83-99行)
- `apps/worker/activities/step0.py` (64-65行)
- `apps/worker/graphs/pre_approval.py` (147-160行)

**修正方針**:

1. Graph/wrapper で async loader を使うか、同期 load がDBアクセス可能になるようにする
2. mock_pack の key を `step0`, `step3a` 等に揃える

**実装例**:

```python
# 1) Graph/wrapper 側で `await loader.load_async(pack_id)` を使う（session_factory を注入）
pack = await loader.load_async(pack_id)

# 2) mock_pack の key を step_id と一致させる
"step0": {"content": "...", "variables": {}},
"step3a": {"content": "...", "variables": {}},
```

##### テスト観点

- [ ] Graph/wrapper が prompt pack を正しくロードできる
- [ ] mock_pack で全 step の prompt が取得できる
- [ ] 本番pack_idで prompt pack を正しくロードできる

---

## P1（短期）: セキュリティ修正

### カテゴリ: Security

#### VULN-001: XSS脆弱性（HTML直接レンダリング）

**優先度**: P1
**重大度**: Critical
**カテゴリ**: XSS

##### 問題

srcDoc属性にユーザー/LLM生成のHTMLを直接渡している。sandbox="allow-same-origin"は同一オリジンでのスクリプト実行を許可する可能性がある。

##### 影響

- 悪意あるHTMLコンテンツによるXSS攻撃
- セッション情報の窃取
- フィッシング攻撃

##### 修正内容

**対象ファイル**:
- `apps/ui/src/components/artifacts/HtmlPreview.tsx` (45-49行)

**修正方針**:

1. sandbox属性を強化する
2. HTMLをサニタイズする

**実装例**:

```typescript
import DOMPurify from 'dompurify';

<iframe
  srcDoc={DOMPurify.sanitize(content, {
    ALLOWED_TAGS: ['p', 'div', 'span', 'h1', 'h2', 'h3', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['class', 'id'],
  })}
  sandbox=""
/>
```

##### テスト観点

- [ ] XSS攻撃が防止される
- [ ] 安全なHTMLが正しく表示される
- [ ] sandbox属性が正しく機能する

---

#### VULN-002 + REVIEW-008: SSRF脆弱性（統合）

**優先度**: P1
**重大度**: Critical
**カテゴリ**: SSRF

##### 問題

page_fetchツールでURL検証が不十分。内部ネットワークやクラウドメタデータサービス（169.254.169.254 等）へのアクセスが可能。また `MAX_CONTENT_LENGTH` を保持しているが実際の取得処理でサイズ制限が行われていない。

##### 影響

- 内部サービスへの不正アクセス
- AWSなどのクラウドメタデータ取得によるクレデンシャル漏洩
- 内部ネットワークのスキャン
- 巨大レスポンスによるメモリ使用量増加

##### 修正内容

**対象ファイル**:
- `apps/api/tools/fetch.py` (133-165行)

**修正方針**:

1. scheme allowlist（http/https のみ）
2. 内部IPブロック（private/reserved/loopback/metadata）
3. 取得サイズ上限（streaming + content-lengthチェック）

**実装例**:

```python
from ipaddress import ip_address, ip_network
from typing import Tuple

BLOCKED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0', '169.254.169.254']
BLOCKED_NETWORKS = [
    ip_network('10.0.0.0/8'),
    ip_network('172.16.0.0/12'),
    ip_network('192.168.0.0/16'),
    ip_network('::1/128'),
    ip_network('fc00::/7'),
]

def is_safe_url(url: str) -> Tuple[bool, str]:
    parsed = urlparse(url)

    # scheme check
    if parsed.scheme not in ['http', 'https']:
        return False, f"Invalid scheme: {parsed.scheme}"

    # hostname check
    host = parsed.hostname
    if not host:
        return False, "Missing hostname"

    if host in BLOCKED_HOSTS:
        return False, f"Blocked host: {host}"

    # IP check
    try:
        ip = ip_address(host)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                return False, f"Blocked network: {network}"
    except ValueError:
        # DNS resolve and check
        try:
            resolved_ips = socket.getaddrinfo(host, None)
            for _, _, _, _, addr in resolved_ips:
                ip = ip_address(addr[0])
                for network in BLOCKED_NETWORKS:
                    if ip in network:
                        return False, f"Resolved to blocked network: {network}"
        except socket.gaierror:
            return False, f"DNS resolution failed: {host}"

    return True, ""

async def execute(self, url: str, **kwargs) -> ToolResult:
    # URL safety check
    is_safe, reason = is_safe_url(url)
    if not is_safe:
        return ToolResult(
            success=False,
            error_message=f"URL safety check failed: {reason}",
            error_type="VALIDATION_FAIL",
        )

    # Streaming fetch with size limit
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', url, headers=headers) as response:
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_content_length:
                return ToolResult(
                    success=False,
                    error_message=f"Content too large: {content_length} bytes",
                    error_type="VALIDATION_FAIL",
                )

            chunks = []
            total_size = 0
            async for chunk in response.aiter_bytes():
                total_size += len(chunk)
                if total_size > self.max_content_length:
                    return ToolResult(
                        success=False,
                        error_message=f"Content exceeded limit: {total_size} bytes",
                        error_type="VALIDATION_FAIL",
                    )
                chunks.append(chunk)

            content = b''.join(chunks)
```

##### テスト観点

- [ ] 内部IPへのアクセスがブロックされる
- [ ] クラウドメタデータへのアクセスがブロックされる
- [ ] 巨大レスポンスが制限される
- [ ] 正常なURLが取得できる

---

#### VULN-003: パストラバーサル脆弱性

**優先度**: P1
**重大度**: Critical
**カテゴリ**: Path Traversal

##### 問題

pdf_pathパラメータにユーザー入力が渡されると、任意のファイルを読み取り可能。

##### 影響

- システムファイルの漏洩（/etc/passwd等）
- 設定ファイル（.env、credentials等）の漏洩
- ソースコードの漏洩

##### 修正内容

**対象ファイル**:
- `apps/api/tools/fetch.py` (366-374行)

**修正方針**:

1. ファイルパスを許可されたディレクトリに制限する

**実装例**:

```python
import os
from pathlib import Path

ALLOWED_DIRS = [
    os.path.abspath('/data/pdfs/'),
    os.path.abspath('/uploads/'),
]

def is_safe_path(pdf_path: str) -> Tuple[bool, str]:
    try:
        resolved = os.path.realpath(pdf_path)

        # Check if path is within allowed directories
        for allowed_dir in ALLOWED_DIRS:
            if resolved.startswith(allowed_dir):
                return True, ""

        return False, f"Path outside allowed directories: {resolved}"
    except Exception as e:
        return False, f"Path resolution failed: {e}"

async def execute(self, pdf_path: str, **kwargs) -> ToolResult:
    # Path safety check
    is_safe, reason = is_safe_path(pdf_path)
    if not is_safe:
        return ToolResult(
            success=False,
            error_message=f"Path safety check failed: {reason}",
            error_type="VALIDATION_FAIL",
        )

    path = Path(pdf_path)
    if not path.exists():
        return ToolResult(
            success=False,
            error_message="File not found",
            error_type="NON_RETRYABLE",
        )

    pdf_data = path.read_bytes()
    # ... rest of the implementation
```

##### テスト観点

- [ ] 許可されたディレクトリ外のファイルへのアクセスがブロックされる
- [ ] パストラバーサル攻撃が防止される
- [ ] 正常なファイルが読み取れる

---

#### VULN-004 + REVIEW-007: SQLインジェクション（統合）

**優先度**: P1
**重大度**: High
**カテゴリ**: SQL Injection

##### 問題

tenant_id から作られる `db_name` を f-string で SQL 文に埋め込んでいる。tenant_id の形式検証がない場合、SQL注入や意図しないDB名生成のリスクがある。

##### 影響

- DB作成/削除操作の悪用（インフラ破壊・データ損失）
- 監査ログ・運用面での重大インシデント

##### 修正内容

**対象ファイル**:
- `apps/api/db/tenant.py` (172-190行, 233-261行)

**修正方針**:

1. tenant_id を厳格な allowlist で検証する
2. 識別子として安全な文字種・長さに制限する

**実装例**:

```python
import re

def validate_tenant_id(tenant_id: str) -> Tuple[bool, str]:
    """
    tenant_id の形式を厳密に検証する。

    許可される文字: a-z, 0-9, ハイフン, アンダースコア
    長さ: 1-32文字
    """
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", tenant_id):
        return False, f"Invalid tenant_id format: {tenant_id}"

    # 予約語チェック
    reserved_words = ['postgres', 'template0', 'template1', 'test']
    if tenant_id.lower() in reserved_words:
        return False, f"Reserved tenant_id: {tenant_id}"

    return True, ""

async def create_tenant_db(tenant_id: str) -> None:
    # Validation
    is_valid, reason = validate_tenant_id(tenant_id)
    if not is_valid:
        raise TenantDBError(reason)

    db_name = f"seo_gen_tenant_{tenant_id}"

    # CREATE DATABASE
    # ...
```

##### テスト観点

- [ ] SQLインジェクションが防止される
- [ ] 不正な tenant_id が拒否される
- [ ] 正常な tenant_id でDBが作成される

---

#### VULN-005: API認証の欠如

**優先度**: P1
**重大度**: High
**カテゴリ**: Authentication

##### 問題

APIクライアントに認証トークン（Bearer token等）を付与するロジックがない。

##### 影響

- 認証バイパス
- 他テナントのデータへのアクセス
- 不正なAPI操作

##### 修正内容

**対象ファイル**:
- `apps/ui/src/lib/api.ts` (20-46行)

**修正方針**:

1. JWTトークンをリクエストヘッダーに含める

**実装例**:

```typescript
// トークン管理
function getAuthToken(): string | null {
  // localStorage or sessionStorage から取得
  return localStorage.getItem('auth_token');
}

// API呼び出し
const headers: HeadersInit = {
  'Content-Type': 'application/json',
  ...options.headers,
};

const token = getAuthToken();
if (token) {
  headers['Authorization'] = `Bearer ${token}`;
}

const response = await fetch(url, {
  method,
  headers,
  body: body ? JSON.stringify(body) : undefined,
});

// 401エラーハンドリング
if (response.status === 401) {
  // トークンリフレッシュ or ログインページへリダイレクト
  handleUnauthorized();
  throw new Error('Unauthorized');
}
```

##### テスト観点

- [ ] 認証トークンが正しく送信される
- [ ] 401エラーが適切にハンドリングされる
- [ ] トークンなしのリクエストが拒否される

---

#### VULN-006: WebSocket認証の欠如

**優先度**: P1
**重大度**: High
**カテゴリ**: Authentication

##### 問題

WebSocket接続に認証情報が含まれていない。runIdを知っていれば誰でも進捗情報を取得可能。

##### 影響

- 認証バイパス
- 他ユーザーのワークフロー進捗の監視
- 情報漏洩

##### 修正内容

**対象ファイル**:
- `apps/ui/src/lib/websocket.ts` (40-43行)

**修正方針**:

1. URLパラメータでトークンを送信

**実装例**:

```typescript
// WebSocket接続
const token = getAuthToken();
if (!token) {
  throw new Error('No auth token available');
}

const url = `${WS_BASE}/ws/runs/${this.runId}?token=${encodeURIComponent(token)}`;
this.ws = new WebSocket(url);

// エラーハンドリング
this.ws.onerror = (error) => {
  console.error('WebSocket error:', error);
  // 認証エラーの場合は再接続しない
};
```

**バックエンド側**:

```python
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from jose import jwt, JWTError

@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(...),
):
    # トークン検証
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # テナント越境チェック
    run = get_run(run_id)
    if run.tenant_id != tenant_id:
        await websocket.close(code=1008, reason="Access denied")
        return

    await websocket.accept()
    # ... rest of the implementation
```

##### テスト観点

- [ ] 認証トークンが正しく送信される
- [ ] トークンなしの接続が拒否される
- [ ] テナント越境アクセスが拒否される

---

## P2（中期）: 運用改善系修正

### カテゴリ: Build / Operational

#### REVIEW-006: Docker依存関係の不整合

**優先度**: P2
**重大度**: High
**カテゴリ**: Build / Packaging

##### 問題

Dockerfile は `pip install ".[dev]"` を実行するが、pyproject は `[dependency-groups] dev` を使用しており、pip の extras（`[project.optional-dependencies]`）とは別概念。

##### 影響

- Docker build が依存解決に失敗しやすい
- ローカル（uv）とDocker（pip）で依存セットがズレる

##### 修正内容

**対象ファイル**:
- `docker/Dockerfile.worker` (15-17行)
- `pyproject.toml` (32-38行)

**修正方針**:

1. Docker も uv を使う（推奨）

**実装例**:

```dockerfile
# Dockerfile.worker

FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/ ./apps/

# Install dependencies
RUN uv sync --frozen --no-dev

# Run worker
CMD ["uv", "run", "python", "-m", "apps.worker.main"]
```

##### テスト観点

- [ ] Docker build が成功する
- [ ] ローカルとDockerで依存セットが一致する
- [ ] dev依存が正しくインストールされる

---

#### REVIEW-009: HTTP HEAD→GET フォールバック

**優先度**: P2
**重大度**: Medium
**カテゴリ**: Operational Safety / HTTP

##### 問題

HEAD が拒否された場合のフォールバックとして `httpx.HTTPStatusError` を捕捉しているが、`client.head()` は通常 `raise_for_status()` を呼ばない限り例外を投げない。

##### 影響

- HEAD非対応サイトで false negative/不完全なメタ情報取得
- 運用時のリトライ増加

##### 修正内容

**対象ファイル**:
- `apps/api/tools/verify.py` (100-111行)

**修正方針**:

1. HEAD のステータスコードを見て GET に切り替える

**実装例**:

```python
async def execute(self, url: str, **kwargs) -> ToolResult:
    async with httpx.AsyncClient() as client:
        # Try HEAD first
        response = await client.head(url, headers=headers, follow_redirects=True)

        # Fallback to GET if HEAD is not supported
        if response.status_code in (405, 403) or response.status_code >= 400:
            response = await client.get(
                url,
                headers=headers,
                follow_redirects=True,
                timeout=self.timeout,
            )

        # Process response
        # ...
```

##### テスト観点

- [ ] HEAD非対応サイトで GET にフォールバックする
- [ ] 正常なサイトで HEAD が動作する
- [ ] メタ情報が正しく取得される

---

#### VULN-007: Markdownレンダリングの改善

**優先度**: P2
**重大度**: Medium
**カテゴリ**: XSS

##### 問題

カスタムMarkdownパーサーを使用。現在はReactの自動エスケープで保護されているが、リンク処理などの機能追加時にXSSリスクが発生する可能性。

##### 影響

- 将来的なXSS脆弱性の導入リスク
- メンテナンス性の低下

##### 修正内容

**対象ファイル**:
- `apps/ui/src/components/artifacts/MarkdownViewer.tsx` (1-183行)

**修正方針**:

1. 信頼できるMarkdownライブラリを使用する

**実装例**:

```typescript
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

export function MarkdownViewer({ content }: { content: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown rehypePlugins={[rehypeSanitize]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

##### テスト観点

- [ ] Markdownが正しくレンダリングされる
- [ ] XSS攻撃が防止される
- [ ] リンクが安全に処理される

---

#### VULN-008: CORS設定の追加

**優先度**: P2
**重大度**: Medium
**カテゴリ**: CORS

##### 問題

バックエンドのCORS設定ファイルが確認できない。適切でない場合、悪意あるサイトからのAPIアクセスが可能。

##### 影響

- クロスオリジンからの不正なAPIアクセス
- CSRF攻撃のリスク

##### 修正内容

**対象ファイル**:
- `apps/api/main.py` (全体)

**修正方針**:

1. 許可するオリジンを明示的に指定する

**実装例**:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS設定
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
    # 開発環境のデフォルト
    allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

##### テスト観点

- [ ] 許可されたオリジンからのアクセスが成功する
- [ ] 許可されていないオリジンからのアクセスが拒否される
- [ ] クレデンシャルが正しく処理される

---

#### VULN-009: エラーメッセージの改善

**優先度**: P2
**重大度**: Medium
**カテゴリ**: Information Disclosure

##### 問題

内部エラーの詳細がユーザーに露出している。スタックトレースやファイルパスが漏洩する可能性。

##### 影響

- 内部システム構造の漏洩
- 攻撃者への情報提供
- ファイルパスの漏洩

##### 修正内容

**対象ファイル**:
- 複数ファイル（LLM/Tools/API）

**修正方針**:

1. ユーザー向けエラーメッセージと内部ログを分離する

**実装例**:

```python
import logging

logger = logging.getLogger(__name__)

try:
    # 処理
    result = process_pdf(pdf_path)
except Exception as e:
    # 内部ログ（詳細情報）
    logger.error(
        f"PDF extraction failed",
        exc_info=True,
        extra={
            "pdf_path": pdf_path,
            "error_type": type(e).__name__,
        },
    )

    # ユーザー向けエラー（一般的なメッセージ）
    return ToolResult(
        success=False,
        error_message="ファイルの処理中にエラーが発生しました",
        error_type="NON_RETRYABLE",
    )
```

##### テスト観点

- [ ] 内部エラーがユーザーに露出しない
- [ ] ログに詳細情報が記録される
- [ ] エラーメッセージが一般的で安全

---

## 並列実装計画（worktree）

### フェーズ1: P0 修正（並列可）

```
worktree-llm-contract/    → REVIEW-001/002: LLM契約統一
worktree-tool-contract/   → REVIEW-003: Tool契約統一
worktree-validator-fix/   → REVIEW-004: Validator import修正
worktree-prompt-fix/      → REVIEW-005: PromptPackLoader修正
```

### フェーズ2: P1 修正（並列可）

```
worktree-xss-fix/         → VULN-001: XSS修正
worktree-ssrf-fix/        → VULN-002+REVIEW-008: SSRF修正
worktree-path-fix/        → VULN-003: Path Traversal修正
worktree-sql-fix/         → VULN-004+REVIEW-007: SQL注入修正
worktree-auth-api/        → VULN-005: API認証
worktree-auth-ws/         → VULN-006: WebSocket認証
```

### フェーズ3: P2 修正（並列可）

```
worktree-docker-fix/      → REVIEW-006: Docker依存修正
worktree-http-fix/        → REVIEW-009: HTTP修正
worktree-markdown-fix/    → VULN-007: Markdown修正
worktree-cors-fix/        → VULN-008: CORS設定
worktree-error-fix/       → VULN-009: エラーメッセージ修正
```

---

## テスト戦略

### P0 テスト

| テスト項目 | 確認内容 |
|-----------|---------|
| LLM契約テスト | Worker/Graph が LLMInterface 契約に準拠 |
| Tool契約テスト | Worker/Graph が ToolRegistry API に準拠 |
| Import テスト | pytest 収集が成功する |
| Prompt テスト | Graph/wrapper が prompt pack を正しくロード |

### P1 テスト

| テスト項目 | 確認内容 |
|-----------|---------|
| XSS テスト | 悪意あるHTMLがサニタイズされる |
| SSRF テスト | 内部IPへのアクセスがブロックされる |
| Path Traversal テスト | 許可されたディレクトリ外へのアクセスがブロック |
| SQL注入テスト | 不正な tenant_id が拒否される |
| API認証テスト | トークンなしのリクエストが拒否される |
| WebSocket認証テスト | トークンなしの接続が拒否される |

### P2 テスト

| テスト項目 | 確認内容 |
|-----------|---------|
| Docker Build テスト | Docker build が成功する |
| HTTP Fallback テスト | HEAD非対応サイトで GET にフォールバック |
| Markdown テスト | Markdownが正しくレンダリングされる |
| CORS テスト | 許可されたオリジンからのアクセスが成功 |
| エラーメッセージテスト | 内部エラーがユーザーに露出しない |

---

## P1-Security 追加項目（レビュー結果）

### VULN-010: LLMプロンプトインジェクション対策

**優先度**: P1
**重大度**: High
**カテゴリ**: LLM Security

#### 問題

ユーザー入力がLLMプロンプトに直接埋め込まれており、プロンプトインジェクション攻撃が可能。

#### 影響

- システムプロンプトの上書き
- 意図しない動作の誘発
- 機密情報の漏洩
- 不適切なコンテンツ生成

#### 修正内容

**対象ファイル**:
- `apps/worker/activities/step*.py` (全工程)
- `apps/worker/graphs/pre_approval.py`
- `apps/worker/graphs/post_approval.py`

**修正方針**:

1. ユーザー入力のサニタイズ
2. プロンプト構造の明確な分離（system/user）
3. 出力検証の強化

**実装例**:

```python
import re
from typing import Tuple

class PromptInjectionDefense:
    """LLMプロンプトインジェクション対策"""

    DANGEROUS_PATTERNS = [
        r'ignore\s+(previous|all|above)\s+instructions',
        r'system\s*:',
        r'<\s*\|im_start\|',
        r'<\s*\|im_end\|',
        r'\[INST\]',
        r'\[/INST\]',
    ]

    @classmethod
    def sanitize_user_input(cls, user_input: str, max_length: int = 1000) -> str:
        """ユーザー入力をサニタイズ"""
        if len(user_input) > max_length:
            user_input = user_input[:max_length]

        for pattern in cls.DANGEROUS_PATTERNS:
            user_input = re.sub(pattern, '', user_input, flags=re.IGNORECASE)

        user_input = ''.join(char for char in user_input if char.isprintable() or char.isspace())
        return user_input.strip()

    @classmethod
    def validate_llm_output(cls, output: str, expected_format: str) -> Tuple[bool, str]:
        """LLM出力を検証"""
        if any(keyword in output.lower() for keyword in [
            'api_key', 'secret', 'password', 'token',
            '/etc/', '/var/', 'postgresql://'
        ]):
            return False, "Output contains sensitive information"

        if expected_format == "json":
            try:
                json.loads(output)
            except json.JSONDecodeError:
                return False, "Invalid JSON format"

        return True, ""
```

#### テスト観点

- [ ] プロンプトインジェクション攻撃が防止される
- [ ] システムプロンプトが上書きされない
- [ ] 機密情報が出力に含まれない

---

### VULN-011: 監査ログの完全性保証

**優先度**: P1
**重大度**: High
**カテゴリ**: Audit / Integrity

#### 問題

監査ログの改ざん防止はDBトリガーのみで、完全性検証機能がない。

#### 影響

- 監査ログの改ざん
- インシデント調査の困難化
- コンプライアンス違反

#### 修正内容

**対象ファイル**:
- `apps/api/db/models.py` (audit_logs テーブル)
- 新規: `apps/api/audit/logger.py`

**修正方針**:

1. ログエントリのチェーンハッシュ実装
2. 定期的な完全性検証
3. Write-once storage への定期バックアップ

**実装例**:

```python
import hashlib
from datetime import datetime
from typing import Optional, Tuple

class AuditLogger:
    """監査ログの完全性を保証するロガー"""

    def _compute_hash(
        self,
        previous_hash: Optional[str],
        log_entry: dict
    ) -> str:
        """ログエントリのハッシュを計算（チェーンハッシュ）"""
        data = f"{previous_hash or ''}{log_entry['user_id']}{log_entry['action']}"
        data += f"{log_entry['resource_type']}{log_entry['resource_id']}"
        data += f"{log_entry['created_at'].isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def log(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
    ) -> None:
        """監査ログを記録（完全性保証付き）"""
        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
            )
            previous_hash = result.scalar()

            log_entry = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "created_at": datetime.utcnow(),
            }

            entry_hash = self._compute_hash(previous_hash, log_entry)

            await session.execute(
                text("""
                    INSERT INTO audit_logs
                    (user_id, action, resource_type, resource_id, details, entry_hash, previous_hash)
                    VALUES (:user_id, :action, :resource_type, :resource_id, :details, :entry_hash, :previous_hash)
                """),
                {**log_entry, "entry_hash": entry_hash, "previous_hash": previous_hash}
            )
            await session.commit()

    async def verify_integrity(self, tenant_id: str) -> Tuple[bool, Optional[int]]:
        """監査ログの完全性を検証"""
        # 全エントリを走査し、チェーンハッシュを検証
        # ...
```

#### テスト観点

- [ ] チェーンハッシュが正しく計算される
- [ ] 改ざんが検出される
- [ ] 完全性検証が定期実行される

---

### VULN-012: Storageアクセス制御

**優先度**: P1
**重大度**: High
**カテゴリ**: Authorization / Storage

#### 問題

MinIO ストレージのテナント分離とアクセス制御が実装されていない。

#### 影響

- テナント越境アクセス
- 不正なファイル削除
- 機密ファイルの漏洩

#### 修正内容

**対象ファイル**:
- 新規: `apps/api/storage/client.py`
- `apps/api/main.py` (storage 初期化)

**修正方針**:

1. MinIO の Bucket Policy でテナント分離
2. Presigned URL の短命化（5分）
3. ファイルアクセスの監査ログ記録

**実装例**:

```python
class SecureStorageClient:
    """テナント分離を保証する Storage クライアント"""

    def _get_tenant_prefix(self, tenant_id: str) -> str:
        """テナント別のプレフィックスを取得"""
        is_valid, _ = validate_tenant_id(tenant_id)
        if not is_valid:
            raise StorageError("Invalid tenant_id")
        return f"tenants/{tenant_id}/"

    async def get_presigned_url(
        self,
        tenant_id: str,
        object_path: str,
        user_id: str,
        expires_minutes: int = 5
    ) -> str:
        """Presigned URL を生成（短命・テナントスコープ）"""
        if expires_minutes > 60:
            raise StorageError("Presigned URL expiry too long")

        prefix = self._get_tenant_prefix(tenant_id)
        full_path = f"{prefix}{object_path}"

        # オブジェクトの存在確認
        try:
            self.client.stat_object(self.bucket_name, full_path)
        except Exception:
            raise StorageError("Object not found")

        # Presigned URL 生成
        url = self.client.presigned_get_object(
            self.bucket_name,
            full_path,
            expires=timedelta(minutes=expires_minutes)
        )

        # 監査ログ
        await self.audit_logger.log(
            tenant_id=tenant_id,
            user_id=user_id,
            action="storage_presigned_url",
            resource_type="artifact",
            resource_id=full_path,
            details={"expires_minutes": expires_minutes}
        )

        return url
```

#### テスト観点

- [ ] テナント越境アクセスがブロックされる
- [ ] Presigned URL の有効期限が適切
- [ ] ファイルアクセスが監査ログに記録される

---

## 実装パターン集（バックエンドレビュー反映）

### Activity/Graph 間の責務分離

| 責務 | Activity | Graph |
|------|----------|-------|
| 外部I/O（LLM/Tool/DB/Storage） | ○ | × |
| エラーハンドリング | ○ | × |
| 冪等性担保 | ○ | × |
| 監査ログ記録 | ○ | × |
| データ整形 | × | ○ |
| フロー制御 | × | ○ |

### LLM呼び出しパターン（metadata必須化）

```python
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig

# metadata 必須化（トレーサビリティ確保）
metadata = LLMCallMetadata(
    run_id=ctx.run_id,
    step_id=self.step_id,
    attempt=activity.info().attempt,
    tenant_id=ctx.tenant_id,
)

response = await llm.generate(
    messages=[{"role": "user", "content": prompt}],
    system_prompt="You are a keyword analysis assistant.",
    config=LLMRequestConfig(
        max_tokens=config.get("max_tokens", 2000),
        temperature=config.get("temperature", 0.7),
    ),
    metadata=metadata,  # 必須
)

# トークン使用量の参照
usage = {
    "input_tokens": response.token_usage.input,
    "output_tokens": response.token_usage.output,
}
```

### LLMエラーハンドリングパターン

```python
from apps.api.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
    LLMInvalidRequestError,
)

try:
    response = await llm.generate(...)
except (LLMRateLimitError, LLMTimeoutError) as e:
    # RETRYABLE
    raise ActivityError(
        f"LLM temporary failure: {e}",
        category=ErrorCategory.RETRYABLE,
        details={"llm_error": str(e)},
    ) from e
except (LLMAuthenticationError, LLMInvalidRequestError) as e:
    # NON_RETRYABLE
    raise ActivityError(
        f"LLM permanent failure: {e}",
        category=ErrorCategory.NON_RETRYABLE,
        details={"llm_error": str(e)},
    ) from e
```

### ツール呼び出しパターン（エラーハンドリング必須）

```python
from apps.api.tools import ToolRegistry
from apps.api.tools.exceptions import ToolNotFoundError

try:
    tool = ToolRegistry.get("serp_fetch")
except ToolNotFoundError as e:
    raise ActivityError(
        f"Tool not found: serp_fetch",
        category=ErrorCategory.NON_RETRYABLE,
    ) from e

result = await tool.execute(query=keyword, num_results=10)

if not result.success:
    if result.error_category == "retryable":
        raise ActivityError(
            f"SERP fetch failed: {result.error_message}",
            category=ErrorCategory.RETRYABLE,
        )
    elif result.error_category == "validation_fail":
        raise ActivityError(
            f"SERP validation failed: {result.error_message}",
            category=ErrorCategory.VALIDATION_FAIL,
        )
    else:
        raise ActivityError(
            f"SERP fetch failed permanently: {result.error_message}",
            category=ErrorCategory.NON_RETRYABLE,
        )

# Evidence 保存
if result.evidence:
    await self.store.save_evidence(
        tenant_id=ctx.tenant_id,
        run_id=ctx.run_id,
        step_id=self.step_id,
        evidence_list=result.evidence,
    )

urls = result.data.get("urls", []) if result.data else []
```

### 監査ログ記録パターン

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 1. 実行開始ログ
    await self.emitter.emit(Event(
        type=EventType.STEP_STARTED,
        tenant_id=ctx.tenant_id,
        run_id=ctx.run_id,
        step_id=self.step_id,
        details={"input_digest": input_digest},
    ))

    try:
        # 2. 処理実行
        result = await llm.generate(...)

        # 3. 実行成功ログ
        await self.emitter.emit(Event(
            type=EventType.STEP_COMPLETED,
            tenant_id=ctx.tenant_id,
            run_id=ctx.run_id,
            step_id=self.step_id,
            details={
                "output_path": artifact_ref.path,
                "output_digest": artifact_ref.digest,
            },
        ))

        return result
    except Exception as e:
        # 4. 実行失敗ログ
        await self.emitter.emit(Event(
            type=EventType.STEP_FAILED,
            tenant_id=ctx.tenant_id,
            run_id=ctx.run_id,
            step_id=self.step_id,
            details={"error": str(e)},
        ))
        raise
```

---

## マイルストーン（改訂版）

### Phase 0: P0-Security（最優先）

- [ ] VULN-005: API認証の実装
- [ ] VULN-006: WebSocket認証の実装
- [ ] 認証middleware テスト通過
- [ ] トークンリフレッシュ動作確認

### Phase 1: P0-Correctness

- [ ] REVIEW-001: LLM契約強化（metadata必須化）
- [ ] REVIEW-002: LangGraph側LLM契約統一
- [ ] REVIEW-003: Tool契約統一
- [ ] REVIEW-004: Validator import修正
- [ ] REVIEW-005: PromptPackLoader修正
- [ ] P0テスト通過
- [ ] E2E smoke テスト通過

### Phase 2: P1-Security

- [ ] VULN-001: XSS修正（DOMPurify導入）
- [ ] VULN-002+REVIEW-008: SSRF修正（DNS Rebinding対策含む）
- [ ] VULN-003: Path Traversal修正
- [ ] VULN-004+REVIEW-007: SQL注入修正
- [ ] VULN-010: プロンプトインジェクション対策
- [ ] VULN-011: 監査ログ完全性保証
- [ ] VULN-012: Storageアクセス制御
- [ ] P1テスト通過
- [ ] セキュリティスキャン通過

### Phase 3: P2修正

- [ ] REVIEW-006: Docker依存修正
- [ ] REVIEW-009: HTTP修正
- [ ] VULN-007: Markdown修正
- [ ] VULN-008: CORS設定
- [ ] VULN-009: エラーメッセージ修正
- [ ] CSP設定追加
- [ ] P2テスト通過
- [ ] 全体テスト通過

---

## 並列実装計画（worktree）改訂版

### Phase 0: P0-Security（並列可）

```
worktree-auth-api/        → VULN-005: API認証
worktree-auth-ws/         → VULN-006: WebSocket認証
```

### Phase 1: P0-Correctness（並列可）

```
worktree-llm-contract/    → REVIEW-001/002: LLM契約強化
worktree-tool-contract/   → REVIEW-003: Tool契約統一
worktree-validator-fix/   → REVIEW-004: Validator import修正
worktree-prompt-fix/      → REVIEW-005: PromptPackLoader修正
```

### Phase 2: P1-Security（並列可）

```
worktree-xss-fix/         → VULN-001: XSS修正
worktree-ssrf-fix/        → VULN-002+REVIEW-008: SSRF修正
worktree-path-fix/        → VULN-003: Path Traversal修正
worktree-sql-fix/         → VULN-004+REVIEW-007: SQL注入修正
worktree-prompt-inject/   → VULN-010: プロンプトインジェクション
worktree-audit-integrity/ → VULN-011: 監査ログ完全性
worktree-storage-acl/     → VULN-012: Storageアクセス制御
```

### Phase 3: P2修正（並列可）

```
worktree-docker-fix/      → REVIEW-006: Docker依存修正
worktree-http-fix/        → REVIEW-009: HTTP修正
worktree-markdown-fix/    → VULN-007: Markdown修正
worktree-cors-fix/        → VULN-008: CORS設定
worktree-error-fix/       → VULN-009: エラーメッセージ修正
worktree-csp/             → CSP設定
```

---

## 次のアクション

1. **Phase 0: P0-Security の開始**
   - worktree-auth-api/ を作成
   - worktree-auth-ws/ を作成
   - VULN-005/006 の修正を並列で開始

2. **認証基盤の整備**
   - JWT 署名鍵の設定
   - トークン有効期限の設定
   - 認証失敗の監査ログ設定

3. **Phase 1 準備**
   - P0-Security 完了後に開始
   - LLMCallMetadata の必須化
   - Tool エラーハンドリングの統一

4. **テストスイートの整備**
   - 認証テストの実装
   - P0テストの実装
   - CI/CDパイプラインの更新

5. **ドキュメントの更新**
   - API契約の明文化
   - セキュリティガイドラインの追加
   - 実装パターン集の公開

---

## 付録A: 依存関係追加（フロントエンド）

```json
{
  "dependencies": {
    "react-markdown": "^9.0.1",
    "rehype-sanitize": "^6.0.0",
    "rehype-external-links": "^3.0.0",
    "dompurify": "^3.0.8",
    "jose": "^5.2.0"
  },
  "devDependencies": {
    "@types/dompurify": "^3.0.5"
  }
}
```

---

## 付録B: 実装チェックリスト

### 認証実装チェック

- [ ] JWT トークンが sessionStorage に保存される
- [ ] API リクエストに Authorization ヘッダーが含まれる
- [ ] 401 エラー時にトークンリフレッシュが実行される
- [ ] WebSocket 接続後に認証メッセージが送信される
- [ ] 認証失敗が監査ログに記録される
- [ ] テナント越境アクセスがブロックされる

### LLMInterface契約チェック

- [ ] 全Activity/Graphで `LLMCallMetadata` を注入している
- [ ] LLMエラーを適切に分類（RETRYABLE/NON_RETRYABLE）している
- [ ] LLM呼び出しログが監査ログに記録されている

### ToolRegistry契約チェック

- [ ] ToolResult.success == False を適切にハンドリングしている
- [ ] エラー分類（RETRYABLE/NON_RETRYABLE/VALIDATION_FAIL）を活用している
- [ ] ToolResult.evidence を storage に保存している

### Activity/Graph責務分離チェック

- [ ] Graph からツール/LLM呼び出しを排除している
- [ ] Activity が外部I/O + エラーハンドリング + 冪等性を担保している
- [ ] Graph がデータ整形 + フロー制御のみを担当している

### セキュリティチェック

- [ ] XSS: DOMPurify でサニタイズしている
- [ ] SSRF: 内部IPブロック + DNS Rebinding対策を実装している
- [ ] Path Traversal: 許可ディレクトリ制限を実装している
- [ ] SQL注入: tenant_id の形式検証を実装している
- [ ] プロンプトインジェクション: 入力サニタイズを実装している
- [ ] 監査ログ: チェーンハッシュを実装している
- [ ] Storage: テナント分離を実装している
