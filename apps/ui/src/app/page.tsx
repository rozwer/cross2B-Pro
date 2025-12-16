'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus, List, Play, Settings } from 'lucide-react';
import { WorkflowGraph, type StepConfig, WORKFLOW_STEPS } from '@/components/workflow';
import type { LLMPlatform } from '@/lib/types';

export default function Home() {
  const router = useRouter();
  const [stepConfigs, setStepConfigs] = useState<StepConfig[]>(WORKFLOW_STEPS);
  const [activeTab, setActiveTab] = useState<'workflow' | 'config'>('workflow');

  const handleConfigSave = (configs: StepConfig[]) => {
    setStepConfigs(configs);
    // Could persist to localStorage or pass to run creation
    localStorage.setItem('workflow-config', JSON.stringify(configs));
  };

  const handleStartNewRun = () => {
    // Save current configs before navigating
    localStorage.setItem('workflow-config', JSON.stringify(stepConfigs));
    router.push('/runs/new');
  };

  // Count models by platform
  const modelCounts = stepConfigs.reduce(
    (acc, step) => {
      if (step.isConfigurable && step.stepId !== 'approval') {
        acc[step.aiModel] = (acc[step.aiModel] || 0) + 1;
      }
      return acc;
    },
    {} as Record<LLMPlatform, number>
  );

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ワークフロー設定</h1>
          <p className="text-sm text-gray-500 mt-1">
            SEO記事生成の工程フローを確認・カスタマイズできます
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/runs"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <List className="w-4 h-4" />
            実行一覧
          </Link>
          <button
            onClick={handleStartNewRun}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新規Run作成
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-gray-200 mb-4">
        <button
          onClick={() => setActiveTab('workflow')}
          className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'workflow'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <Play className="w-4 h-4" />
            ワークフロー
          </span>
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'config'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            設定概要
          </span>
        </button>
      </div>

      {activeTab === 'workflow' ? (
        /* Workflow Graph */
        <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden">
          <WorkflowGraph onConfigSave={handleConfigSave} />
        </div>
      ) : (
        /* Config Summary */
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {/* Gemini */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🔵</span>
                <h3 className="font-semibold text-blue-800">Gemini</h3>
              </div>
              <p className="text-2xl font-bold text-blue-900">{modelCounts.gemini || 0}</p>
              <p className="text-sm text-blue-700">ステップで使用</p>
              <p className="text-xs text-blue-600 mt-2">分析・検索・自然な表現</p>
            </div>
            {/* Claude */}
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🟠</span>
                <h3 className="font-semibold text-orange-800">Claude</h3>
              </div>
              <p className="text-2xl font-bold text-orange-900">{modelCounts.anthropic || 0}</p>
              <p className="text-sm text-orange-700">ステップで使用</p>
              <p className="text-xs text-orange-600 mt-2">構造化・統合・品質制御</p>
            </div>
            {/* OpenAI */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🟢</span>
                <h3 className="font-semibold text-green-800">OpenAI</h3>
              </div>
              <p className="text-2xl font-bold text-green-900">{modelCounts.openai || 0}</p>
              <p className="text-sm text-green-700">ステップで使用</p>
              <p className="text-xs text-green-600 mt-2">汎用タスク</p>
            </div>
          </div>

          {/* Step Config Table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ステップ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    説明
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    モデル
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Temperature
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    オプション
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {stepConfigs
                  .filter((step) => step.stepId !== 'approval' && step.isConfigurable)
                  .map((step) => (
                    <tr key={step.stepId} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {step.label}
                        <span className="block text-xs text-gray-500">{step.stepId}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{step.description}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${
                            step.aiModel === 'gemini'
                              ? 'bg-blue-100 text-blue-700'
                              : step.aiModel === 'anthropic'
                                ? 'bg-orange-100 text-orange-700'
                                : 'bg-green-100 text-green-700'
                          }`}
                        >
                          {step.aiModel === 'gemini' && '🔵'}
                          {step.aiModel === 'anthropic' && '🟠'}
                          {step.aiModel === 'openai' && '🟢'}
                          {step.modelName}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{step.temperature}</td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex flex-wrap gap-1">
                          {step.grounding && (
                            <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                              Grounding
                            </span>
                          )}
                          {step.repairEnabled && (
                            <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                              自動修正
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mt-4 flex items-center justify-between text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
        <div className="flex items-center gap-4">
          <span>
            💡 ノードをクリックするとモデル設定を変更できます
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs">
            全{stepConfigs.filter((s) => s.isConfigurable && s.stepId !== 'approval').length}
            ステップ
          </span>
          <span className="text-gray-300">|</span>
          <span className="text-xs">承認ポイント: 工程3完了後</span>
        </div>
      </div>
    </div>
  );
}
