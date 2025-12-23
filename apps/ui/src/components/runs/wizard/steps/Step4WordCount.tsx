"use client";

import { WordCountInput, WordCountMode, ArticleStyle } from "@/lib/types";

interface Step4WordCountProps {
  data: WordCountInput;
  onChange: (data: Partial<WordCountInput>) => void;
  articleStyle: ArticleStyle;
  errors: string[];
}

const WORD_COUNT_OPTIONS: {
  value: WordCountMode;
  label: string;
  description: string;
}[] = [
  {
    value: "manual",
    label: "manual（ユーザー指定）",
    description: "すぐに上限文字数を決めたい場合",
  },
  {
    value: "ai_seo_optimized",
    label: "ai_seo_optimized（競合平均 × 1.2）",
    description: "情報量で競合を上回りたい場合",
  },
  {
    value: "ai_readability",
    label: "ai_readability（競合平均 × 0.9）",
    description: "読みやすさを優先したい場合",
  },
  {
    value: "ai_balanced",
    label: "ai_balanced（競合平均 × 1.0 ±5%）【推奨】",
    description: "SEOと読みやすさのバランスを取りたい場合",
  },
];

export function Step4WordCount({
  data,
  onChange,
  articleStyle,
  errors,
}: Step4WordCountProps) {
  const recommendedRange =
    articleStyle === "topic_cluster"
      ? "15,000〜20,000文字"
      : "8,000〜12,000文字";

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

      {/* 文字数設定モード */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          文字数設定モード <span className="text-red-500">*</span>
        </label>
        <p className="mt-1 text-xs text-gray-500">
          ターゲット文字数の決定方法を選んでください
        </p>

        <div className="mt-4 space-y-3">
          {WORD_COUNT_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`
                relative flex cursor-pointer rounded-lg border p-4
                ${
                  data.mode === option.value
                    ? "border-primary-500 bg-primary-50"
                    : "border-gray-200 hover:border-gray-300"
                }
              `}
            >
              <input
                type="radio"
                name="word_count_mode"
                value={option.value}
                checked={data.mode === option.value}
                onChange={() => onChange({ mode: option.value })}
                className="sr-only"
              />
              <div className="flex flex-1 items-center justify-between">
                <div>
                  <span className="block text-sm font-medium text-gray-900">
                    {option.label}
                  </span>
                  <span className="mt-1 text-xs text-gray-500">
                    {option.description}
                  </span>
                </div>
                {data.mode === option.value && (
                  <svg
                    className="h-5 w-5 text-primary-600 flex-shrink-0"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* ターゲット文字数（manualの場合のみ） */}
      {data.mode === "manual" && (
        <div>
          <label
            htmlFor="target_word_count"
            className="block text-sm font-medium text-gray-700"
          >
            ターゲット文字数（上限） <span className="text-red-500">*</span>
          </label>
          <p className="mt-1 text-xs text-gray-500">
            {articleStyle === "topic_cluster"
              ? "トピッククラスター戦略の場合: 推奨 15,000〜20,000文字"
              : "標準記事の場合: 推奨 8,000〜12,000文字"}
          </p>
          <div className="mt-2 flex items-center gap-2">
            <input
              type="number"
              id="target_word_count"
              value={data.target || ""}
              onChange={(e) => {
                const parsed = parseInt(e.target.value, 10);
                onChange({
                  target: !isNaN(parsed) ? parsed : undefined,
                });
              }}
              min={1000}
              max={50000}
              step={1000}
              placeholder="例: 12000"
              className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
            <span className="text-sm text-gray-500">文字</span>
          </div>
        </div>
      )}

      {/* AI決定の場合の説明 */}
      {data.mode !== "manual" && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex">
            <svg
              className="h-5 w-5 text-blue-400 flex-shrink-0"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>ai_* モードを選択した場合:</strong>
              </p>
              <p className="mt-1 text-xs text-blue-600">
                ターゲット文字数は工程3CでAIが競合分析後に算出します。
                後続の工程では自動的に決定された値が使用されます。
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 参考情報 */}
      <div className="p-4 bg-gray-50 border border-gray-200 rounded-md">
        <h4 className="text-sm font-medium text-gray-700">参考: 推奨文字数</h4>
        <ul className="mt-2 text-xs text-gray-500 space-y-1">
          <li>・標準記事（スタンドアロン型）: 8,000〜12,000文字</li>
          <li>・トピッククラスター戦略（親記事）: 15,000〜20,000文字</li>
        </ul>
        <p className="mt-2 text-xs text-gray-400">
          現在の設定:{" "}
          <span className="font-medium">
            {articleStyle === "topic_cluster"
              ? "トピッククラスター戦略"
              : "標準記事"}
          </span>
          （推奨: {recommendedRange}）
        </p>
      </div>
    </div>
  );
}
