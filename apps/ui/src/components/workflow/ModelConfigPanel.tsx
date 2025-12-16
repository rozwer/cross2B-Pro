'use client';

import { useState } from 'react';
import {
  Settings,
  Cpu,
  Globe,
  Thermometer,
  Hash,
  ChevronDown,
  ChevronRight,
  Sparkles,
  RotateCcw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  StepAIProvider,
  WORKFLOW_STEPS,
  getProviderColor,
  getProviderLabel,
} from './workflowConfig';

// Model definitions for each provider
const GEMINI_MODELS = [
  { id: 'gemini-2.0-flash-exp', name: 'Gemini 2.0 Flash (Exp)', isDefault: true },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
  { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
];

const CLAUDE_MODELS = [
  { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', isDefault: true },
  { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus' },
  { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku' },
];

export interface ModelSettings {
  geminiModel: string;
  claudeModel: string;
  temperature: number;
  maxTokens: number;
  groundingEnabled: boolean;
}

export interface ModelConfigPanelProps {
  className?: string;
  stepProviders: Record<string, StepAIProvider>;
  modelSettings: ModelSettings;
  onStepProviderChange: (stepId: string, provider: StepAIProvider) => void;
  onModelSettingsChange: (settings: ModelSettings) => void;
  onResetToDefaults: () => void;
}

export function ModelConfigPanel({
  className,
  stepProviders,
  modelSettings,
  onStepProviderChange,
  onModelSettingsChange,
  onResetToDefaults,
}: ModelConfigPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    models: true,
    advanced: false,
    steps: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const updateModelSettings = (updates: Partial<ModelSettings>) => {
    onModelSettingsChange({ ...modelSettings, ...updates });
  };

  // Count steps by provider
  const providerCounts = WORKFLOW_STEPS.reduce(
    (acc, step) => {
      const provider = stepProviders[step.id] || step.defaultProvider;
      acc[provider] = (acc[provider] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div
      className={cn(
        'flex h-full flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 bg-gray-50/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-800">モデル設定</h2>
        </div>
        <button
          onClick={onResetToDefaults}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          title="デフォルトに戻す"
        >
          <RotateCcw className="h-3 w-3" />
          リセット
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Provider Summary */}
        <div className="border-b border-gray-100 p-4">
          <div className="mb-3 text-xs font-medium text-gray-500">使用モデル概要</div>
          <div className="grid grid-cols-2 gap-2">
            {(['gemini', 'claude', 'gemini+web', 'manual'] as StepAIProvider[]).map(
              (provider) => (
                <div
                  key={provider}
                  className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={cn('h-2.5 w-2.5 rounded-sm', getProviderColor(provider))}
                    />
                    <span className="text-xs text-gray-600">
                      {getProviderLabel(provider)}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-gray-700">
                    {providerCounts[provider] || 0}
                  </span>
                </div>
              )
            )}
          </div>
        </div>

        {/* Models Section */}
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('models')}
            className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
          >
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">
                デフォルトモデル
              </span>
            </div>
            {expandedSections.models ? (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            )}
          </button>

          {expandedSections.models && (
            <div className="space-y-4 px-4 pb-4">
              {/* Gemini Model */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-gray-600">
                  <span className="h-2 w-2 rounded-sm bg-blue-500" />
                  Gemini モデル
                </label>
                <select
                  value={modelSettings.geminiModel}
                  onChange={(e) =>
                    updateModelSettings({ geminiModel: e.target.value })
                  }
                  className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  {GEMINI_MODELS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Claude Model */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-gray-600">
                  <span className="h-2 w-2 rounded-sm bg-orange-500" />
                  Claude モデル
                </label>
                <select
                  value={modelSettings.claudeModel}
                  onChange={(e) =>
                    updateModelSettings({ claudeModel: e.target.value })
                  }
                  className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  {CLAUDE_MODELS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Advanced Settings Section */}
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('advanced')}
            className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">詳細設定</span>
            </div>
            {expandedSections.advanced ? (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            )}
          </button>

          {expandedSections.advanced && (
            <div className="space-y-4 px-4 pb-4">
              {/* Temperature */}
              <div>
                <label className="mb-1.5 flex items-center justify-between text-xs font-medium text-gray-600">
                  <span className="flex items-center gap-1.5">
                    <Thermometer className="h-3 w-3" />
                    Temperature
                  </span>
                  <span className="text-gray-500">{modelSettings.temperature}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={modelSettings.temperature}
                  onChange={(e) =>
                    updateModelSettings({ temperature: parseFloat(e.target.value) })
                  }
                  className="w-full accent-primary-500"
                />
                <div className="mt-1 flex justify-between text-[10px] text-gray-400">
                  <span>厳密</span>
                  <span>創造的</span>
                </div>
              </div>

              {/* Max Tokens */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-gray-600">
                  <Hash className="h-3 w-3" />
                  最大トークン数
                </label>
                <input
                  type="number"
                  min="1000"
                  max="128000"
                  step="1000"
                  value={modelSettings.maxTokens}
                  onChange={(e) =>
                    updateModelSettings({ maxTokens: parseInt(e.target.value) || 8000 })
                  }
                  className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>

              {/* Grounding */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-1.5 text-xs font-medium text-gray-600">
                  <Globe className="h-3 w-3" />
                  Grounding (Web検索)
                </label>
                <button
                  onClick={() =>
                    updateModelSettings({
                      groundingEnabled: !modelSettings.groundingEnabled,
                    })
                  }
                  className={cn(
                    'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                    modelSettings.groundingEnabled ? 'bg-primary-500' : 'bg-gray-200'
                  )}
                >
                  <span
                    className={cn(
                      'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                      modelSettings.groundingEnabled
                        ? 'translate-x-4'
                        : 'translate-x-0'
                    )}
                  />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Step-by-Step Configuration */}
        <div>
          <button
            onClick={() => toggleSection('steps')}
            className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
          >
            <div className="flex items-center gap-2">
              <Settings className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">
                工程別設定
              </span>
            </div>
            {expandedSections.steps ? (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            )}
          </button>

          {expandedSections.steps && (
            <div className="px-4 pb-4">
              <div className="max-h-64 space-y-2 overflow-y-auto">
                {WORKFLOW_STEPS.filter((step) => step.allowedProviders.length > 1).map(
                  (step) => (
                    <div
                      key={step.id}
                      className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2"
                    >
                      <div>
                        <div className="text-xs font-medium text-gray-700">
                          {step.label}
                        </div>
                        <div className="text-[10px] text-gray-500">
                          {step.description}
                        </div>
                      </div>
                      <select
                        value={stepProviders[step.id] || step.defaultProvider}
                        onChange={(e) =>
                          onStepProviderChange(
                            step.id,
                            e.target.value as StepAIProvider
                          )
                        }
                        className="rounded border border-gray-200 bg-white px-2 py-1 text-xs focus:border-primary-500 focus:outline-none"
                      >
                        {step.allowedProviders.map((provider) => (
                          <option key={provider} value={provider}>
                            {getProviderLabel(provider)}
                          </option>
                        ))}
                      </select>
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ModelConfigPanel;
