'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Settings2,
  GitBranch,
  FileOutput,
  Plus,
  List,
  Play,
  Save,
  RotateCcw,
} from 'lucide-react';
import { WORKFLOW_STEPS, type StepConfig } from '@/components/workflow';
import { TabBar, type TabItem } from '@/components/common/TabBar';
import { ModelSettingsTab } from '@/components/tabs/ModelSettingsTab';
import { GraphViewTab } from '@/components/tabs/GraphViewTab';
import { OutputApprovalTab } from '@/components/tabs/OutputApprovalTab';
import type { LLMPlatform, Run, Step } from '@/lib/types';
import { useRun } from '@/hooks/useRun';

type MainTabType = 'model' | 'graph' | 'output';

const TABS: TabItem[] = [
  { id: 'model', label: 'モデル設定', icon: <Settings2 className="h-4 w-4" /> },
  { id: 'graph', label: 'グラフビュー', icon: <GitBranch className="h-4 w-4" /> },
  { id: 'output', label: '出力・承認', icon: <FileOutput className="h-4 w-4" /> },
];

export default function Home() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<MainTabType>('model');
  const [stepConfigs, setStepConfigs] = useState<StepConfig[]>(WORKFLOW_STEPS);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [isGraphFullscreen, setIsGraphFullscreen] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Load saved config on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('workflow-config');
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig);
        setStepConfigs(parsed);
      } catch (e) {
        console.error('Failed to parse saved config:', e);
      }
    }
  }, []);

  // Get selected run data
  const { run: selectedRun, loading: runLoading } = useRun(selectedRunId || '', {
    autoFetch: !!selectedRunId,
  });

  // Handle config change
  const handleConfigChange = useCallback((stepId: string, config: Partial<StepConfig>) => {
    setStepConfigs((prev) =>
      prev.map((step) => (step.stepId === stepId ? { ...step, ...config } : step))
    );
    setHasUnsavedChanges(true);
  }, []);

  // Save config
  const handleSaveConfig = useCallback(() => {
    localStorage.setItem('workflow-config', JSON.stringify(stepConfigs));
    setHasUnsavedChanges(false);
  }, [stepConfigs]);

  // Reset to defaults
  const handleResetConfig = useCallback(() => {
    setStepConfigs(WORKFLOW_STEPS);
    localStorage.removeItem('workflow-config');
    setHasUnsavedChanges(false);
  }, []);

  // Navigate to new run
  const handleStartNewRun = useCallback(() => {
    handleSaveConfig();
    router.push('/runs/new');
  }, [handleSaveConfig, router]);

  // Handle node click in graph
  const handleGraphNodeClick = useCallback((stepId: string) => {
    // Switch to model tab and highlight the step
    setActiveTab('model');
  }, []);

  // Model counts for display
  const modelCounts = useMemo(() => {
    return stepConfigs.reduce(
      (acc, step) => {
        if (step.isConfigurable && step.stepId !== 'approval') {
          acc[step.aiModel] = (acc[step.aiModel] || 0) + 1;
        }
        return acc;
      },
      {} as Record<LLMPlatform, number>
    );
  }, [stepConfigs]);

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">SEO記事生成ワークフロー</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            モデル設定、ワークフロー確認、実行状況の管理
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Model Summary Badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs">
            <span className="text-blue-600 dark:text-blue-400">{modelCounts.gemini || 0}</span>
            <span className="text-gray-400 dark:text-gray-500">/</span>
            <span className="text-orange-600 dark:text-orange-400">{modelCounts.anthropic || 0}</span>
            <span className="text-gray-400 dark:text-gray-500">/</span>
            <span className="text-green-600 dark:text-green-400">{modelCounts.openai || 0}</span>
          </div>

          {/* Save/Reset (only in model tab) */}
          {activeTab === 'model' && (
            <>
              <button
                onClick={handleResetConfig}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                title="デフォルトに戻す"
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
                {hasUnsavedChanges && (
                  <span className="w-2 h-2 bg-yellow-400 rounded-full" />
                )}
              </button>
            </>
          )}

          <div className="h-6 w-px bg-gray-200 dark:bg-gray-700" />

          <Link
            href="/runs"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <List className="w-4 h-4" />
            実行一覧
          </Link>
          <button
            onClick={handleStartNewRun}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新規Run
          </button>
        </div>
      </div>

      {/* Tab Bar */}
      <TabBar
        tabs={TABS}
        activeTab={activeTab}
        onTabChange={(id) => setActiveTab(id as MainTabType)}
        className="mb-4"
      />

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'model' && (
          <div className="h-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 overflow-auto">
            <ModelSettingsTab
              stepConfigs={stepConfigs}
              onConfigChange={handleConfigChange}
            />
          </div>
        )}

        {activeTab === 'graph' && (
          <GraphViewTab
            stepConfigs={stepConfigs}
            onNodeClick={handleGraphNodeClick}
            runStatus={selectedRun?.status}
            runSteps={selectedRun?.steps}
            currentStep={selectedRun?.current_step ?? undefined}
            isFullscreen={isGraphFullscreen}
            onToggleFullscreen={() => setIsGraphFullscreen(!isGraphFullscreen)}
          />
        )}

        {activeTab === 'output' && (
          <OutputApprovalTab onCreateRun={handleStartNewRun} />
        )}
      </div>

      {/* Quick Tip Footer */}
      <div className="mt-4 flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
        <div className="flex items-center gap-4">
          {activeTab === 'model' && (
            <span>各ステップを展開してモデル設定を変更できます。一括適用も可能です。</span>
          )}
          {activeTab === 'graph' && (
            <span>ノードをクリックするとモデル設定タブに移動します。ミニマップでナビゲートできます。</span>
          )}
          {activeTab === 'output' && (
            <span>左のリストからRunを選択すると、工程別の出力と承認操作ができます。</span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span>
            全{stepConfigs.filter((s) => s.isConfigurable && s.stepId !== 'approval').length}
            ステップ
          </span>
          <span className="text-gray-300 dark:text-gray-600">|</span>
          <span>承認ポイント: 工程3完了後</span>
        </div>
      </div>
    </div>
  );
}
