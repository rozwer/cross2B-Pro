# blog.System プロンプト比較分析

**作成日**: 2026-01-08

## 分析結果サマリー

| 観点 | default.json | blog.System Ver8.3 |
|------|-------------|-------------------|
| 詳細度 | 1-3ステップ/工程 | 5-15ステップ/工程 |
| 4本柱 | ❌ | ✅ 全工程で必須 |
| 3フェーズ | ❌ | ✅ Phase1/2/3 |
| KGI設定 | ❌ | ✅ CVR目標明示 |
| チェックリスト | ❌ | ✅ 10重+4本柱 |
| 出力スキーマ | JSON簡潔 | JSON詳細（3-5倍） |
| Human-in-the-loop | ❌ | ✅ 明示的 |

## 新規追加工程

| 工程 | 名称 | 説明 |
|------|------|------|
| -1 | 絶対条件ヒアリング | 工程0前の要件確認 |
| 1.5 | 関連KW競合取得 | サジェストKWの競合分析 |
| 2 | CSV読み込み・初期化 | データ正規化（詳細版） |
| 3C | 競合分析・差別化 | 5 Whys深層分析 |
| 6.5 | 構成案作成 | ファイル集約ハブ |
| 11 | 画像差し込み提案 | Human-in-the-loop |
| 12 | WordPress HTML | Gutenberg対応 |
| 13 | WordPress自動投稿 | 将来実装 |

## unified_knowledge.json 構造

```json
{
  "process_info": {
    "name": "工程名",
    "version": "バージョン",
    "purpose": "目的"
  },
  "guidelines": {
    "source": "detailed_guidelines.md",
    "content": "ガイドライン全文（Markdown）"
  },
  "templates": {
    "output_template_complete": {
      // 出力スキーマ定義（詳細）
    }
  },
  "examples": {
    // 具体例
  },
  "checklist": {
    // 4本柱チェックリスト
  }
}
```

## 主要な差異詳細

### 4本柱（神経科学・行動経済学・LLMO・KGI）

| 柱 | default.json | blog.System |
|----|-------------|-------------|
| 神経科学 | ❌ 言及なし | ✅ 3フェーズ（扁桃体→前頭前野→線条体） |
| 行動経済学 | ❌ 言及なし | ✅ 6原則を工程3A以降で必須配置 |
| LLMO | ❌ 言及なし | ✅ 400-600 tokens/section、独立性 |
| KGI | ❌ 言及なし | ✅ CVR目標（Early 3%, Mid 2-3%, Final 2-3%） |

### 変数マッピング

| blog.System変数 | 既存変数 | 備考 |
|----------------|---------|------|
| `{{target_word_count}}` | なし | 全工程で厳守のマスター変数 |
| `{{strategy}}` | なし | 標準記事 vs トピッククラスター |
| `{{word_count_mode}}` | なし | manual / ai_seo_optimized等 |
| `{{keyword}}` | `{{keyword}}` | 同一 |

### 出力スキーマの違い（工程3Aの例）

**default.json**:
```json
{
  "query_type": "informational",
  "user_intent": "...",
  "related_queries": ["..."],
  "content_format_suggestion": "..."
}
```

**blog.System**:
```json
{
  "analysis_date": "ISO 8601",
  "keyword": "...",
  "core_question": {...},
  "question_hierarchy": {...},
  "persona_deep_dive": {
    "behavioral_economics_profile": {
      "loss_aversion": {...},
      "social_proof": {...},
      // 6原則すべて
    }
  },
  "three_phase_psychological_mapping": {
    "phase1_anxiety": {...},
    "phase2_understanding": {...},
    "phase3_action": {...}
  }
}
```

## 統合方針の検討ポイント

1. **プロンプト管理方式**
   - A案: default.json を拡張
   - B案: instructions.txt + unified_knowledge.json 形式を採用
   - C案: DBで管理、形式は混在許可

2. **4本柱の実装方法**
   - 出力バリデーションで自動チェック
   - LLMに4本柱チェックリストを強制

3. **フロー変更の範囲**
   - 新規工程の追加（-1, 1.5, 6.5等）
   - 既存工程の強化（3C, 11, 12）
