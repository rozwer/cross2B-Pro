# ヒアリングテンプレート集（テスト用）

> コピペで使えるアンケート回答テンプレート。API に直接 POST するか、フォームに貼り付けて使用。

---

## 使い方

### 1. API 直接 POST

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '<以下のJSONをコピペ>'
```

### 2. フロントエンドのデバッグコンソール

```javascript
// ブラウザのコンソールで実行
const template = <以下のJSONをコピペ>;
fetch('/api/runs', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(template)
}).then(r => r.json()).then(console.log);
```

---

## テンプレート一覧

| # | 名前 | 業種 | キーワード状態 | CTA |
|---|------|------|---------------|-----|
| 1 | 派遣社員教育 | 人材派遣 | 決定済み | 単一 |
| 2 | SaaS マーケ | IT/SaaS | 決定済み | 段階的 |
| 3 | 飲食店集客 | 飲食業 | 未定（テーマのみ） | 単一 |
| 4 | 不動産投資 | 不動産 | 決定済み | 段階的 |
| 5 | 医療クリニック | 医療 | 未定（テーマのみ） | 単一 |

---

## テンプレート 1: 派遣社員教育（人材派遣）

**特徴**: スタンダードなテンプレート、キーワード決定済み、単一CTA

```json
{
  "business": {
    "description": "派遣社員向けeラーニングサービスを提供。中小企業の人材教育をサポートし、派遣社員のスキルアップと定着率向上を実現します。",
    "target_cv": "inquiry",
    "target_cv_other": null,
    "target_audience": "派遣会社の教育担当者、人事部長、30〜50代、派遣社員の離職率や教育コストに悩んでいる方",
    "company_strengths": "中小企業特化、月額5,000円からの低コストプラン、導入実績300社以上、24時間サポート対応"
  },
  "keyword": {
    "status": "decided",
    "main_keyword": "派遣社員 教育方法",
    "monthly_search_volume": "100-200",
    "competition_level": "medium",
    "theme_topics": null,
    "selected_keyword": null,
    "related_keywords": [
      {"keyword": "派遣社員 研修", "volume": "50-100"},
      {"keyword": "派遣社員 スキルアップ", "volume": "30-50"}
    ]
  },
  "strategy": {
    "article_style": "standalone",
    "child_topics": null
  },
  "word_count": {
    "mode": "ai_seo_optimized",
    "target": null
  },
  "cta": {
    "type": "single",
    "position_mode": "ai",
    "single": {
      "url": "https://example.com/contact",
      "text": "無料トライアルを申し込む",
      "description": "14日間の無料トライアルで、eラーニングの効果を実感してください"
    },
    "staged": null
  },
  "confirmed": true
}
```

---

## テンプレート 2: SaaS マーケティング（IT/SaaS）

**特徴**: トピッククラスター戦略、段階的CTA、手動文字数指定

```json
{
  "business": {
    "description": "BtoB向けマーケティングオートメーションツールを提供。リード獲得から育成、商談化までを一気通貫で支援するクラウドサービスです。",
    "target_cv": "document_request",
    "target_cv_other": null,
    "target_audience": "BtoB企業のマーケティング担当者、マーケティング部長、デジタルマーケティングに課題を感じている30〜40代",
    "company_strengths": "日本語UIで使いやすい、Salesforce/HubSpot連携、専任CSによる導入支援、月額3万円から"
  },
  "keyword": {
    "status": "decided",
    "main_keyword": "マーケティングオートメーション 比較",
    "monthly_search_volume": "500-1000",
    "competition_level": "high",
    "theme_topics": null,
    "selected_keyword": null,
    "related_keywords": [
      {"keyword": "MA ツール おすすめ", "volume": "200-500"},
      {"keyword": "マーケティングオートメーション 導入", "volume": "100-200"}
    ]
  },
  "strategy": {
    "article_style": "topic_cluster",
    "child_topics": [
      "MAツール導入の失敗パターンと対策",
      "MAツール選定チェックリスト",
      "MAツール活用事例集"
    ]
  },
  "word_count": {
    "mode": "manual",
    "target": 15000
  },
  "cta": {
    "type": "staged",
    "position_mode": "fixed",
    "single": null,
    "staged": {
      "early": {
        "url": "https://example.com/whitepaper",
        "text": "MA導入ガイドをダウンロード",
        "description": "MAツール選定の基礎知識をまとめた資料",
        "position": 650
      },
      "mid": {
        "url": "https://example.com/case-study",
        "text": "導入事例を見る",
        "description": "業界別の導入成功事例集",
        "position": 2800
      },
      "final": {
        "url": "https://example.com/demo",
        "text": "無料デモを予約する",
        "description": "製品デモと個別相談",
        "position": null
      }
    }
  },
  "confirmed": true
}
```

---

## テンプレート 3: 飲食店集客（飲食業）

**特徴**: キーワード未定（テーマのみ）、AI にキーワード提案を依頼

```json
{
  "business": {
    "description": "飲食店向けの集客・予約管理システムを提供。Googleマップ対策、SNS連携、予約システムを一元管理できるクラウドサービスです。",
    "target_cv": "free_consultation",
    "target_cv_other": null,
    "target_audience": "個人経営の飲食店オーナー、居酒屋・カフェ・レストランの店長、集客に悩む30〜50代",
    "company_strengths": "初期費用0円、月額9,800円、導入店舗5,000店以上、Googleマップ上位表示実績多数"
  },
  "keyword": {
    "status": "undecided",
    "main_keyword": null,
    "monthly_search_volume": null,
    "competition_level": null,
    "theme_topics": "飲食店の集客方法について書きたい。特にGoogleマップを活用した集客や、SNSを使った効果的な宣伝方法に興味がある。",
    "selected_keyword": null,
    "related_keywords": null
  },
  "strategy": {
    "article_style": "standalone",
    "child_topics": null
  },
  "word_count": {
    "mode": "ai_balanced",
    "target": null
  },
  "cta": {
    "type": "single",
    "position_mode": "ai",
    "single": {
      "url": "https://example.com/free-consultation",
      "text": "無料集客診断を受ける",
      "description": "現在の集客状況を無料で診断し、改善提案をお伝えします"
    },
    "staged": null
  },
  "confirmed": true
}
```

---

## テンプレート 4: 不動産投資（不動産）

**特徴**: 高競合キーワード、段階的CTA、SEO最適化文字数

```json
{
  "business": {
    "description": "不動産投資のコンサルティングサービスを提供。初心者向けのセミナー開催から、物件紹介、融資サポート、管理代行まで一貫して支援します。",
    "target_cv": "other",
    "target_cv_other": "セミナー申込",
    "target_audience": "不動産投資に興味のある会社員、年収600万円以上、30〜40代、将来の資産形成に関心がある方",
    "company_strengths": "10年以上の実績、成約率95%、提携金融機関20社以上、初心者向けセミナー毎月開催"
  },
  "keyword": {
    "status": "decided",
    "main_keyword": "不動産投資 始め方",
    "monthly_search_volume": "1000-2000",
    "competition_level": "high",
    "theme_topics": null,
    "selected_keyword": null,
    "related_keywords": [
      {"keyword": "不動産投資 初心者", "volume": "500-1000"},
      {"keyword": "ワンルームマンション投資", "volume": "300-500"},
      {"keyword": "不動産投資 リスク", "volume": "200-500"}
    ]
  },
  "strategy": {
    "article_style": "topic_cluster",
    "child_topics": [
      "不動産投資の種類と特徴",
      "不動産投資の融資審査のポイント",
      "不動産投資の失敗事例と対策"
    ]
  },
  "word_count": {
    "mode": "ai_seo_optimized",
    "target": null
  },
  "cta": {
    "type": "staged",
    "position_mode": "ratio",
    "single": null,
    "staged": {
      "early": {
        "url": "https://example.com/ebook",
        "text": "不動産投資入門ガイドを無料ダウンロード",
        "description": "初心者向けの基礎知識をまとめたPDF",
        "position": null
      },
      "mid": {
        "url": "https://example.com/seminar",
        "text": "無料セミナーに参加する",
        "description": "毎月開催の初心者向けセミナー",
        "position": null
      },
      "final": {
        "url": "https://example.com/consultation",
        "text": "個別相談を予約する",
        "description": "専門コンサルタントとの1on1相談",
        "position": null
      }
    }
  },
  "confirmed": true
}
```

---

## テンプレート 5: 医療クリニック（医療）

**特徴**: キーワード未定、読みやすさ優先の文字数、シンプルな単一CTA

```json
{
  "business": {
    "description": "美容皮膚科クリニックを運営。シミ・しわ・たるみ治療、医療脱毛、ニキビ治療など、最新の美容医療を提供しています。",
    "target_cv": "inquiry",
    "target_cv_other": null,
    "target_audience": "美容に関心のある20〜40代女性、肌悩みを抱えている方、医療機関での治療を検討している方",
    "company_strengths": "皮膚科専門医在籍、最新レーザー機器導入、症例実績10,000件以上、カウンセリング無料"
  },
  "keyword": {
    "status": "undecided",
    "main_keyword": null,
    "monthly_search_volume": null,
    "competition_level": null,
    "theme_topics": "シミ取りレーザー治療について詳しく解説したい。治療の種類、効果、ダウンタイム、料金相場などを網羅的に説明する記事を書きたい。",
    "selected_keyword": null,
    "related_keywords": null
  },
  "strategy": {
    "article_style": "standalone",
    "child_topics": null
  },
  "word_count": {
    "mode": "ai_readability",
    "target": null
  },
  "cta": {
    "type": "single",
    "position_mode": "fixed",
    "single": {
      "url": "https://example.com/reservation",
      "text": "無料カウンセリングを予約する",
      "description": "医師による肌診断と最適な治療プランのご提案"
    },
    "staged": null
  },
  "confirmed": true
}
```

---

## 最小限テンプレート（デバッグ用）

最小限の必須フィールドのみ。素早くテストしたい場合に使用。

```json
{
  "business": {
    "description": "テスト用の事業内容説明です。最低10文字必要。",
    "target_cv": "inquiry",
    "target_cv_other": null,
    "target_audience": "テスト用のターゲット読者像です。最低10文字必要。",
    "company_strengths": "テスト用の自社強みです。最低10文字必要。"
  },
  "keyword": {
    "status": "decided",
    "main_keyword": "テスト キーワード",
    "monthly_search_volume": "100-200",
    "competition_level": "low",
    "theme_topics": null,
    "selected_keyword": null,
    "related_keywords": null
  },
  "strategy": {
    "article_style": "standalone",
    "child_topics": null
  },
  "word_count": {
    "mode": "ai_balanced",
    "target": null
  },
  "cta": {
    "type": "single",
    "position_mode": "ai",
    "single": {
      "url": "https://example.com/test",
      "text": "テストCTAボタン",
      "description": ""
    },
    "staged": null
  },
  "confirmed": true
}
```

---

## cURL コマンド例

### テンプレート1を実行

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
  "business": {
    "description": "派遣社員向けeラーニングサービスを提供。中小企業の人材教育をサポートし、派遣社員のスキルアップと定着率向上を実現します。",
    "target_cv": "inquiry",
    "target_cv_other": null,
    "target_audience": "派遣会社の教育担当者、人事部長、30〜50代、派遣社員の離職率や教育コストに悩んでいる方",
    "company_strengths": "中小企業特化、月額5,000円からの低コストプラン、導入実績300社以上、24時間サポート対応"
  },
  "keyword": {
    "status": "decided",
    "main_keyword": "派遣社員 教育方法",
    "monthly_search_volume": "100-200",
    "competition_level": "medium",
    "theme_topics": null,
    "selected_keyword": null,
    "related_keywords": null
  },
  "strategy": {
    "article_style": "standalone",
    "child_topics": null
  },
  "word_count": {
    "mode": "ai_seo_optimized",
    "target": null
  },
  "cta": {
    "type": "single",
    "position_mode": "ai",
    "single": {
      "url": "https://example.com/contact",
      "text": "無料トライアルを申し込む",
      "description": "14日間の無料トライアルで、eラーニングの効果を実感してください"
    },
    "staged": null
  },
  "confirmed": true
}'
```

### 最小限テンプレートを実行

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"business":{"description":"テスト用の事業内容説明です。最低10文字必要。","target_cv":"inquiry","target_cv_other":null,"target_audience":"テスト用のターゲット読者像です。最低10文字必要。","company_strengths":"テスト用の自社強みです。最低10文字必要。"},"keyword":{"status":"decided","main_keyword":"テスト キーワード","monthly_search_volume":"100-200","competition_level":"low","theme_topics":null,"selected_keyword":null,"related_keywords":null},"strategy":{"article_style":"standalone","child_topics":null},"word_count":{"mode":"ai_balanced","target":null},"cta":{"type":"single","position_mode":"ai","single":{"url":"https://example.com/test","text":"テストCTAボタン","description":""},"staged":null},"confirmed":true}'
```

---

## フィールド早見表

### business（必須）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| description | string | ✓ | 事業内容（10文字以上） |
| target_cv | enum | ✓ | `inquiry` / `document_request` / `free_consultation` / `other` |
| target_cv_other | string | △ | target_cv=other の場合のみ必須 |
| target_audience | string | ✓ | ターゲット読者像（10文字以上） |
| company_strengths | string | ✓ | 自社の強み（10文字以上） |

### keyword（必須）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| status | enum | ✓ | `decided` / `undecided` |
| main_keyword | string | △ | status=decided の場合必須 |
| monthly_search_volume | string | - | 月間検索ボリューム |
| competition_level | enum | - | `high` / `medium` / `low` |
| theme_topics | string | △ | status=undecided の場合必須 |
| selected_keyword | object | - | LLM提案から選択したキーワード |
| related_keywords | array | - | 関連キーワード一覧 |

### strategy（必須）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| article_style | enum | ✓ | `standalone` / `topic_cluster` |
| child_topics | array | - | topic_cluster の場合の子記事トピック |

### word_count（必須）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| mode | enum | ✓ | `manual` / `ai_seo_optimized` / `ai_readability` / `ai_balanced` |
| target | int | △ | mode=manual の場合必須（1000-50000） |

### cta（必須）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| type | enum | ✓ | `single` / `staged` |
| position_mode | enum | ✓ | `fixed` / `ratio` / `ai` |
| single | object | △ | type=single の場合必須 |
| staged | object | △ | type=staged の場合必須 |

### confirmed（必須）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| confirmed | bool | ✓ | 必ず `true` |
