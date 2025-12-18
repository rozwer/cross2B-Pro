"use client";

import { useState, useMemo } from "react";
import {
  Cpu,
  Thermometer,
  RotateCcw,
  Wrench,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Settings2,
  Globe,
  Code,
  Brain,
  Link,
  Gauge,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ProviderLogo } from "@/components/icons/ProviderLogos";
import type { StepConfig } from "@/components/workflow/NodeConfigPanel";
import type { LLMPlatform } from "@/lib/types";

interface ModelSettingsTabProps {
  stepConfigs: StepConfig[];
  onConfigChange: (stepId: string, config: Partial<StepConfig>) => void;
}

interface ModelOption {
  id: string;
  name: string;
  description?: string;
  isDefault?: boolean;
}

// バックエンド実装に基づいたモデル一覧（apps/api/llm/）
const PLATFORM_MODELS: Record<LLMPlatform, ModelOption[]> = {
  gemini: [
    {
      id: "gemini-2.5-flash",
      name: "Gemini 2.5 Flash",
      description: "高速・コスト効率（デフォルト）",
      isDefault: true,
    },
    { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", description: "標準" },
    { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", description: "高精度" },
    { id: "gemini-3-pro-preview", name: "Gemini 3 Pro Preview", description: "最新プレビュー" },
  ],
  openai: [
    { id: "gpt-4o", name: "GPT-4o", description: "最新（デフォルト）", isDefault: true },
    { id: "gpt-4o-mini", name: "GPT-4o Mini", description: "軽量・高速" },
    { id: "gpt-4-turbo", name: "GPT-4 Turbo", description: "高精度" },
  ],
  anthropic: [
    {
      id: "claude-sonnet-4-20250514",
      name: "Claude Sonnet 4",
      description: "バランス型（デフォルト）",
      isDefault: true,
    },
    { id: "claude-opus-4-20250514", name: "Claude Opus 4", description: "最高精度" },
    { id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 Sonnet", description: "高速" },
  ],
};

const PLATFORM_INFO: Record<
  LLMPlatform,
  { name: string; color: string; bgColor: string; borderColor: string; description: string }
> = {
  gemini: {
    name: "Gemini",
    color: "text-blue-700 dark:text-blue-300",
    bgColor: "bg-blue-50 dark:bg-blue-900/30",
    borderColor: "border-blue-200 dark:border-blue-800",
    description: "Grounding・URL Context・Code Execution対応",
  },
  anthropic: {
    name: "Claude",
    color: "text-orange-700 dark:text-orange-300",
    bgColor: "bg-orange-50 dark:bg-orange-900/30",
    borderColor: "border-orange-200 dark:border-orange-800",
    description: "Extended Thinking対応",
  },
  openai: {
    name: "OpenAI",
    color: "text-green-700 dark:text-green-300",
    bgColor: "bg-green-50 dark:bg-green-900/30",
    borderColor: "border-green-200 dark:border-green-800",
    description: "Reasoning・Web Search対応",
  },
};

type FilterPlatform = "all" | LLMPlatform;

// プラットフォーム固有オプションの型定義
interface GeminiOptions {
  grounding: boolean;
  groundingThreshold: number;
  urlContext: boolean;
  codeExecution: boolean;
  thinking: boolean;
  thinkingBudget: number;
}

interface OpenAIOptions {
  reasoningEffort: "none" | "low" | "medium" | "high" | "xhigh";
  webSearch: boolean;
  verbosity: "concise" | "detailed";
}

interface AnthropicOptions {
  extendedThinking: boolean;
  thinkingBudget: number;
  effort: "low" | "medium" | "high";
}

// デフォルト値
const DEFAULT_GEMINI_OPTIONS: GeminiOptions = {
  grounding: false,
  groundingThreshold: 0.3,
  urlContext: false,
  codeExecution: false,
  thinking: true,
  thinkingBudget: 8192,
};

const DEFAULT_OPENAI_OPTIONS: OpenAIOptions = {
  reasoningEffort: "medium",
  webSearch: false,
  verbosity: "detailed",
};

const DEFAULT_ANTHROPIC_OPTIONS: AnthropicOptions = {
  extendedThinking: false,
  thinkingBudget: 1024,
  effort: "medium",
};

export function ModelSettingsTab({ stepConfigs, onConfigChange }: ModelSettingsTabProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterPlatform, setFilterPlatform] = useState<FilterPlatform>("all");
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // プラットフォーム固有オプションの状態（stepIdごとに管理）
  const [geminiOptions, setGeminiOptions] = useState<Record<string, GeminiOptions>>({});
  const [openaiOptions, setOpenaiOptions] = useState<Record<string, OpenAIOptions>>({});
  const [anthropicOptions, setAnthropicOptions] = useState<Record<string, AnthropicOptions>>({});

  // Filter configurable steps only
  const configurableSteps = useMemo(() => {
    return stepConfigs.filter((step) => step.isConfigurable && step.stepId !== "approval");
  }, [stepConfigs]);

  // Apply search and platform filter
  const filteredSteps = useMemo(() => {
    return configurableSteps.filter((step) => {
      const matchesSearch =
        searchQuery === "" ||
        step.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        step.stepId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        step.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesPlatform = filterPlatform === "all" || step.aiModel === filterPlatform;

      return matchesSearch && matchesPlatform;
    });
  }, [configurableSteps, searchQuery, filterPlatform]);

  // Model counts
  const modelCounts = useMemo(() => {
    return configurableSteps.reduce(
      (acc, step) => {
        acc[step.aiModel] = (acc[step.aiModel] || 0) + 1;
        return acc;
      },
      {} as Record<LLMPlatform, number>,
    );
  }, [configurableSteps]);

  const toggleExpand = (stepId: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  // オプション取得ヘルパー
  const getGeminiOpts = (stepId: string): GeminiOptions =>
    geminiOptions[stepId] || { ...DEFAULT_GEMINI_OPTIONS };

  const getOpenaiOpts = (stepId: string): OpenAIOptions =>
    openaiOptions[stepId] || { ...DEFAULT_OPENAI_OPTIONS };

  const getAnthropicOpts = (stepId: string): AnthropicOptions =>
    anthropicOptions[stepId] || { ...DEFAULT_ANTHROPIC_OPTIONS };

  // オプション更新ヘルパー
  const updateGeminiOpts = (stepId: string, update: Partial<GeminiOptions>) => {
    setGeminiOptions((prev) => ({
      ...prev,
      [stepId]: { ...getGeminiOpts(stepId), ...update },
    }));
  };

  const updateOpenaiOpts = (stepId: string, update: Partial<OpenAIOptions>) => {
    setOpenaiOptions((prev) => ({
      ...prev,
      [stepId]: { ...getOpenaiOpts(stepId), ...update },
    }));
  };

  const updateAnthropicOpts = (stepId: string, update: Partial<AnthropicOptions>) => {
    setAnthropicOptions((prev) => ({
      ...prev,
      [stepId]: { ...getAnthropicOpts(stepId), ...update },
    }));
  };

  // Gemini固有オプションUI
  const renderGeminiOptions = (stepId: string) => {
    const opts = getGeminiOpts(stepId);
    return (
      <div className="space-y-3">
        {/* Grounding */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={opts.grounding}
            onChange={(e) => updateGeminiOpts(stepId, { grounding: e.target.checked })}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-sm text-gray-700">Grounding (Google Search)</span>
            </div>
            <p className="text-xs text-gray-500">Web検索で最新情報を取得</p>
          </div>
        </label>

        {opts.grounding && (
          <div className="ml-7 pl-3 border-l-2 border-blue-200">
            <label className="text-xs text-gray-500 block mb-1">
              Dynamic Retrieval Threshold: {opts.groundingThreshold.toFixed(1)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={opts.groundingThreshold}
              onChange={(e) =>
                updateGeminiOpts(stepId, { groundingThreshold: parseFloat(e.target.value) })
              }
              className="w-full"
            />
          </div>
        )}

        {/* URL Context */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={opts.urlContext}
            onChange={(e) => updateGeminiOpts(stepId, { urlContext: e.target.checked })}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <Link className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-sm text-gray-700">URL Context</span>
            </div>
            <p className="text-xs text-gray-500">URLからコンテンツを取得してコンテキストに追加</p>
          </div>
        </label>

        {/* Code Execution */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={opts.codeExecution}
            onChange={(e) => updateGeminiOpts(stepId, { codeExecution: e.target.checked })}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <Code className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-sm text-gray-700">Code Execution</span>
            </div>
            <p className="text-xs text-gray-500">Pythonコードを生成・実行</p>
          </div>
        </label>

        {/* Thinking */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={opts.thinking}
            onChange={(e) => updateGeminiOpts(stepId, { thinking: e.target.checked })}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-sm text-gray-700">Thinking (Adaptive)</span>
            </div>
            <p className="text-xs text-gray-500">Gemini 2.5/3の推論機能</p>
          </div>
        </label>

        {opts.thinking && (
          <div className="ml-7 pl-3 border-l-2 border-blue-200">
            <label className="text-xs text-gray-500 block mb-1">
              Thinking Budget: {opts.thinkingBudget.toLocaleString()} tokens
            </label>
            <input
              type="range"
              min="0"
              max="24576"
              step="1024"
              value={opts.thinkingBudget}
              onChange={(e) =>
                updateGeminiOpts(stepId, { thinkingBudget: parseInt(e.target.value) })
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>無効</span>
              <span>深い推論</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  // OpenAI固有オプションUI
  const renderOpenAIOptions = (stepId: string) => {
    const opts = getOpenaiOpts(stepId);
    return (
      <div className="space-y-3">
        {/* Reasoning Effort */}
        <div>
          <label className="flex items-center gap-1.5 text-sm text-gray-700 mb-2">
            <Gauge className="w-3.5 h-3.5 text-green-600" />
            Reasoning Effort
          </label>
          <select
            value={opts.reasoningEffort}
            onChange={(e) =>
              updateOpenaiOpts(stepId, {
                reasoningEffort: e.target.value as OpenAIOptions["reasoningEffort"],
              })
            }
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            <option value="none">None (低レイテンシ)</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="xhigh">X-High (GPT-5.2+)</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">推論の深さを制御（GPT-5系向け）</p>
        </div>

        {/* Web Search */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={opts.webSearch}
            onChange={(e) => updateOpenaiOpts(stepId, { webSearch: e.target.checked })}
            className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
          />
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-green-600" />
              <span className="text-sm text-gray-700">Web Search</span>
            </div>
            <p className="text-xs text-gray-500">GPT-5系でWeb検索を有効化</p>
          </div>
        </label>

        {/* Verbosity */}
        <div>
          <label className="flex items-center gap-1.5 text-sm text-gray-700 mb-2">
            <Settings2 className="w-3.5 h-3.5 text-green-600" />
            Verbosity
          </label>
          <div className="flex gap-2">
            {(["concise", "detailed"] as const).map((level) => (
              <button
                key={level}
                onClick={() => updateOpenaiOpts(stepId, { verbosity: level })}
                className={cn(
                  "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all",
                  opts.verbosity === level
                    ? "bg-green-100 text-green-700 ring-1 ring-green-300"
                    : "bg-gray-50 text-gray-600 hover:bg-gray-100",
                )}
              >
                {level === "concise" ? "簡潔" : "詳細"}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // Anthropic固有オプションUI
  const renderAnthropicOptions = (stepId: string) => {
    const opts = getAnthropicOpts(stepId);
    return (
      <div className="space-y-3">
        {/* Extended Thinking */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={opts.extendedThinking}
            onChange={(e) => updateAnthropicOpts(stepId, { extendedThinking: e.target.checked })}
            className="w-4 h-4 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
          />
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5 text-orange-600" />
              <span className="text-sm text-gray-700">Extended Thinking</span>
            </div>
            <p className="text-xs text-gray-500">Claude 4系の拡張推論機能</p>
          </div>
        </label>

        {opts.extendedThinking && (
          <div className="ml-7 pl-3 border-l-2 border-orange-200">
            <label className="text-xs text-gray-500 block mb-1">
              Thinking Budget: {opts.thinkingBudget.toLocaleString()} tokens (最小1024)
            </label>
            <input
              type="range"
              min="1024"
              max="32768"
              step="1024"
              value={opts.thinkingBudget}
              onChange={(e) =>
                updateAnthropicOpts(stepId, { thinkingBudget: parseInt(e.target.value) })
              }
              className="w-full"
            />
          </div>
        )}

        {/* Effort Level */}
        <div>
          <label className="flex items-center gap-1.5 text-sm text-gray-700 mb-2">
            <Gauge className="w-3.5 h-3.5 text-orange-600" />
            Effort Level (Claude Opus 4.5向け)
          </label>
          <div className="flex gap-2">
            {(["low", "medium", "high"] as const).map((level) => (
              <button
                key={level}
                onClick={() => updateAnthropicOpts(stepId, { effort: level })}
                className={cn(
                  "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all",
                  opts.effort === level
                    ? "bg-orange-100 text-orange-700 ring-1 ring-orange-300"
                    : "bg-gray-50 text-gray-600 hover:bg-gray-100",
                )}
              >
                {level === "low" ? "低" : level === "medium" ? "中" : "高"}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {(["gemini", "anthropic", "openai"] as LLMPlatform[]).map((platform) => {
          const info = PLATFORM_INFO[platform];
          return (
            <button
              key={platform}
              onClick={() => setFilterPlatform(filterPlatform === platform ? "all" : platform)}
              className={cn(
                "p-4 rounded-xl border-2 transition-all text-left",
                filterPlatform === platform
                  ? `${info.bgColor} ${info.borderColor} ring-2 ring-offset-2 dark:ring-offset-gray-900 ring-${platform === "gemini" ? "blue" : platform === "anthropic" ? "orange" : "green"}-200`
                  : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600",
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <ProviderLogo platform={platform} size={28} />
                <h3 className={cn("font-semibold", info.color)}>{info.name}</h3>
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                {modelCounts[platform] || 0}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">ステップで使用</p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{info.description}</p>
            </button>
          );
        })}
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-4 mb-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="ステップを検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>
      </div>

      {/* Steps List */}
      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 sticky top-0">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {filteredSteps.length}件のステップ
            {filterPlatform !== "all" && ` (${PLATFORM_INFO[filterPlatform].name}でフィルタ中)`}
          </span>
        </div>

        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          {filteredSteps.map((step) => {
            const isExpanded = expandedSteps.has(step.stepId);
            const platformInfo = PLATFORM_INFO[step.aiModel];
            const isRecommended = step.aiModel === step.recommendedModel;

            return (
              <div key={step.stepId} className="transition-colors">
                {/* Step Header */}
                <div
                  className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
                  onClick={() => toggleExpand(step.stepId)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100">{step.label}</h4>
                      <span className="text-xs text-gray-400 dark:text-gray-500">
                        {step.stepId}
                      </span>
                      {isRecommended && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs rounded">
                          <CheckCircle2 className="h-3 w-3" />
                          推奨
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                      {step.description}
                    </p>
                  </div>

                  {/* Current Model Badge */}
                  <div
                    className={cn(
                      "flex items-center gap-2 px-3 py-1.5 rounded-lg",
                      platformInfo.bgColor,
                      platformInfo.borderColor,
                      "border",
                    )}
                  >
                    <ProviderLogo platform={step.aiModel} size={20} />
                    <div className="text-right">
                      <p className={cn("text-sm font-medium", platformInfo.color)}>
                        {step.modelName}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        T: {step.temperature}
                      </p>
                    </div>
                  </div>

                  {/* Expand Button */}
                  <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                </div>

                {/* Expanded Config Panel */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-700">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* 左カラム: 共通設定 */}
                      <div className="space-y-4">
                        <h5 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                          基本設定
                        </h5>

                        {/* Platform Selection */}
                        <div>
                          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                            <Cpu className="inline h-3 w-3 mr-1" />
                            プラットフォーム
                          </label>
                          <div className="flex gap-2">
                            {(["gemini", "anthropic", "openai"] as LLMPlatform[]).map(
                              (platform) => {
                                const info = PLATFORM_INFO[platform];
                                const isActive = step.aiModel === platform;
                                return (
                                  <button
                                    key={platform}
                                    onClick={() => {
                                      const defaultModel =
                                        PLATFORM_MODELS[platform].find((m) => m.isDefault) ||
                                        PLATFORM_MODELS[platform][0];
                                      onConfigChange(step.stepId, {
                                        aiModel: platform,
                                        modelName: defaultModel.id,
                                      });
                                    }}
                                    className={cn(
                                      "flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2",
                                      isActive
                                        ? `${info.bgColor} ${info.color} ring-2 ${info.borderColor}`
                                        : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600",
                                    )}
                                  >
                                    <ProviderLogo platform={platform} size={18} />
                                    <span className="hidden sm:inline">{info.name}</span>
                                  </button>
                                );
                              },
                            )}
                          </div>
                        </div>

                        {/* Model Selection */}
                        <div>
                          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                            <Settings2 className="inline h-3 w-3 mr-1" />
                            モデル
                          </label>
                          <select
                            value={step.modelName}
                            onChange={(e) =>
                              onConfigChange(step.stepId, { modelName: e.target.value })
                            }
                            className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          >
                            {PLATFORM_MODELS[step.aiModel].map((model) => (
                              <option key={model.id} value={model.id}>
                                {model.name} {model.description && `- ${model.description}`}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Temperature */}
                        <div>
                          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                            <Thermometer className="inline h-3 w-3 mr-1" />
                            Temperature: {step.temperature.toFixed(1)}
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={step.temperature}
                            onChange={(e) =>
                              onConfigChange(step.stepId, {
                                temperature: parseFloat(e.target.value),
                              })
                            }
                            className="w-full"
                          />
                          <div className="flex justify-between text-xs text-gray-400 dark:text-gray-500">
                            <span>厳密</span>
                            <span>創造的</span>
                          </div>
                        </div>

                        {/* Common Options */}
                        <div>
                          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                            共通オプション
                          </label>
                          <div className="space-y-2">
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={step.repairEnabled}
                                onChange={(e) =>
                                  onConfigChange(step.stepId, { repairEnabled: e.target.checked })
                                }
                                className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 bg-white dark:bg-gray-700"
                              />
                              <span className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-1">
                                <Wrench className="h-3.5 w-3.5" />
                                自動修正（決定的修正のみ）
                              </span>
                            </label>
                            <div className="flex items-center gap-2">
                              <RotateCcw className="h-3.5 w-3.5 text-gray-400 dark:text-gray-500" />
                              <span className="text-sm text-gray-600 dark:text-gray-300">
                                リトライ上限:
                              </span>
                              <input
                                type="number"
                                min="1"
                                max="10"
                                value={step.retryLimit}
                                onChange={(e) =>
                                  onConfigChange(step.stepId, {
                                    retryLimit: parseInt(e.target.value, 10),
                                  })
                                }
                                className="w-16 px-2 py-1 border border-gray-200 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                              />
                              <span className="text-sm text-gray-500 dark:text-gray-400">回</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 右カラム: プラットフォーム固有オプション */}
                      <div className="space-y-4">
                        <h5 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide flex items-center gap-2">
                          <ProviderLogo platform={step.aiModel} size={14} />
                          {PLATFORM_INFO[step.aiModel].name}固有オプション
                        </h5>

                        <div
                          className={cn(
                            "p-4 rounded-lg border",
                            step.aiModel === "gemini" &&
                              "bg-blue-50/50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
                            step.aiModel === "openai" &&
                              "bg-green-50/50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
                            step.aiModel === "anthropic" &&
                              "bg-orange-50/50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800",
                          )}
                        >
                          {step.aiModel === "gemini" && renderGeminiOptions(step.stepId)}
                          {step.aiModel === "openai" && renderOpenAIOptions(step.stepId)}
                          {step.aiModel === "anthropic" && renderAnthropicOptions(step.stepId)}
                        </div>
                      </div>
                    </div>

                    {/* Recommendation Note */}
                    {!isRecommended && (
                      <div className="mt-4 flex items-center gap-2 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                        <p className="text-xs text-yellow-700 dark:text-yellow-300">
                          このステップには{" "}
                          <strong>{PLATFORM_INFO[step.recommendedModel].name}</strong>{" "}
                          が推奨されています
                        </p>
                        <button
                          onClick={() => {
                            const defaultModel =
                              PLATFORM_MODELS[step.recommendedModel].find((m) => m.isDefault) ||
                              PLATFORM_MODELS[step.recommendedModel][0];
                            onConfigChange(step.stepId, {
                              aiModel: step.recommendedModel,
                              modelName: defaultModel.id,
                            });
                          }}
                          className="ml-auto text-xs text-yellow-700 dark:text-yellow-300 underline hover:text-yellow-800 dark:hover:text-yellow-200"
                        >
                          推奨に戻す
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {filteredSteps.length === 0 && (
          <div className="p-12 text-center">
            <Filter className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">
              {searchQuery ? "検索結果がありません" : "フィルタに一致するステップがありません"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
