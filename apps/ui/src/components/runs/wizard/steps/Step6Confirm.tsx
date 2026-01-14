"use client";

import {
  BusinessInput,
  KeywordInput,
  StrategyInput,
  WordCountInput,
  CTAInput,
} from "@/lib/types";
import { RepoSelector } from "@/components/github/RepoSelector";

interface WizardFormData {
  business: BusinessInput;
  keyword: KeywordInput;
  strategy: StrategyInput;
  word_count: WordCountInput;
  cta: CTAInput;
  confirmed: boolean;
  github_repo_url: string;
}

interface Step6ConfirmProps {
  formData: WizardFormData;
  onConfirm: (confirmed: boolean) => void;
  onGitHubRepoChange: (repoUrl: string) => void;
  errors: string[];
}

const TARGET_CV_LABELS: Record<string, string> = {
  inquiry: "問い合わせ獲得",
  document_request: "資料請求",
  free_consultation: "無料相談申込",
  other: "その他",
};

const WORD_COUNT_MODE_LABELS: Record<string, string> = {
  manual: "ユーザー指定",
  ai_seo_optimized: "SEO最適化（競合平均×1.2）",
  ai_readability: "読みやすさ優先（競合平均×0.9）",
  ai_balanced: "バランス型（競合平均±5%）",
};

const CTA_POSITION_LABELS: Record<string, string> = {
  fixed: "固定位置",
  ratio: "比率で動的計算",
  ai: "AIにお任せ",
};

export function Step6Confirm({
  formData,
  onConfirm,
  onGitHubRepoChange,
  errors,
}: Step6ConfirmProps) {
  const { business, keyword, strategy, word_count, cta, confirmed, github_repo_url } = formData;

  // Get effective keyword
  const effectiveKeyword =
    keyword.status === "decided"
      ? keyword.main_keyword
      : keyword.selected_keyword?.keyword;

  return (
    <div className="space-y-6">
      {/* Validation Errors */}
      {errors.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <ul className="list-disc list-inside text-sm text-red-600">
            {errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary Cards */}
      <div className="space-y-4">
        {/* Section 1: Business */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            セクション1: 事業内容とターゲット
          </h3>
          <dl className="space-y-2 text-sm">
            <div className="flex">
              <dt className="w-32 text-gray-500">事業内容:</dt>
              <dd className="flex-1 text-gray-900">{business.description}</dd>
            </div>
            <div className="flex">
              <dt className="w-32 text-gray-500">目標CV:</dt>
              <dd className="flex-1 text-gray-900">
                {TARGET_CV_LABELS[business.target_cv]}
                {business.target_cv === "other" && business.target_cv_other && (
                  <span className="ml-1">({business.target_cv_other})</span>
                )}
              </dd>
            </div>
            <div className="flex">
              <dt className="w-32 text-gray-500">ターゲット:</dt>
              <dd className="flex-1 text-gray-900">{business.target_audience}</dd>
            </div>
            <div className="flex">
              <dt className="w-32 text-gray-500">自社の強み:</dt>
              <dd className="flex-1 text-gray-900">{business.company_strengths}</dd>
            </div>
          </dl>
        </div>

        {/* Section 2: Keyword */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            セクション2: キーワード選定
          </h3>
          <dl className="space-y-2 text-sm">
            <div className="flex">
              <dt className="w-32 text-gray-500">状態:</dt>
              <dd className="flex-1 text-gray-900">
                {keyword.status === "decided" ? "決定済み" : "AI候補から選択"}
              </dd>
            </div>
            <div className="flex">
              <dt className="w-32 text-gray-500">キーワード:</dt>
              <dd className="flex-1 text-gray-900 font-medium">
                {effectiveKeyword || "(未選択)"}
              </dd>
            </div>
            {keyword.status === "decided" && keyword.monthly_search_volume && (
              <div className="flex">
                <dt className="w-32 text-gray-500">検索ボリューム:</dt>
                <dd className="flex-1 text-gray-900">
                  {keyword.monthly_search_volume}
                </dd>
              </div>
            )}
            {keyword.selected_keyword && (
              <>
                <div className="flex">
                  <dt className="w-32 text-gray-500">推定検索数:</dt>
                  <dd className="flex-1 text-gray-900">
                    {keyword.selected_keyword.estimated_volume}
                  </dd>
                </div>
                <div className="flex">
                  <dt className="w-32 text-gray-500">推定競合性:</dt>
                  <dd className="flex-1 text-gray-900">
                    {keyword.selected_keyword.estimated_competition}
                  </dd>
                </div>
              </>
            )}
            {keyword.related_keywords && keyword.related_keywords.length > 0 && (
              <div className="flex">
                <dt className="w-32 text-gray-500">関連KW:</dt>
                <dd className="flex-1 text-gray-900">
                  {keyword.related_keywords.map((rk) => rk.keyword).join(", ")}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Section 3: Strategy */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            セクション3: 記事戦略
          </h3>
          <dl className="space-y-2 text-sm">
            <div className="flex">
              <dt className="w-32 text-gray-500">スタイル:</dt>
              <dd className="flex-1 text-gray-900">
                {strategy.article_style === "standalone"
                  ? "標準記事（スタンドアロン）"
                  : "トピッククラスター戦略"}
              </dd>
            </div>
            {strategy.article_style === "topic_cluster" &&
              strategy.child_topics &&
              strategy.child_topics.length > 0 && (
                <div className="flex">
                  <dt className="w-32 text-gray-500">子記事:</dt>
                  <dd className="flex-1 text-gray-900">
                    <ul className="list-disc list-inside">
                      {strategy.child_topics.map((topic, idx) => (
                        <li key={idx}>{topic}</li>
                      ))}
                    </ul>
                  </dd>
                </div>
              )}
          </dl>
        </div>

        {/* Section 4: Word Count */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            セクション4: 文字数設定
          </h3>
          <dl className="space-y-2 text-sm">
            <div className="flex">
              <dt className="w-32 text-gray-500">モード:</dt>
              <dd className="flex-1 text-gray-900">
                {WORD_COUNT_MODE_LABELS[word_count.mode]}
              </dd>
            </div>
            {word_count.mode === "manual" && word_count.target && (
              <div className="flex">
                <dt className="w-32 text-gray-500">文字数:</dt>
                <dd className="flex-1 text-gray-900">
                  {word_count.target.toLocaleString()}文字
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Section 5: CTA */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            セクション5: CTA設定
          </h3>
          <dl className="space-y-2 text-sm">
            <div className="flex">
              <dt className="w-32 text-gray-500">タイプ:</dt>
              <dd className="flex-1 text-gray-900">
                {cta.type === "single" ? "単一CTA" : "段階的CTA"}
              </dd>
            </div>
            <div className="flex">
              <dt className="w-32 text-gray-500">位置モード:</dt>
              <dd className="flex-1 text-gray-900">
                {CTA_POSITION_LABELS[cta.position_mode]}
              </dd>
            </div>
            {cta.type === "single" && cta.single && (
              <>
                <div className="flex">
                  <dt className="w-32 text-gray-500">URL:</dt>
                  <dd className="flex-1 text-gray-900 truncate">
                    {cta.single.url}
                  </dd>
                </div>
                <div className="flex">
                  <dt className="w-32 text-gray-500">テキスト:</dt>
                  <dd className="flex-1 text-gray-900">{cta.single.text}</dd>
                </div>
              </>
            )}
            {cta.type === "staged" && cta.staged && (
              <div className="mt-2 space-y-2">
                {(["early", "mid", "final"] as const).map((phase) => (
                  <div key={phase} className="pl-4 border-l-2 border-gray-200">
                    <p className="text-xs font-medium text-gray-600 uppercase">
                      {phase}
                    </p>
                    <p className="text-gray-900">{cta.staged![phase].text}</p>
                    <p className="text-xs text-gray-500 truncate">
                      {cta.staged![phase].url}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* GitHub Integration Section */}
      <div className="border border-gray-200 rounded-lg p-4">
        <RepoSelector
          value={github_repo_url}
          onChange={onGitHubRepoChange}
        />
      </div>

      {/* Confirmation Checkbox */}
      <div className="border-t border-gray-200 pt-6">
        <label className="flex items-start">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => onConfirm(e.target.checked)}
            className="h-5 w-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500 mt-0.5"
          />
          <span className="ml-3 text-sm text-gray-700">
            上記の内容で記事生成を開始することを確認しました。
            <span className="text-red-500">*</span>
          </span>
        </label>
      </div>
    </div>
  );
}
