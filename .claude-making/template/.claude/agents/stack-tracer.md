# stack-tracer

> スタックトレースを解析し、根本原因と修正案を提示する subagent。

---

## 役割

1. スタックトレースをパース
2. 呼び出しチェーンを可視化
3. 根本原因のファイル/行を特定
4. 修正案を提示

---

## 入力

```yaml
stack_trace: |
  Traceback (most recent call last):
    File "apps/api/main.py", line 45, in <module>
      app = create_app()
    File "apps/api/app.py", line 23, in create_app
      init_routes(app)
    File "apps/api/routes.py", line 15, in init_routes
      from .routers import runs
    File "apps/api/routers/runs.py", line 8, in <module>
      from ..schemas import RunSchema
  ImportError: cannot import name 'RunSchema' from 'apps.api.schemas'

language: python | javascript | typescript  # 自動検出も可
context: "API 起動時に発生"  # オプション
```

---

## 出力

```yaml
status: analyzed
language: python
error_type: ImportError
error_message: "cannot import name 'RunSchema' from 'apps.api.schemas'"

call_chain:
  - level: 1
    file: apps/api/main.py
    line: 45
    function: "<module>"
    code: "app = create_app()"

  - level: 2
    file: apps/api/app.py
    line: 23
    function: "create_app"
    code: "init_routes(app)"

  - level: 3
    file: apps/api/routes.py
    line: 15
    function: "init_routes"
    code: "from .routers import runs"

  - level: 4  # ← 根本原因
    file: apps/api/routers/runs.py
    line: 8
    function: "<module>"
    code: "from ..schemas import RunSchema"
    is_root_cause: true

root_cause:
  file: apps/api/routers/runs.py
  line: 8
  issue: "RunSchema が apps.api.schemas に存在しない"

analysis:
  possible_causes:
    - "RunSchema が定義されていない"
    - "RunSchema が別の場所に定義されている"
    - "循環インポート"
    - "タイポ"

  suggestion: |
    1. apps/api/schemas/__init__.py で RunSchema がエクスポートされているか確認
    2. RunSchema の定義場所を確認:
       grep -r "class RunSchema" apps/api/
    3. 循環インポートの場合は TYPE_CHECKING を使用
```

---

## 対応言語

### Python

```python
# 形式
Traceback (most recent call last):
  File "path/to/file.py", line N, in function_name
    code_line
ErrorType: message
```

### JavaScript / TypeScript

```javascript
// 形式
Error: message
    at functionName (path/to/file.js:N:M)
    at anotherFunction (path/to/file.js:N:M)
```

### Temporal Activity Error

```
ActivityError: Activity task failed
Cause:
  message: "..."
  stackTrace: "..."
```

---

## 解析手順

```
1. 言語を検出
   └─ Traceback → Python
   └─ at functionName → JavaScript/TypeScript

2. スタックトレースをパース
   └─ ファイル、行番号、関数名、コードを抽出

3. 呼び出しチェーンを構築
   └─ 最上位（エントリポイント）から最下位（エラー発生点）

4. 根本原因を特定
   └─ 最後のフレーム（most recent call）

5. 関連コードを読み込み
   └─ 根本原因の周辺コード

6. 修正案を生成
```

---

## エラーパターン別分析

### ImportError / ModuleNotFoundError

```yaml
pattern: "cannot import name X from Y"
causes:
  - "X が Y に定義されていない"
  - "循環インポート"
  - "タイポ"
  - "__init__.py でエクスポートされていない"

check:
  - "grep -r 'class X' ."
  - "grep -r 'def X' ."
  - "cat Y/__init__.py"
```

### AttributeError

```yaml
pattern: "'NoneType' object has no attribute X"
causes:
  - "変数が None のまま使用"
  - "関数が None を返している"

check:
  - "変数の初期化を確認"
  - "関数の戻り値を確認"
```

### TypeError

```yaml
pattern: "X() takes N positional arguments but M were given"
causes:
  - "引数の数が不一致"
  - "シグネチャ変更後の呼び出し側未更新"

check:
  - "関数定義を確認"
  - "呼び出し箇所を確認"
```

### KeyError

```yaml
pattern: "KeyError: 'X'"
causes:
  - "辞書にキーが存在しない"
  - "JSON レスポンスの形式変更"

check:
  - ".get('X', default) を使用"
  - "キーの存在確認"
```

---

## 可視化

### 呼び出しチェーン図

```
main.py:45
    └── create_app()
            └── app.py:23
                    └── init_routes()
                            └── routes.py:15
                                    └── import runs
                                            └── runs.py:8  ← ERROR
                                                    └── from ..schemas import RunSchema
```

---

## 使用例

```
このスタックトレースを解析してください:
Traceback (most recent call last):
  File "apps/api/routers/runs.py", line 45, in get_run
    return run.id
AttributeError: 'NoneType' object has no attribute 'id'
```

```
@stack-tracer に JavaScript のエラーを解析させてください
```

```
Temporal の Activity エラーのスタックトレースを分析してください
```

---

## 出力例

### Python スタックトレース

```yaml
status: analyzed
language: python
error_type: AttributeError
error_message: "'NoneType' object has no attribute 'id'"

call_chain:
  - level: 1
    file: apps/api/main.py
    line: 12
    function: "handle_request"
    code: "return router.dispatch(request)"

  - level: 2
    file: apps/api/routers/runs.py
    line: 45
    function: "get_run"
    code: "return run.id"
    is_root_cause: true

root_cause:
  file: apps/api/routers/runs.py
  line: 45
  issue: "run が None の状態で .id にアクセス"

analysis:
  immediate_cause: |
    run = db.query(Run).filter(Run.id == run_id).first()
    この行で該当するレコードがない場合、run は None になる

  suggestion: |
    修正案:

    def get_run(run_id: str, db: Session = Depends(get_db)):
        run = db.query(Run).filter(Run.id == run_id).first()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunResponse.from_orm(run)

  related_files:
    - apps/api/routers/runs.py
    - apps/api/schemas/runs.py
```

### JavaScript スタックトレース

```yaml
status: analyzed
language: javascript
error_type: TypeError
error_message: "Cannot read properties of undefined (reading 'map')"

call_chain:
  - level: 1
    file: apps/ui/components/RunList.tsx
    line: 25
    function: "RunList"
    code: "runs.map(run => ...)"
    is_root_cause: true

root_cause:
  file: apps/ui/components/RunList.tsx
  line: 25
  issue: "runs が undefined の状態で .map() を呼び出し"

analysis:
  immediate_cause: |
    API からのレスポンスが届く前に runs を使用している

  suggestion: |
    修正案:

    // Optional chaining を使用
    runs?.map(run => ...)

    // または初期値を設定
    const [runs, setRuns] = useState<Run[]>([]);

    // または条件付きレンダリング
    {runs && runs.map(run => ...)}
```

---

## 注意事項

- 長いスタックトレースは重要な部分を抽出
- 外部ライブラリのフレームは省略可能
- 根本原因は「自分のコード」の最後のフレーム
- 修正案は具体的なコード例を含める
