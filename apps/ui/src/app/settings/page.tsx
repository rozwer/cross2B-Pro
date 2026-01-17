"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Save,
  RotateCcw,
  Play,
  Settings,
  FileText,
  Search,
  Filter,
  ChevronDown,
  RefreshCw,
  Edit,
  Key,
  Github,
} from "lucide-react";
import { WORKFLOW_STEPS, type StepConfig } from "@/components/workflow";
import { ModelSettingsTab, ApiKeysTab, ModelsManagementTab, GitHubSettingsTab } from "@/components/tabs";
import { TabBar, type TabItem } from "@/components/common/TabBar";
import { Cpu } from "lucide-react";
import api from "@/lib/api";
import type { LLMPlatform, Prompt } from "@/lib/types";
import { STEP_LABELS } from "@/lib/types";
import { Loading } from "@/components/common";
import { HelpButton } from "@/components/common/HelpButton";

type SettingsTab = "models" | "prompts" | "apikeys" | "llm-models" | "github";

const TABS: TabItem[] = [
  { id: "models", label: "モデル設定", icon: <Settings className="h-4 w-4" /> },
  { id: "llm-models", label: "LLMモデル", icon: <Cpu className="h-4 w-4" /> },
  { id: "prompts", label: "プロンプト", icon: <FileText className="h-4 w-4" /> },
  { id: "apikeys", label: "APIキー", icon: <Key className="h-4 w-4" /> },
  { id: "github", label: "GitHub", icon: <Github className="h-4 w-4" /> },
];

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as SettingsTab) || "models";

  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);

  // Model settings state
  const [stepConfigs, setStepConfigs] = useState<StepConfig[]>(WORKFLOW_STEPS);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Prompts state
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [packId] = useState("default");
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [promptsError, setPromptsError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [stepFilter, setStepFilter] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Load saved model config on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem("workflow-config");
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig);
        setStepConfigs(parsed);
      } catch (e) {
        console.error("Failed to parse saved config:", e);
      }
    }
  }, []);

  // Load prompts when tab changes
  const loadPrompts = useCallback(async () => {
    setPromptsLoading(true);
    setPromptsError(null);
    try {
      const params: { pack_id?: string; step?: string } = { pack_id: packId };
      if (stepFilter) params.step = stepFilter;
      const response = await api.prompts.list(params);
      setPrompts(response.prompts);
    } catch (err) {
      setPromptsError(err instanceof Error ? err.message : "Failed to load prompts");
    } finally {
      setPromptsLoading(false);
    }
  }, [packId, stepFilter]);

  useEffect(() => {
    if (activeTab === "prompts") {
      loadPrompts();
    }
  }, [activeTab, loadPrompts]);

  // Update URL when tab changes
  const handleTabChange = (tab: string) => {
    setActiveTab(tab as SettingsTab);
    router.replace(`/settings?tab=${tab}`, { scroll: false });
  };

  // Model settings handlers
  const handleConfigChange = useCallback((stepId: string, config: Partial<StepConfig>) => {
    setStepConfigs((prev) =>
      prev.map((step) => (step.stepId === stepId ? { ...step, ...config } : step))
    );
    setHasUnsavedChanges(true);
  }, []);

  const handleSaveConfig = useCallback(() => {
    localStorage.setItem("workflow-config", JSON.stringify(stepConfigs));
    setHasUnsavedChanges(false);
  }, [stepConfigs]);

  const handleResetConfig = useCallback(() => {
    setStepConfigs(WORKFLOW_STEPS);
    localStorage.removeItem("workflow-config");
    setHasUnsavedChanges(false);
  }, []);

  const handleStartNewRun = useCallback(() => {
    handleSaveConfig();
    router.push("/settings/runs/new");
  }, [handleSaveConfig, router]);

  // Model counts
  const modelCounts = useMemo(() => {
    return stepConfigs.reduce(
      (acc, step) => {
        if (step.isConfigurable && step.stepId !== "approval") {
          acc[step.aiModel] = (acc[step.aiModel] || 0) + 1;
        }
        return acc;
      },
      {} as Record<LLMPlatform, number>
    );
  }, [stepConfigs]);

  // Prompts filtering
  const filteredPrompts = prompts.filter((prompt) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      prompt.step.toLowerCase().includes(query) ||
      prompt.content.toLowerCase().includes(query) ||
      (STEP_LABELS[prompt.step] || "").toLowerCase().includes(query)
    );
  });

  const groupedPrompts = filteredPrompts.reduce(
    (acc, prompt) => {
      if (!acc[prompt.step]) acc[prompt.step] = [];
      acc[prompt.step].push(prompt);
      return acc;
    },
    {} as Record<string, Prompt[]>
  );

  const sortedSteps = Object.keys(groupedPrompts).sort((a, b) => {
    const stepOrder = [
      "step0", "step1", "step2", "step3a", "step3b", "step3c", "step4", "step5",
      "step6", "step6_5", "step7a", "step7b", "step8", "step8_claims", "step8_verify",
      "step8_faq", "step9", "step10", "step10_html", "step10_checklist",
    ];
    return stepOrder.indexOf(a) - stepOrder.indexOf(b);
  });

  const uniqueSteps = Array.from(new Set(prompts.map((p) => p.step))).sort();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">設定</h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              モデルとプロンプトの管理
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Model tab actions */}
          {activeTab === "models" && (
            <>
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs">
                <span className="text-blue-600 dark:text-blue-400">
                  Gemini: {modelCounts.gemini || 0}
                </span>
                <span className="text-gray-400">/</span>
                <span className="text-orange-600 dark:text-orange-400">
                  Anthropic: {modelCounts.anthropic || 0}
                </span>
                <span className="text-gray-400">/</span>
                <span className="text-green-600 dark:text-green-400">
                  OpenAI: {modelCounts.openai || 0}
                </span>
              </div>
              <button
                onClick={handleResetConfig}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span className="hidden sm:inline">リセット</span>
              </button>
              <button
                onClick={handleSaveConfig}
                disabled={!hasUnsavedChanges}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                <span className="hidden sm:inline">保存</span>
                {hasUnsavedChanges && <span className="w-2 h-2 bg-yellow-400 rounded-full" />}
              </button>
            </>
          )}

          <div className="h-6 w-px bg-gray-200 dark:bg-gray-700" />

          <button
            onClick={handleStartNewRun}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            新規Run
          </button>
        </div>
      </div>

      {/* Tabs */}
      <TabBar tabs={TABS} activeTab={activeTab} onTabChange={handleTabChange} />

      {/* Tab Content */}
      {activeTab === "models" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">モデル設定</h2>
            <HelpButton helpKey="settings.models" size="sm" />
          </div>
          <ModelSettingsTab stepConfigs={stepConfigs} onConfigChange={handleConfigChange} />
        </div>
      )}

      {activeTab === "prompts" && (
        <div className="space-y-6">
          {/* Search and Filters */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
                  showFilters || stepFilter
                    ? "bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800 text-primary-700 dark:text-primary-300"
                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                }`}
              >
                <Filter className="h-4 w-4" />
                フィルター
                <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`} />
              </button>
              <button
                onClick={loadPrompts}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 ${promptsLoading ? "animate-spin" : ""}`} />
              </button>
            </div>

            {showFilters && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    工程
                  </label>
                  <select
                    value={stepFilter}
                    onChange={(e) => setStepFilter(e.target.value)}
                    className="px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">すべて</option>
                    {uniqueSteps.map((step) => (
                      <option key={step} value={step}>
                        {STEP_LABELS[step] || step}
                      </option>
                    ))}
                  </select>
                </div>
                {stepFilter && (
                  <button
                    onClick={() => setStepFilter("")}
                    className="self-end px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:underline"
                  >
                    クリア
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Error */}
          {promptsError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-sm text-red-700 dark:text-red-400">{promptsError}</p>
            </div>
          )}

          {/* Prompts List */}
          {promptsLoading ? (
            <Loading text="プロンプトを読み込み中..." />
          ) : filteredPrompts.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
                プロンプトがありません
              </h3>
            </div>
          ) : (
            <div className="space-y-6">
              {sortedSteps.map((step) => (
                <div
                  key={step}
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
                >
                  <div className="px-5 py-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      {STEP_LABELS[step] || step}
                      <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                        ({step})
                      </span>
                    </h2>
                  </div>
                  <div className="divide-y divide-gray-200 dark:divide-gray-700">
                    {groupedPrompts[step]
                      .sort((a, b) => b.version - a.version)
                      .map((prompt, index) => (
                        <div
                          key={`${prompt.step}-${index}`}
                          className="p-5 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                  バージョン {prompt.version}
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 whitespace-pre-wrap">
                                {prompt.content.slice(0, 300)}
                                {prompt.content.length > 300 && "..."}
                              </p>
                              {prompt.variables && Object.keys(prompt.variables).length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-1">
                                  {Object.keys(prompt.variables).map((varName) => (
                                    <span
                                      key={varName}
                                      className="inline-flex items-center px-2 py-0.5 text-xs font-mono bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded"
                                    >
                                      {`{{${varName}}}`}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <Link
                              href={`/settings/prompts/${encodeURIComponent(prompt.step)}`}
                              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                            >
                              <Edit className="h-4 w-4" />
                              編集
                            </Link>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "apikeys" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">APIキー設定</h2>
            <HelpButton helpKey="settings.apikeys" size="sm" />
          </div>
          <ApiKeysTab />
        </div>
      )}

      {activeTab === "llm-models" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <ModelsManagementTab />
        </div>
      )}

      {activeTab === "github" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <GitHubSettingsTab />
        </div>
      )}
    </div>
  );
}
