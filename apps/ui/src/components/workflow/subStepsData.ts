/**
 * Sub-steps data for each workflow step
 * Used by all workflow patterns for inline expansion
 */

export interface SubStep {
  id: string;
  name: string;
  description: string;
}

export const SUB_STEPS: Record<string, SubStep[]> = {
  "step-1": [
    { id: "input-validate", name: "入力検証", description: "キーワードと要件の形式チェック" },
    { id: "input-normalize", name: "データ正規化", description: "入力データの標準化" },
  ],
  step0: [
    { id: "prep-config", name: "設定読み込み", description: "モデル設定とパラメータの初期化" },
    { id: "prep-context", name: "コンテキスト準備", description: "実行環境の準備" },
  ],
  step1: [
    { id: "analysis-keyword", name: "キーワード解析", description: "検索意図と関連語の分析" },
    { id: "analysis-serp", name: "SERP分析", description: "検索結果ページの構造分析" },
    { id: "analysis-intent", name: "検索意図分類", description: "ユーザーインテントの特定" },
  ],
  "step1.5": [
    { id: "related-kw", name: "関連KW抽出", description: "関連キーワード候補の抽出" },
    { id: "related-serp", name: "関連SERP収集", description: "関連KWの競合記事を取得" },
  ],
  step2: [
    { id: "research-fetch", name: "ページ取得", description: "競合ページのコンテンツ取得" },
    { id: "research-extract", name: "コンテンツ抽出", description: "本文とメタデータの抽出" },
    { id: "research-analyze", name: "競合分析", description: "競合の強み・弱みの分析" },
  ],
  step3: [
    { id: "outline-generate", name: "構成生成", description: "AI による記事構成の生成" },
    { id: "outline-validate", name: "構成検証", description: "構成の論理性チェック" },
  ],
  step3a: [
    { id: "content-a-gen", name: "コンテンツ生成", description: "セクションAの本文生成" },
    { id: "content-a-validate", name: "品質チェック", description: "生成内容の品質検証" },
  ],
  step3b: [
    { id: "content-b-gen", name: "コンテンツ生成", description: "セクションBの本文生成" },
    { id: "content-b-validate", name: "品質チェック", description: "生成内容の品質検証" },
  ],
  step3c: [
    { id: "content-c-gen", name: "コンテンツ生成", description: "セクションCの本文生成" },
    { id: "content-c-validate", name: "品質チェック", description: "生成内容の品質検証" },
  ],
  "step3.5": [
    { id: "human-touch", name: "人間味生成", description: "感情・体験要素の作成" },
    { id: "human-touch-validate", name: "要素確認", description: "生成要素の整合性確認" },
  ],
  step4: [
    { id: "prep-merge", name: "コンテンツ統合", description: "並列生成結果の統合" },
    { id: "prep-order", name: "構成最適化", description: "セクション順序の最適化" },
  ],
  step5: [
    { id: "write-intro", name: "導入部生成", description: "リード文と導入セクション" },
    { id: "write-body", name: "本文生成", description: "メインコンテンツの生成" },
    { id: "write-conclusion", name: "結論生成", description: "まとめセクションの生成" },
  ],
  step6: [
    { id: "edit-grammar", name: "文法チェック", description: "文法・表現の修正" },
    { id: "edit-style", name: "スタイル調整", description: "トーン・文体の統一" },
    { id: "edit-seo", name: "SEO最適化", description: "キーワード密度の調整" },
  ],
  "step6.5": [
    { id: "package-bundle", name: "バンドル作成", description: "成果物のパッケージング" },
    { id: "package-validate", name: "整合性検証", description: "パッケージの検証" },
  ],
  step7a: [
    { id: "html-generate", name: "HTML生成", description: "マークアップの生成" },
    { id: "html-validate", name: "HTML検証", description: "構文とアクセシビリティ検証" },
  ],
  step7b: [
    { id: "meta-title", name: "タイトル生成", description: "SEOタイトルの生成" },
    { id: "meta-description", name: "メタ説明生成", description: "メタディスクリプションの生成" },
    { id: "meta-og", name: "OGP生成", description: "ソーシャルメタタグの生成" },
  ],
  step8: [
    { id: "verify-seo", name: "SEO検証", description: "SEOスコアのチェック" },
    { id: "verify-quality", name: "品質検証", description: "コンテンツ品質の最終確認" },
    { id: "verify-links", name: "リンク検証", description: "内部・外部リンクの検証" },
  ],
  step9: [{ id: "adjust-final", name: "最終調整", description: "検証結果に基づく修正" }],
  step10: [
    { id: "complete-save", name: "保存処理", description: "成果物の最終保存" },
    { id: "complete-notify", name: "完了通知", description: "完了ステータスの更新" },
  ],
  step11: [
    { id: "image-analyze", name: "挿入位置分析", description: "記事を分析して画像挿入ポイントを特定" },
    { id: "image-generate", name: "画像生成", description: "各位置に対して画像を生成" },
    { id: "image-insert", name: "画像挿入", description: "HTML/Markdownに画像を挿入" },
    { id: "image-preview", name: "プレビュー", description: "最終プレビューの生成" },
  ],
  step12: [
    { id: "wp-convert", name: "WP変換", description: "Gutenbergブロック形式に変換" },
    { id: "wp-validate", name: "HTML検証", description: "WordPress向けHTMLの整合性確認" },
    { id: "wp-save", name: "成果物保存", description: "生成HTMLの保存" },
  ],
};

/**
 * Calculate sub-step status based on parent step status
 *
 * Note: Since backend doesn't track individual sub-step progress,
 * we show sub-steps as:
 * - All completed when parent is completed
 * - Last one failed when parent is failed
 * - First one running, rest pending when parent is running
 * - All pending when parent is pending
 */
export function getSubStepStatus(
  parentStatus: string | undefined,
  subStepIndex: number,
  totalSubSteps: number,
): "completed" | "running" | "failed" | "pending" {
  if (!parentStatus) return "pending";
  if (parentStatus === "completed") return "completed";
  if (parentStatus === "failed") {
    // When parent fails, assume it failed at the last sub-step
    return subStepIndex < totalSubSteps - 1 ? "completed" : "failed";
  }
  if (parentStatus === "running") {
    // When parent is running, show first sub-step as running
    // This is a simplified view since we don't have granular sub-step tracking
    if (subStepIndex === 0) return "running";
    return "pending";
  }
  return "pending";
}
