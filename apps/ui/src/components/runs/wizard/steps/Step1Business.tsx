"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { BusinessInput, TargetCV, TargetAudienceSuggestion } from "@/lib/types";

interface Step1BusinessProps {
  data: BusinessInput;
  onChange: (data: Partial<BusinessInput>) => void;
  errors: string[];
}

const TARGET_CV_OPTIONS: { value: TargetCV; label: string }[] = [
  { value: "inquiry", label: "問い合わせ獲得" },
  { value: "document_request", label: "資料請求" },
  { value: "free_consultation", label: "無料相談申込" },
  { value: "other", label: "その他" },
];

export function Step1Business({ data, onChange, errors }: Step1BusinessProps) {
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [audienceSuggestions, setAudienceSuggestions] = useState<TargetAudienceSuggestion[]>([]);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  const canSuggestAudience = data.description.length >= 10 && data.target_cv;

  const handleSuggestAudience = async () => {
    if (!canSuggestAudience) return;

    setIsLoadingSuggestions(true);
    setSuggestionError(null);
    setAudienceSuggestions([]);

    try {
      const response = await api.suggestions.targetAudience({
        business_description: data.description,
        target_cv: data.target_cv,
      });
      setAudienceSuggestions(response.suggestions);
    } catch (error) {
      setSuggestionError("ターゲット読者の提案に失敗しました。再度お試しください。");
      console.error("Failed to get audience suggestions:", error);
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const handleSelectSuggestion = (suggestion: TargetAudienceSuggestion) => {
    onChange({ target_audience: suggestion.audience });
    setAudienceSuggestions([]);
  };

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

      {/* 事業内容 */}
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-gray-700"
        >
          事業内容 <span className="text-red-500">*</span>
        </label>
        <p className="mt-1 text-xs text-gray-500">
          貴社の事業内容をできる限り詳細に教えてください
        </p>
        <textarea
          id="description"
          rows={4}
          value={data.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder="例: 派遣社員向けeラーニングサービス、Indeed・求人ボックス・スタンバイといった求人広告運用支援（人材紹介領域に特化）"
          className="mt-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
      </div>

      {/* 目標CV */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          目標CV（コンバージョン） <span className="text-red-500">*</span>
        </label>
        <div className="mt-2 space-y-2">
          {TARGET_CV_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center">
              <input
                type="radio"
                name="target_cv"
                value={option.value}
                checked={data.target_cv === option.value}
                onChange={(e) =>
                  onChange({ target_cv: e.target.value as TargetCV })
                }
                className="h-4 w-4 text-primary-600 border-gray-300 focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-gray-700">{option.label}</span>
            </label>
          ))}
        </div>

        {/* その他の場合の入力欄 */}
        {data.target_cv === "other" && (
          <input
            type="text"
            value={data.target_cv_other || ""}
            onChange={(e) => onChange({ target_cv_other: e.target.value })}
            placeholder="具体的なCV目標を入力"
            className="mt-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          />
        )}
      </div>

      {/* ターゲット読者 */}
      <div>
        <div className="flex items-center justify-between">
          <label
            htmlFor="target_audience"
            className="block text-sm font-medium text-gray-700"
          >
            ターゲット読者 <span className="text-red-500">*</span>
          </label>
          <button
            type="button"
            onClick={handleSuggestAudience}
            disabled={!canSuggestAudience || isLoadingSuggestions}
            className={`
              inline-flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md
              ${
                canSuggestAudience && !isLoadingSuggestions
                  ? "bg-primary-50 text-primary-700 hover:bg-primary-100 border border-primary-200"
                  : "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
              }
            `}
            title={!canSuggestAudience ? "事業内容と目標CVを入力してください" : ""}
          >
            {isLoadingSuggestions ? (
              <>
                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
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
                <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                    clipRule="evenodd"
                  />
                </svg>
                AIで提案
              </>
            )}
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          想定する読者像を教えてください（役職、年齢層、課題など）
        </p>
        <textarea
          id="target_audience"
          rows={3}
          value={data.target_audience}
          onChange={(e) => onChange({ target_audience: e.target.value })}
          placeholder="例: 派遣会社の教育担当者、人事部長、30〜40代、派遣社員の離職率に悩んでいる"
          className="mt-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />

        {/* サジェスト候補 */}
        {audienceSuggestions.length > 0 && (
          <div className="mt-3 p-3 bg-primary-50 rounded-lg border border-primary-200">
            <p className="text-xs font-medium text-primary-700 mb-2">
              AI提案（クリックで選択）
            </p>
            <div className="space-y-2">
              {audienceSuggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectSuggestion(suggestion)}
                  className="w-full text-left p-2 bg-white rounded border border-primary-100 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <p className="text-sm text-gray-900">{suggestion.audience}</p>
                  <p className="text-xs text-gray-500 mt-1">{suggestion.rationale}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* エラー表示 */}
        {suggestionError && (
          <p className="mt-2 text-xs text-red-600">{suggestionError}</p>
        )}
      </div>

      {/* 自社の強み */}
      <div>
        <label
          htmlFor="company_strengths"
          className="block text-sm font-medium text-gray-700"
        >
          自社の強み <span className="text-red-500">*</span>
        </label>
        <p className="mt-1 text-xs text-gray-500">
          競合と比較した際の貴社の強みを教えてください
        </p>
        <textarea
          id="company_strengths"
          rows={3}
          value={data.company_strengths}
          onChange={(e) => onChange({ company_strengths: e.target.value })}
          placeholder="例: 中小企業特化、低予算での教育プラン提供、導入実績300社以上"
          className="mt-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
      </div>
    </div>
  );
}
