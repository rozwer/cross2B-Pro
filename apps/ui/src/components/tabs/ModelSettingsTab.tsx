'use client';

import { useState, useMemo } from 'react';
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
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { StepConfig } from '@/components/workflow/NodeConfigPanel';
import type { LLMPlatform } from '@/lib/types';

interface ModelSettingsTabProps {
  stepConfigs: StepConfig[];
  onConfigChange: (stepId: string, config: Partial<StepConfig>) => void;
  onBatchApply?: (platform: LLMPlatform, stepIds: string[]) => void;
}

interface ModelOption {
  id: string;
  name: string;
  description?: string;
  isDefault?: boolean;
}

const PLATFORM_MODELS: Record<LLMPlatform, ModelOption[]> = {
  gemini: [
    { id: 'gemini-3-pro', name: 'Gemini 3 Pro', description: '最新・最高性能', isDefault: true },
    { id: 'gemini-3-deep-think', name: 'Gemini 3 Deep Think', description: '深層推論' },
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', description: '高速・コスト効率' },
  ],
  openai: [
    { id: 'gpt-5.2', name: 'GPT-5.2', description: '最新・最高性能', isDefault: true },
    { id: 'gpt-5.1-thinking', name: 'GPT-5.1 Thinking', description: '推論特化' },
    { id: 'o4-mini', name: 'o4-mini', description: '推論・軽量' },
  ],
  anthropic: [
    { id: 'claude-opus-4.5', name: 'Claude Opus 4.5', description: '最新・最高性能', isDefault: true },
    { id: 'claude-sonnet-4', name: 'Claude Sonnet 4', description: 'バランス型' },
    { id: 'claude-opus-4', name: 'Claude Opus 4', description: '高精度' },
  ],
};

const PLATFORM_INFO: Record<LLMPlatform, { name: string; color: string; bgColor: string; borderColor: string; emoji: string; description: string }> = {
  gemini: {
    name: 'Gemini',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    emoji: '🔵',
    description: '分析・検索・自然な表現に強み',
  },
  anthropic: {
    name: 'Claude',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    emoji: '🟠',
    description: '構造化・統合・品質制御に強み',
  },
  openai: {
    name: 'OpenAI',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    emoji: '🟢',
    description: '汎用タスクに対応',
  },
};

type FilterPlatform = 'all' | LLMPlatform;

export function ModelSettingsTab({ stepConfigs, onConfigChange, onBatchApply }: ModelSettingsTabProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterPlatform, setFilterPlatform] = useState<FilterPlatform>('all');
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [selectedSteps, setSelectedSteps] = useState<Set<string>>(new Set());
  const [showBatchPanel, setShowBatchPanel] = useState(false);

  // Filter configurable steps only
  const configurableSteps = useMemo(() => {
    return stepConfigs.filter(step => step.isConfigurable && step.stepId !== 'approval');
  }, [stepConfigs]);

  // Apply search and platform filter
  const filteredSteps = useMemo(() => {
    return configurableSteps.filter(step => {
      const matchesSearch = searchQuery === '' ||
        step.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        step.stepId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        step.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesPlatform = filterPlatform === 'all' || step.aiModel === filterPlatform;

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
      {} as Record<LLMPlatform, number>
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

  const toggleSelect = (stepId: string) => {
    const newSelected = new Set(selectedSteps);
    if (newSelected.has(stepId)) {
      newSelected.delete(stepId);
    } else {
      newSelected.add(stepId);
    }
    setSelectedSteps(newSelected);
  };

  const selectAll = () => {
    if (selectedSteps.size === filteredSteps.length) {
      setSelectedSteps(new Set());
    } else {
      setSelectedSteps(new Set(filteredSteps.map(s => s.stepId)));
    }
  };

  const handleBatchApply = (platform: LLMPlatform) => {
    if (onBatchApply) {
      onBatchApply(platform, Array.from(selectedSteps));
    } else {
      // Default implementation
      const defaultModel = PLATFORM_MODELS[platform].find(m => m.isDefault) || PLATFORM_MODELS[platform][0];
      selectedSteps.forEach(stepId => {
        onConfigChange(stepId, {
          aiModel: platform,
          modelName: defaultModel.id,
        });
      });
    }
    setSelectedSteps(new Set());
    setShowBatchPanel(false);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {(['gemini', 'anthropic', 'openai'] as LLMPlatform[]).map(platform => {
          const info = PLATFORM_INFO[platform];
          return (
            <button
              key={platform}
              onClick={() => setFilterPlatform(filterPlatform === platform ? 'all' : platform)}
              className={cn(
                'p-4 rounded-xl border-2 transition-all text-left',
                filterPlatform === platform
                  ? `${info.bgColor} ${info.borderColor} ring-2 ring-offset-2 ring-${platform === 'gemini' ? 'blue' : platform === 'anthropic' ? 'orange' : 'green'}-200`
                  : 'bg-white border-gray-200 hover:border-gray-300'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">{info.emoji}</span>
                <h3 className={cn('font-semibold', info.color)}>{info.name}</h3>
              </div>
              <p className="text-3xl font-bold text-gray-900">{modelCounts[platform] || 0}</p>
              <p className="text-sm text-gray-500">ステップで使用</p>
              <p className="text-xs text-gray-400 mt-1">{info.description}</p>
            </button>
          );
        })}
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-4 mb-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="ステップを検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Batch Actions */}
        {selectedSteps.size > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowBatchPanel(!showBatchPanel)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              <Sparkles className="h-4 w-4" />
              一括適用 ({selectedSteps.size})
              <ChevronDown className="h-4 w-4" />
            </button>

            {showBatchPanel && (
              <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl border border-gray-200 shadow-xl z-10 p-3">
                <p className="text-xs text-gray-500 mb-3">選択したステップに一括適用</p>
                <div className="space-y-2">
                  {(['gemini', 'anthropic', 'openai'] as LLMPlatform[]).map(platform => {
                    const info = PLATFORM_INFO[platform];
                    return (
                      <button
                        key={platform}
                        onClick={() => handleBatchApply(platform)}
                        className={cn(
                          'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
                          info.bgColor,
                          'hover:opacity-80'
                        )}
                      >
                        <span>{info.emoji}</span>
                        <span className={info.color}>{info.name}に変更</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Steps List */}
      <div className="flex-1 overflow-auto">
        {/* Select All */}
        <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 border-b border-gray-200 sticky top-0">
          <input
            type="checkbox"
            checked={selectedSteps.size === filteredSteps.length && filteredSteps.length > 0}
            onChange={selectAll}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-gray-600">
            {filteredSteps.length}件のステップ
            {filterPlatform !== 'all' && ` (${PLATFORM_INFO[filterPlatform].name}でフィルタ中)`}
          </span>
        </div>

        <div className="divide-y divide-gray-100">
          {filteredSteps.map((step) => {
            const isExpanded = expandedSteps.has(step.stepId);
            const isSelected = selectedSteps.has(step.stepId);
            const platformInfo = PLATFORM_INFO[step.aiModel];
            const isRecommended = step.aiModel === step.recommendedModel;

            return (
              <div
                key={step.stepId}
                className={cn(
                  'transition-colors',
                  isSelected && 'bg-primary-50/50'
                )}
              >
                {/* Step Header */}
                <div className="flex items-center gap-4 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(step.stepId)}
                    className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-gray-900">{step.label}</h4>
                      <span className="text-xs text-gray-400">{step.stepId}</span>
                      {isRecommended && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                          <CheckCircle2 className="h-3 w-3" />
                          推奨
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 truncate">{step.description}</p>
                  </div>

                  {/* Current Model Badge */}
                  <div className={cn(
                    'flex items-center gap-2 px-3 py-1.5 rounded-lg',
                    platformInfo.bgColor,
                    platformInfo.borderColor,
                    'border'
                  )}>
                    <span>{platformInfo.emoji}</span>
                    <div className="text-right">
                      <p className={cn('text-sm font-medium', platformInfo.color)}>
                        {step.modelName}
                      </p>
                      <p className="text-xs text-gray-500">T: {step.temperature}</p>
                    </div>
                  </div>

                  {/* Expand Button */}
                  <button
                    onClick={() => toggleExpand(step.stepId)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                </div>

                {/* Expanded Config Panel */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 bg-gray-50 border-t border-gray-100">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {/* Platform Selection */}
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                          <Cpu className="inline h-3 w-3 mr-1" />
                          プラットフォーム
                        </label>
                        <div className="flex gap-1">
                          {(['gemini', 'anthropic', 'openai'] as LLMPlatform[]).map((platform) => {
                            const info = PLATFORM_INFO[platform];
                            const isActive = step.aiModel === platform;
                            return (
                              <button
                                key={platform}
                                onClick={() => {
                                  const defaultModel = PLATFORM_MODELS[platform].find(m => m.isDefault) || PLATFORM_MODELS[platform][0];
                                  onConfigChange(step.stepId, {
                                    aiModel: platform,
                                    modelName: defaultModel.id,
                                  });
                                }}
                                className={cn(
                                  'flex-1 py-2 px-2 rounded text-xs font-medium transition-all',
                                  isActive
                                    ? `${info.bgColor} ${info.color} ring-1 ring-inset ${info.borderColor}`
                                    : 'bg-white text-gray-600 hover:bg-gray-100'
                                )}
                              >
                                {info.emoji}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Model Selection */}
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                          <Settings2 className="inline h-3 w-3 mr-1" />
                          モデル
                        </label>
                        <select
                          value={step.modelName}
                          onChange={(e) => onConfigChange(step.stepId, { modelName: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                          {PLATFORM_MODELS[step.aiModel].map((model) => (
                            <option key={model.id} value={model.id}>
                              {model.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Temperature */}
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                          <Thermometer className="inline h-3 w-3 mr-1" />
                          Temperature: {step.temperature.toFixed(1)}
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="2"
                          step="0.1"
                          value={step.temperature}
                          onChange={(e) => onConfigChange(step.stepId, { temperature: parseFloat(e.target.value) })}
                          className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-400">
                          <span>厳密</span>
                          <span>創造的</span>
                        </div>
                      </div>

                      {/* Options */}
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                          オプション
                        </label>
                        <div className="space-y-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={step.grounding}
                              onChange={(e) => onConfigChange(step.stepId, { grounding: e.target.checked })}
                              className="w-3.5 h-3.5 rounded border-gray-300 text-primary-600"
                            />
                            <span className="text-xs text-gray-600">Grounding</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={step.repairEnabled}
                              onChange={(e) => onConfigChange(step.stepId, { repairEnabled: e.target.checked })}
                              className="w-3.5 h-3.5 rounded border-gray-300 text-primary-600"
                            />
                            <span className="text-xs text-gray-600 flex items-center gap-1">
                              <Wrench className="h-3 w-3" />
                              自動修正
                            </span>
                          </label>
                        </div>
                        <div className="mt-2 flex items-center gap-1">
                          <RotateCcw className="h-3 w-3 text-gray-400" />
                          <input
                            type="number"
                            min="1"
                            max="10"
                            value={step.retryLimit}
                            onChange={(e) => onConfigChange(step.stepId, { retryLimit: parseInt(e.target.value, 10) })}
                            className="w-12 px-2 py-1 border border-gray-200 rounded text-xs"
                          />
                          <span className="text-xs text-gray-500">回</span>
                        </div>
                      </div>
                    </div>

                    {/* Recommendation Note */}
                    {!isRecommended && (
                      <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-yellow-600" />
                        <p className="text-xs text-yellow-700">
                          このステップには <strong>{PLATFORM_INFO[step.recommendedModel].name}</strong> が推奨されています
                        </p>
                        <button
                          onClick={() => {
                            const defaultModel = PLATFORM_MODELS[step.recommendedModel].find(m => m.isDefault) || PLATFORM_MODELS[step.recommendedModel][0];
                            onConfigChange(step.stepId, {
                              aiModel: step.recommendedModel,
                              modelName: defaultModel.id,
                            });
                          }}
                          className="ml-auto text-xs text-yellow-700 underline hover:text-yellow-800"
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
            <Filter className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">
              {searchQuery ? '検索結果がありません' : 'フィルタに一致するステップがありません'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
