"use client";

import { X, Cpu, Thermometer, RotateCcw, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LLMPlatform } from "@/lib/types";

export interface StepConfig {
  stepId: string;
  label: string;
  description: string;
  aiModel: LLMPlatform;
  modelName: string;
  temperature: number;
  grounding: boolean;
  retryLimit: number;
  repairEnabled: boolean;
  isConfigurable: boolean;
  recommendedModel: LLMPlatform;
}

interface NodeConfigPanelProps {
  step: StepConfig | null;
  onClose: () => void;
  onConfigChange: (stepId: string, config: Partial<StepConfig>) => void;
}

interface ModelOption {
  id: string;
  name: string;
  description?: string;
  isDefault?: boolean;
}

const PLATFORM_MODELS: Record<LLMPlatform, ModelOption[]> = {
  gemini: [
    { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", description: "高速・コスト効率", isDefault: true },
    { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", description: "高精度" },
    { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", description: "標準" },
    { id: "gemini-3.0-pro", name: "Gemini 3.0 Pro", description: "最新・最高性能" },
    { id: "gemini-3-pro-latest", name: "Gemini 3 Pro Latest", description: "最新安定版" },
    { id: "gemini-3-pro-preview-11-2025", name: "Gemini 3 Pro Preview", description: "最新プレビュー" },
    { id: "gemini-3-flash-preview", name: "Gemini 3 Flash Preview", description: "最新高速プレビュー" },
    { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro", description: "安定版" },
    { id: "gemini-1.5-flash", name: "Gemini 1.5 Flash", description: "軽量" },
  ],
  openai: [
    { id: "gpt-5.2", name: "GPT-5.2", description: "最新・最高性能", isDefault: true },
    { id: "gpt-5.2-pro", name: "GPT-5.2 Pro", description: "最高精度" },
    { id: "gpt-4o", name: "GPT-4o", description: "高性能" },
    { id: "gpt-4o-mini", name: "GPT-4o Mini", description: "軽量・高速" },
    { id: "gpt-4-turbo", name: "GPT-4 Turbo", description: "安定版" },
  ],
  anthropic: [
    {
      id: "claude-sonnet-4-5-20250929",
      name: "Claude Sonnet 4.5",
      description: "最新バランス型",
      isDefault: true,
    },
    { id: "claude-opus-4-5-20251101", name: "Claude Opus 4.5", description: "最新・最高精度" },
    { id: "claude-sonnet-4-20250514", name: "Claude Sonnet 4", description: "バランス型" },
    { id: "claude-opus-4-20250514", name: "Claude Opus 4", description: "高精度" },
    { id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 Sonnet", description: "高速" },
  ],
};

const PLATFORM_LABELS: Record<LLMPlatform, { name: string; color: string; emoji: string }> = {
  gemini: { name: "Gemini", color: "bg-blue-500", emoji: "🔵" },
  anthropic: { name: "Claude", color: "bg-orange-500", emoji: "🟠" },
  openai: { name: "OpenAI", color: "bg-green-500", emoji: "🟢" },
};

export function NodeConfigPanel({ step, onClose, onConfigChange }: NodeConfigPanelProps) {
  if (!step) return null;

  const handlePlatformChange = (platform: LLMPlatform) => {
    const defaultModel =
      PLATFORM_MODELS[platform].find((m) => m.isDefault) || PLATFORM_MODELS[platform][0];
    onConfigChange(step.stepId, {
      aiModel: platform,
      modelName: defaultModel.id,
    });
  };

  return (
    <div className="w-80 bg-white border-l border-gray-200 h-full overflow-y-auto shadow-xl">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">{step.label}</h3>
          <p className="text-xs text-gray-500">{step.stepId}</p>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-md transition-colors">
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Description */}
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">説明</label>
          <p className="mt-1 text-sm text-gray-700">{step.description}</p>
        </div>

        {/* Recommended Model */}
        {step.recommendedModel && (
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <Cpu className="w-3 h-3" />
              推奨モデル
            </div>
            <span
              className={cn(
                "text-sm font-medium",
                step.recommendedModel === "gemini" && "text-blue-700",
                step.recommendedModel === "anthropic" && "text-orange-700",
                step.recommendedModel === "openai" && "text-green-700",
              )}
            >
              {PLATFORM_LABELS[step.recommendedModel].emoji}{" "}
              {PLATFORM_LABELS[step.recommendedModel].name}
            </span>
          </div>
        )}

        {step.isConfigurable ? (
          <>
            {/* Platform Selection */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                プラットフォーム
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["gemini", "anthropic", "openai"] as LLMPlatform[]).map((platform) => (
                  <button
                    key={platform}
                    onClick={() => handlePlatformChange(platform)}
                    className={cn(
                      "py-2 px-3 rounded-lg text-xs font-medium transition-all border-2",
                      step.aiModel === platform
                        ? cn("text-white border-transparent", PLATFORM_LABELS[platform].color)
                        : "bg-white text-gray-700 border-gray-200 hover:border-gray-300",
                    )}
                  >
                    {PLATFORM_LABELS[platform].emoji}
                    <br />
                    {PLATFORM_LABELS[platform].name}
                  </button>
                ))}
              </div>
            </div>

            {/* Model Selection */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                モデル
              </label>
              <select
                value={step.modelName}
                onChange={(e) => onConfigChange(step.stepId, { modelName: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {PLATFORM_MODELS[step.aiModel].map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} {model.description && `- ${model.description}`}
                  </option>
                ))}
              </select>
              {/* Model description */}
              {(() => {
                const selectedModel = PLATFORM_MODELS[step.aiModel].find(
                  (m) => m.id === step.modelName,
                );
                return (
                  selectedModel?.description && (
                    <p className="mt-1.5 text-xs text-gray-500">{selectedModel.description}</p>
                  )
                );
              })()}
            </div>

            {/* Temperature */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center gap-1 mb-2">
                <Thermometer className="w-3 h-3" />
                Temperature: {step.temperature.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={step.temperature}
                onChange={(e) =>
                  onConfigChange(step.stepId, { temperature: parseFloat(e.target.value) })
                }
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>厳密</span>
                <span>創造的</span>
              </div>
            </div>

            {/* Options */}
            <div className="space-y-3">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block">
                オプション
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={step.grounding}
                  onChange={(e) => onConfigChange(step.stepId, { grounding: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <div>
                  <span className="text-sm text-gray-700">Grounding</span>
                  <p className="text-xs text-gray-500">Web検索で最新情報を取得</p>
                </div>
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={step.repairEnabled}
                  onChange={(e) => onConfigChange(step.stepId, { repairEnabled: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <div className="flex items-center gap-1.5">
                  <Wrench className="w-3 h-3 text-gray-500" />
                  <span className="text-sm text-gray-700">自動修正</span>
                </div>
              </label>
            </div>

            {/* Retry Limit */}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center gap-1 mb-2">
                <RotateCcw className="w-3 h-3" />
                リトライ上限
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={step.retryLimit}
                onChange={(e) =>
                  onConfigChange(step.stepId, { retryLimit: parseInt(e.target.value, 10) })
                }
                className="w-20 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
            この工程は設定変更できません
          </div>
        )}
      </div>
    </div>
  );
}
