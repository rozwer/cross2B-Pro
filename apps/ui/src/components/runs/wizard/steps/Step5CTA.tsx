"use client";

import {
  CTAInput,
  CTAPositionMode,
  SingleCTA,
  StagedCTA,
  StagedCTAItem,
} from "@/lib/types";
import { HelpButton } from "@/components/common/HelpButton";

interface Step5CTAProps {
  data: CTAInput;
  onChange: (data: Partial<CTAInput>) => void;
  errors: string[];
}

const CTA_POSITION_OPTIONS: {
  value: CTAPositionMode;
  label: string;
  description: string;
}[] = [
  {
    value: "fixed",
    label: "固定位置",
    description: "Early: 650字, Mid: 2,800字, Final: 記事末尾",
  },
  {
    value: "ratio",
    label: "比率で動的計算",
    description: "全体の約8%, 35%, 末尾に自動配置",
  },
  {
    value: "ai",
    label: "AIにお任せ",
    description: "記事の流れを見て自然な位置に配置",
  },
];

const DEFAULT_SINGLE_CTA: SingleCTA = {
  url: "https://cross-learning.jp/",
  text: "クロスラーニングの詳細を見る",
  description: "クロスラーニング広報サイトのTOPページ",
};

const DEFAULT_STAGED_CTA: StagedCTA = {
  early: {
    url: "",
    text: "",
    description: "",
    position: 650,
  },
  mid: {
    url: "",
    text: "",
    description: "",
    position: 2800,
  },
  final: {
    url: "",
    text: "",
    description: "",
  },
};

export function Step5CTA({ data, onChange, errors }: Step5CTAProps) {
  const updateSingleCTA = (updates: Partial<SingleCTA>) => {
    onChange({
      single: {
        ...(data.single || DEFAULT_SINGLE_CTA),
        ...updates,
      },
    });
  };

  const updateStagedCTA = (
    phase: "early" | "mid" | "final",
    updates: Partial<StagedCTAItem>
  ) => {
    const current = data.staged || DEFAULT_STAGED_CTA;
    onChange({
      staged: {
        ...current,
        [phase]: {
          ...current[phase],
          ...updates,
        },
      },
    });
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

      {/* CTAタイプ選択 */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          <span className="inline-flex items-center gap-1">
            CTA設計のタイプ <span className="text-red-500">*</span>
            <HelpButton helpKey="wizard.step5.cta" size="sm" />
          </span>
        </label>

        <div className="mt-4 space-y-3">
          {/* 単一CTA */}
          <label
            className={`
              relative flex cursor-pointer rounded-lg border p-4
              ${
                data.type === "single"
                  ? "border-primary-500 bg-primary-50"
                  : "border-gray-200 hover:border-gray-300"
              }
            `}
          >
            <input
              type="radio"
              name="cta_type"
              value="single"
              checked={data.type === "single"}
              onChange={() =>
                onChange({
                  type: "single",
                  single: data.single || DEFAULT_SINGLE_CTA,
                })
              }
              className="sr-only"
            />
            <div className="flex flex-1 items-center justify-between">
              <div>
                <span className="block text-sm font-medium text-gray-900">
                  ①単一CTA（推奨）
                </span>
                <span className="mt-1 text-xs text-gray-500">
                  全てのCTA（Early/Mid/Final）で同じURLとテキストを使用。最もシンプルで効果的。
                </span>
              </div>
              {data.type === "single" && (
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

          {/* 段階的CTA */}
          <label
            className={`
              relative flex cursor-pointer rounded-lg border p-4
              ${
                data.type === "staged"
                  ? "border-primary-500 bg-primary-50"
                  : "border-gray-200 hover:border-gray-300"
              }
            `}
          >
            <input
              type="radio"
              name="cta_type"
              value="staged"
              checked={data.type === "staged"}
              onChange={() =>
                onChange({
                  type: "staged",
                  staged: data.staged || DEFAULT_STAGED_CTA,
                })
              }
              className="sr-only"
            />
            <div className="flex flex-1 items-center justify-between">
              <div>
                <span className="block text-sm font-medium text-gray-900">
                  ②段階的CTA（高度）
                </span>
                <span className="mt-1 text-xs text-gray-500">
                  Early/Mid/Final で異なるURLやテキストを使用。段階的な誘導戦略。
                </span>
              </div>
              {data.type === "staged" && (
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
        </div>
      </div>

      {/* CTA挿入位置モード */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          CTA挿入位置モード <span className="text-red-500">*</span>
        </label>
        <div className="mt-2 flex gap-2 flex-wrap">
          {CTA_POSITION_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange({ position_mode: option.value })}
              className={`
                px-3 py-2 text-sm rounded-md border
                ${
                  data.position_mode === option.value
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                }
              `}
              title={option.description}
            >
              {option.label}
            </button>
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-500">
          {CTA_POSITION_OPTIONS.find((o) => o.value === data.position_mode)?.description}
        </p>
      </div>

      {/* 単一CTA設定 */}
      {data.type === "single" && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700">CTA設定</h4>

          <div>
            <label className="block text-xs font-medium text-gray-600">
              CTA URL <span className="text-red-500">*</span>
            </label>
            <input
              type="url"
              value={data.single?.url || DEFAULT_SINGLE_CTA.url}
              onChange={(e) => updateSingleCTA({ url: e.target.value })}
              placeholder="https://example.com/contact"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">
              CTAテキスト <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={data.single?.text || DEFAULT_SINGLE_CTA.text}
              onChange={(e) => updateSingleCTA({ text: e.target.value })}
              placeholder="クロスラーニングの詳細を見る"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">
              誘導先の説明
            </label>
            <textarea
              rows={2}
              value={data.single?.description || DEFAULT_SINGLE_CTA.description}
              onChange={(e) => updateSingleCTA({ description: e.target.value })}
              placeholder="クロスラーニング広報サイトのTOPページ"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
          </div>
        </div>
      )}

      {/* 段階的CTA設定 */}
      {data.type === "staged" && (
        <div className="space-y-6">
          {(["early", "mid", "final"] as const).map((phase) => {
            const phaseLabels = {
              early: { name: "Early CTA", position: "650字前後" },
              mid: { name: "Mid CTA", position: "2,800字前後" },
              final: { name: "Final CTA", position: "記事末尾" },
            };
            const current = data.staged?.[phase] || DEFAULT_STAGED_CTA[phase];

            return (
              <div key={phase} className="p-4 bg-gray-50 rounded-lg">
                <h4 className="text-sm font-medium text-gray-700">
                  {phaseLabels[phase].name}（{phaseLabels[phase].position}）
                </h4>

                <div className="mt-3 space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600">
                      URL <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="url"
                      value={current.url}
                      onChange={(e) =>
                        updateStagedCTA(phase, { url: e.target.value })
                      }
                      placeholder="https://example.com/"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600">
                      テキスト <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={current.text}
                      onChange={(e) =>
                        updateStagedCTA(phase, { text: e.target.value })
                      }
                      placeholder="CTAテキスト"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600">
                      説明
                    </label>
                    <textarea
                      rows={2}
                      value={current.description}
                      onChange={(e) =>
                        updateStagedCTA(phase, { description: e.target.value })
                      }
                      placeholder="誘導先の説明"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
