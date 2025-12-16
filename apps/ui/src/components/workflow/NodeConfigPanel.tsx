'use client';

import { useState, useEffect } from 'react';
import { X, Sparkles, Thermometer, FileText, AlertTriangle } from 'lucide-react';
import type { WorkflowNodeData, AIProvider } from '@/lib/workflow-graph';
import { modelOptions, getProviderColor, getNodeTypeIcon } from '@/lib/workflow-graph';
import { cn } from '@/lib/utils';

interface NodeConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  grounding: boolean;
}

interface NodeConfigPanelProps {
  node: { id: string; data: WorkflowNodeData } | null;
  onClose: () => void;
  onSave: (nodeId: string, config: NodeConfig) => void;
  initialConfig?: Partial<NodeConfig>;
}

const defaultConfigs: Record<AIProvider, NodeConfig> = {
  gemini: {
    model: 'gemini-2.0-flash-exp',
    temperature: 0.7,
    maxTokens: 8192,
    grounding: false,
  },
  openai: {
    model: 'gpt-4o',
    temperature: 0.7,
    maxTokens: 8192,
    grounding: false,
  },
  claude: {
    model: 'claude-3-5-sonnet-20241022',
    temperature: 0.7,
    maxTokens: 8192,
    grounding: false,
  },
  manual: {
    model: '',
    temperature: 0,
    maxTokens: 0,
    grounding: false,
  },
  tool: {
    model: '',
    temperature: 0,
    maxTokens: 0,
    grounding: false,
  },
};

export function NodeConfigPanel({
  node,
  onClose,
  onSave,
  initialConfig,
}: NodeConfigPanelProps) {
  const [config, setConfig] = useState<NodeConfig>(
    initialConfig
      ? { ...defaultConfigs[node?.data.aiProvider || 'gemini'], ...initialConfig }
      : defaultConfigs[node?.data.aiProvider || 'gemini']
  );

  useEffect(() => {
    if (node) {
      const provider = node.data.aiProvider;
      setConfig(
        initialConfig
          ? { ...defaultConfigs[provider], ...initialConfig }
          : defaultConfigs[provider]
      );
    }
  }, [node, initialConfig]);

  if (!node) return null;

  const { data } = node;
  const colors = getProviderColor(data.aiProvider);
  const typeIcon = getNodeTypeIcon(data.nodeType);
  const models = modelOptions[data.aiProvider] || [];

  const handleSave = () => {
    onSave(node.id, config);
    onClose();
  };

  const isConfigurable = data.configurable && ['gemini', 'openai', 'claude'].includes(data.aiProvider);

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl border-l border-gray-200 z-50 overflow-y-auto animate-slide-in-right">
      {/* Header */}
      <div className={cn('p-4 border-b', colors.bg)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{typeIcon}</span>
            <div>
              <h2 className={cn('text-lg font-bold', colors.text)}>{data.label}</h2>
              <p className="text-sm text-gray-600">{data.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/50 rounded-full transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Provider Info */}
        <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
          <span className="text-xl">{colors.icon}</span>
          <div>
            <p className="text-sm font-medium text-gray-700">
              {data.aiProvider === 'gemini' && 'Google Gemini'}
              {data.aiProvider === 'openai' && 'OpenAI GPT'}
              {data.aiProvider === 'claude' && 'Anthropic Claude'}
              {data.aiProvider === 'manual' && '手動入力'}
              {data.aiProvider === 'tool' && '外部ツール'}
            </p>
            <p className="text-xs text-gray-500">
              {data.outputFile && `出力: ${data.outputFile}`}
            </p>
          </div>
        </div>

        {isConfigurable ? (
          <>
            {/* Model Selection */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <Sparkles className="h-4 w-4" />
                モデル
              </label>
              <select
                value={config.model}
                onChange={(e) => setConfig({ ...config, model: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {models.map((model) => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Temperature */}
            <div className="space-y-2">
              <label className="flex items-center justify-between text-sm font-medium text-gray-700">
                <span className="flex items-center gap-2">
                  <Thermometer className="h-4 w-4" />
                  Temperature
                </span>
                <span className="text-blue-600 font-mono">{config.temperature.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={config.temperature}
                onChange={(e) =>
                  setConfig({ ...config, temperature: parseFloat(e.target.value) })
                }
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-400">
                <span>精密</span>
                <span>創造的</span>
              </div>
            </div>

            {/* Max Tokens */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <FileText className="h-4 w-4" />
                最大トークン数
              </label>
              <input
                type="number"
                value={config.maxTokens}
                onChange={(e) =>
                  setConfig({ ...config, maxTokens: parseInt(e.target.value) || 0 })
                }
                min="100"
                max="32000"
                step="100"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Grounding (Gemini only) */}
            {data.aiProvider === 'gemini' && (
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🌐</span>
                  <div>
                    <p className="text-sm font-medium text-gray-700">Grounding</p>
                    <p className="text-xs text-gray-500">Google検索で最新情報を取得</p>
                  </div>
                </div>
                <button
                  onClick={() => setConfig({ ...config, grounding: !config.grounding })}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    config.grounding ? 'bg-blue-600' : 'bg-gray-200'
                  )}
                >
                  <span
                    className={cn(
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                      config.grounding ? 'translate-x-6' : 'translate-x-1'
                    )}
                  />
                </button>
              </div>
            )}

            {/* Actions */}
            <div className="pt-4 border-t space-y-2">
              <button
                onClick={handleSave}
                className={cn(
                  'w-full py-2.5 px-4 rounded-lg font-medium text-white transition-colors',
                  'bg-blue-600 hover:bg-blue-700'
                )}
              >
                設定を保存
              </button>
              <button
                onClick={onClose}
                className="w-full py-2.5 px-4 rounded-lg font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                キャンセル
              </button>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
            <p className="text-sm text-amber-700">
              この工程は設定変更できません。
              {data.aiProvider === 'manual' && '手動入力が必要です。'}
              {data.aiProvider === 'tool' && '外部ツールによる自動処理です。'}
            </p>
          </div>
        )}

        {/* Step Info */}
        <div className="pt-4 border-t">
          <h3 className="text-sm font-medium text-gray-700 mb-2">工程情報</h3>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">工程ID</dt>
              <dd className="font-mono text-gray-700">{data.stepName}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">タイプ</dt>
              <dd className="text-gray-700">{data.nodeType}</dd>
            </div>
            {data.outputFile && (
              <div className="flex justify-between">
                <dt className="text-gray-500">出力ファイル</dt>
                <dd className="font-mono text-gray-700 text-xs">{data.outputFile}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
