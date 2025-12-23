"use client";

import {
  KeywordInput,
  CompetitionLevel,
  KeywordSuggestion,
} from "@/lib/types";

interface Step2KeywordProps {
  data: KeywordInput;
  onChange: (data: Partial<KeywordInput>) => void;
  suggestions: KeywordSuggestion[] | null;
  isLoadingSuggestions: boolean;
  onGenerateSuggestions: () => void;
  onSelectKeyword: (suggestion: KeywordSuggestion) => void;
  errors: string[];
}

const COMPETITION_LABELS: Record<CompetitionLevel, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const COMPETITION_COLORS: Record<CompetitionLevel, string> = {
  high: "text-red-600 bg-red-50",
  medium: "text-yellow-600 bg-yellow-50",
  low: "text-green-600 bg-green-50",
};

export function Step2Keyword({
  data,
  onChange,
  suggestions,
  isLoadingSuggestions,
  onGenerateSuggestions,
  onSelectKeyword,
  errors,
}: Step2KeywordProps) {
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

      {/* キーワードの状態 */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          キーワードの状態 <span className="text-red-500">*</span>
        </label>
        <p className="mt-1 text-xs text-gray-500">
          メインキーワードの状態を選択してください
        </p>
        <div className="mt-2 space-y-2">
          <label className="flex items-start">
            <input
              type="radio"
              name="keyword_status"
              value="decided"
              checked={data.status === "decided"}
              onChange={() => onChange({ status: "decided" })}
              className="h-4 w-4 mt-0.5 text-primary-600 border-gray-300 focus:ring-primary-500"
            />
            <div className="ml-2">
              <span className="text-sm font-medium text-gray-700">
                ①既に決まっている
              </span>
              <p className="text-xs text-gray-500">
                Googleキーワードプランナーで検証済みのキーワードがある場合
              </p>
            </div>
          </label>
          <label className="flex items-start">
            <input
              type="radio"
              name="keyword_status"
              value="undecided"
              checked={data.status === "undecided"}
              onChange={() => onChange({ status: "undecided" })}
              className="h-4 w-4 mt-0.5 text-primary-600 border-gray-300 focus:ring-primary-500"
            />
            <div className="ml-2">
              <span className="text-sm font-medium text-gray-700">
                ②まだ決まっていない
              </span>
              <p className="text-xs text-gray-500">
                AIにキーワード候補を提案してもらいたい場合
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* 決まっている場合のフィールド */}
      {data.status === "decided" && (
        <>
          <div>
            <label
              htmlFor="main_keyword"
              className="block text-sm font-medium text-gray-700"
            >
              メインキーワード <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="main_keyword"
              value={data.main_keyword || ""}
              onChange={(e) => onChange({ main_keyword: e.target.value })}
              placeholder="例: 派遣社員 教育方法"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="monthly_search_volume"
                className="block text-sm font-medium text-gray-700"
              >
                月間検索ボリューム
              </label>
              <input
                type="text"
                id="monthly_search_volume"
                value={data.monthly_search_volume || ""}
                onChange={(e) =>
                  onChange({ monthly_search_volume: e.target.value })
                }
                placeholder="例: 100-200"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                競合性
              </label>
              <div className="mt-1 flex gap-2">
                {(["high", "medium", "low"] as CompetitionLevel[]).map(
                  (level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => onChange({ competition_level: level })}
                      className={`
                        px-3 py-1.5 text-sm rounded-md border
                        ${
                          data.competition_level === level
                            ? "border-primary-500 bg-primary-50 text-primary-700"
                            : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                        }
                      `}
                    >
                      {COMPETITION_LABELS[level]}
                    </button>
                  )
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* 決まっていない場合のフィールド */}
      {data.status === "undecided" && (
        <>
          <div>
            <label
              htmlFor="theme_topics"
              className="block text-sm font-medium text-gray-700"
            >
              書きたいテーマ・トピック <span className="text-red-500">*</span>
            </label>
            <p className="mt-1 text-xs text-gray-500">
              AIがこの情報を基にキーワード候補を10個提案します
            </p>
            <textarea
              id="theme_topics"
              rows={4}
              value={data.theme_topics || ""}
              onChange={(e) => onChange({ theme_topics: e.target.value })}
              placeholder={`例:
派遣社員の教育方法について知りたい
派遣社員の定着率を高める方法
eラーニングの活用事例を紹介したい
中小企業向けの低予算教育プラン`}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
          </div>

          {/* キーワード候補生成ボタン */}
          <div>
            <button
              type="button"
              onClick={onGenerateSuggestions}
              disabled={isLoadingSuggestions || !data.theme_topics}
              className={`
                inline-flex items-center px-4 py-2 text-sm font-medium rounded-md
                ${
                  isLoadingSuggestions || !data.theme_topics
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-primary-600 text-white hover:bg-primary-700"
                }
              `}
            >
              {isLoadingSuggestions ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  生成中...
                </>
              ) : (
                <>
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                  キーワード候補を生成
                </>
              )}
            </button>
          </div>

          {/* キーワード候補一覧 */}
          {suggestions && suggestions.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                キーワード候補（クリックして選択）
              </label>
              <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onSelectKeyword(suggestion)}
                    className={`
                      w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between
                      ${
                        data.selected_keyword?.keyword === suggestion.keyword
                          ? "bg-primary-50 border-l-4 border-primary-500"
                          : ""
                      }
                    `}
                  >
                    <div>
                      <span className="font-medium text-gray-900">
                        {suggestion.keyword}
                      </span>
                      <div className="mt-1 flex items-center gap-3 text-xs">
                        <span className="text-gray-500">
                          推定検索数: {suggestion.estimated_volume}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded ${
                            COMPETITION_COLORS[suggestion.estimated_competition]
                          }`}
                        >
                          競合: {COMPETITION_LABELS[suggestion.estimated_competition]}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-sm text-gray-500">
                        関連度: {Math.round(suggestion.relevance_score * 100)}%
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 選択されたキーワード */}
          {data.selected_keyword && (
            <div className="p-4 bg-primary-50 border border-primary-200 rounded-md">
              <p className="text-sm text-primary-700">
                選択されたキーワード:{" "}
                <span className="font-semibold">
                  {data.selected_keyword.keyword}
                </span>
              </p>
            </div>
          )}
        </>
      )}

      {/* 関連キーワード（任意） */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          関連キーワード（任意）
        </label>
        <p className="mt-1 text-xs text-gray-500">
          メインキーワードに関連するキーワードがあれば入力してください（1行につき1キーワード）
        </p>
        <textarea
          rows={3}
          value={
            data.related_keywords
              ?.map((rk) => `${rk.keyword}${rk.volume ? ` (${rk.volume})` : ""}`)
              .join("\n") || ""
          }
          onChange={(e) => {
            const lines = e.target.value.split("\n").filter((l) => l.trim());
            const related = lines.map((line) => {
              const match = line.match(/^(.+?)\s*(?:\(([^)]+)\))?$/);
              if (match) {
                return {
                  keyword: match[1].trim(),
                  volume: match[2]?.trim(),
                };
              }
              return { keyword: line.trim() };
            });
            onChange({ related_keywords: related.length > 0 ? related : undefined });
          }}
          placeholder={`例:
派遣社員 研修プログラム (50-100)
派遣社員 定着率向上 (100-200)`}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
      </div>
    </div>
  );
}
