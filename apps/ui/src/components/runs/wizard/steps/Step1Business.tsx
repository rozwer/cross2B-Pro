"use client";

import { BusinessInput, TargetCV } from "@/lib/types";

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
        <label
          htmlFor="target_audience"
          className="block text-sm font-medium text-gray-700"
        >
          ターゲット読者 <span className="text-red-500">*</span>
        </label>
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
