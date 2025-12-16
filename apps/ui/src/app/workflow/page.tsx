'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Play, Save, FileDown, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  WorkflowGraph,
  ModelConfigPanel,
  WORKFLOW_STEPS,
  StepAIProvider,
  ModelSettings,
} from '@/components/workflow';

// Default model settings
const DEFAULT_MODEL_SETTINGS: ModelSettings = {
  geminiModel: 'gemini-2.0-flash-exp',
  claudeModel: 'claude-3-5-sonnet-20241022',
  temperature: 0.7,
  maxTokens: 8000,
  groundingEnabled: true,
};

// Initialize step providers from workflow config defaults
function getDefaultStepProviders(): Record<string, StepAIProvider> {
  const providers: Record<string, StepAIProvider> = {};
  WORKFLOW_STEPS.forEach((step) => {
    providers[step.id] = step.defaultProvider;
  });
  return providers;
}

export default function WorkflowPage() {
  const router = useRouter();

  // State for step providers and model settings
  const [stepProviders, setStepProviders] = useState<Record<string, StepAIProvider>>(
    getDefaultStepProviders
  );
  const [modelSettings, setModelSettings] = useState<ModelSettings>(
    DEFAULT_MODEL_SETTINGS
  );
  const [showInfo, setShowInfo] = useState(false);

  // Handler for step provider changes (from graph or panel)
  const handleStepProviderChange = useCallback(
    (stepId: string, provider: StepAIProvider) => {
      setStepProviders((prev) => ({
        ...prev,
        [stepId]: provider,
      }));
    },
    []
  );

  // Handler for model settings changes
  const handleModelSettingsChange = useCallback((settings: ModelSettings) => {
    setModelSettings(settings);
  }, []);

  // Reset to defaults
  const handleResetToDefaults = useCallback(() => {
    setStepProviders(getDefaultStepProviders());
    setModelSettings(DEFAULT_MODEL_SETTINGS);
  }, []);

  // Navigate to new run with current configuration
  const handleStartRun = useCallback(() => {
    // Store configuration in sessionStorage for the new run page
    const config = {
      stepProviders,
      modelSettings,
    };
    sessionStorage.setItem('workflowConfig', JSON.stringify(config));
    router.push('/runs/new');
  }, [stepProviders, modelSettings, router]);

  // Export configuration as JSON
  const handleExportConfig = useCallback(() => {
    const config = {
      stepProviders,
      modelSettings,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'workflow-config.json';
    a.click();
    URL.revokeObjectURL(url);
  }, [stepProviders, modelSettings]);

  return (
    <div className="flex h-[calc(100vh-10rem)] gap-4">
      {/* Main Graph Area */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {/* Graph Header */}
        <div className="flex items-center justify-between border-b border-gray-100 bg-gray-50/50 px-4 py-3">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              ワークフローエディタ
            </h1>
            <p className="text-xs text-gray-500">
              各工程のAIモデルを設定してワークフローをカスタマイズ
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInfo(!showInfo)}
              className={cn(
                'rounded-lg p-2 transition-colors',
                showInfo
                  ? 'bg-primary-100 text-primary-600'
                  : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              )}
              title="ヘルプ"
            >
              <Info className="h-4 w-4" />
            </button>
            <button
              onClick={handleExportConfig}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-800"
              title="設定をエクスポート"
            >
              <FileDown className="h-4 w-4" />
              <span className="hidden sm:inline">エクスポート</span>
            </button>
            <button
              onClick={handleStartRun}
              className="btn btn-primary flex items-center gap-1.5"
            >
              <Play className="h-4 w-4" />
              実行開始
            </button>
          </div>
        </div>

        {/* Info Banner */}
        {showInfo && (
          <div className="border-b border-blue-100 bg-blue-50 px-4 py-3">
            <div className="flex items-start gap-3">
              <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500" />
              <div className="text-sm text-blue-800">
                <p className="font-medium">使い方</p>
                <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-blue-700">
                  <li>各ノードをクリックしてAIモデルを切り替え</li>
                  <li>右側のパネルでデフォルトモデルを設定</li>
                  <li>
                    <span className="inline-flex items-center gap-1">
                      <span className="flex h-3 w-3 items-center justify-center rounded-full bg-blue-500 text-[8px] font-bold text-white">
                        P
                      </span>
                      は並列処理を示します
                    </span>
                  </li>
                  <li>黄色枠のノードは承認待ちポイントです</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Graph */}
        <div className="flex-1">
          <WorkflowGraph
            stepProviders={stepProviders}
            onProviderChange={handleStepProviderChange}
          />
        </div>
      </div>

      {/* Configuration Panel */}
      <div className="w-80 flex-shrink-0">
        <ModelConfigPanel
          className="h-full"
          stepProviders={stepProviders}
          modelSettings={modelSettings}
          onStepProviderChange={handleStepProviderChange}
          onModelSettingsChange={handleModelSettingsChange}
          onResetToDefaults={handleResetToDefaults}
        />
      </div>
    </div>
  );
}
