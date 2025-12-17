'use client';

import { useState } from 'react';
import type { Step } from '@/lib/types';
import {
  WorkflowPattern1_N8nStyle,
  WorkflowPattern4_VerticalTimeline,
  WorkflowPattern5_RadialProgress,
  WorkflowProgressView,
} from '@/components/workflow';

// Mock data for demonstration
const MOCK_STEPS: Step[] = [
  { id: '1', run_id: 'run1', step_name: 'step-1', status: 'completed', attempts: [], started_at: '2024-01-01T10:00:00Z', completed_at: '2024-01-01T10:00:05Z' },
  { id: '2', run_id: 'run1', step_name: 'step0', status: 'completed', attempts: [], started_at: '2024-01-01T10:00:05Z', completed_at: '2024-01-01T10:00:10Z' },
  { id: '3', run_id: 'run1', step_name: 'step1', status: 'completed', attempts: [], started_at: '2024-01-01T10:00:10Z', completed_at: '2024-01-01T10:00:30Z' },
  { id: '4', run_id: 'run1', step_name: 'step2', status: 'completed', attempts: [], started_at: '2024-01-01T10:00:30Z', completed_at: '2024-01-01T10:01:00Z' },
  { id: '5', run_id: 'run1', step_name: 'step3', status: 'completed', attempts: [], started_at: '2024-01-01T10:01:00Z', completed_at: '2024-01-01T10:01:30Z' },
  { id: '6', run_id: 'run1', step_name: 'step3a', status: 'completed', attempts: [], started_at: '2024-01-01T10:01:30Z', completed_at: '2024-01-01T10:02:00Z' },
  { id: '7', run_id: 'run1', step_name: 'step3b', status: 'completed', attempts: [], started_at: '2024-01-01T10:01:30Z', completed_at: '2024-01-01T10:02:10Z' },
  { id: '8', run_id: 'run1', step_name: 'step3c', status: 'running', attempts: [{ id: 'a1', step_id: '8', attempt_num: 1, status: 'running', started_at: '2024-01-01T10:01:30Z' }], started_at: '2024-01-01T10:01:30Z' },
  { id: '9', run_id: 'run1', step_name: 'step4', status: 'pending', attempts: [] },
  { id: '10', run_id: 'run1', step_name: 'step5', status: 'pending', attempts: [] },
  { id: '11', run_id: 'run1', step_name: 'step6', status: 'pending', attempts: [] },
  { id: '12', run_id: 'run1', step_name: 'step6.5', status: 'pending', attempts: [] },
  { id: '13', run_id: 'run1', step_name: 'step7a', status: 'pending', attempts: [] },
  { id: '14', run_id: 'run1', step_name: 'step7b', status: 'pending', attempts: [] },
  { id: '15', run_id: 'run1', step_name: 'step8', status: 'pending', attempts: [] },
  { id: '16', run_id: 'run1', step_name: 'step9', status: 'pending', attempts: [] },
  { id: '17', run_id: 'run1', step_name: 'step10', status: 'pending', attempts: [] },
];

const MOCK_STEPS_WAITING: Step[] = MOCK_STEPS.map(s => ({
  ...s,
  status: ['step-1', 'step0', 'step1', 'step2', 'step3', 'step3a', 'step3b', 'step3c', 'step4', 'step5'].includes(s.step_name)
    ? 'completed' as const
    : s.step_name === 'step6' ? 'running' as const : 'pending' as const,
}));

type ViewMode = 'all' | 'integrated';

export default function WorkflowPatternsPage() {
  const [scenario, setScenario] = useState<'running' | 'waiting'>('running');
  const [viewMode, setViewMode] = useState<ViewMode>('integrated');

  const steps = scenario === 'running' ? MOCK_STEPS : MOCK_STEPS_WAITING;
  const currentStep = scenario === 'running' ? 'step3c' : 'step6';
  const waitingApproval = scenario === 'waiting';

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            ワークフロー UI パターン
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            採用パターン: n8n / タイムライン / ラジアル（切り替え可能）
          </p>

          {/* Controls */}
          <div className="flex flex-wrap items-center gap-4 mb-4">
            {/* View Mode */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">表示:</span>
              <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
                <button
                  onClick={() => setViewMode('integrated')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    viewMode === 'integrated'
                      ? 'bg-violet-600 text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  統合ビュー
                </button>
                <button
                  onClick={() => setViewMode('all')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    viewMode === 'all'
                      ? 'bg-violet-600 text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  全パターン
                </button>
              </div>
            </div>

            {/* Scenario Toggle */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">シナリオ:</span>
              <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
                <button
                  onClick={() => setScenario('running')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    scenario === 'running'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  実行中
                </button>
                <button
                  onClick={() => setScenario('waiting')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    scenario === 'waiting'
                      ? 'bg-amber-600 text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  承認待ち
                </button>
              </div>
            </div>
          </div>

          {/* Info */}
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm text-blue-700 dark:text-blue-300">
            ステップをクリックすると内部サブステップの詳細がインラインで表示されます
          </div>
        </div>

        {/* Content */}
        {viewMode === 'integrated' ? (
          <section>
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                統合ビュー（右上で切り替え可能）
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                本番環境で使用されるビュー。ユーザーの好みでパターンを切り替え可能
              </p>
            </div>
            <WorkflowProgressView
              steps={steps}
              currentStep={currentStep}
              waitingApproval={waitingApproval}
              onApprove={() => alert('承認しました')}
              onReject={() => alert('却下しました')}
              onRetry={(step) => alert(`${step}をリトライします`)}
            />
          </section>
        ) : (
          <div className="space-y-12">
            {/* Pattern 1: n8n Style */}
            <section>
              <div className="mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="w-6 h-6 rounded bg-violet-600 text-white text-sm flex items-center justify-center">1</span>
                  n8n スタイル
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  ダークテーマ、グラスモーフィズム、水平フロー、グロー効果
                </p>
              </div>
              <WorkflowPattern1_N8nStyle
                steps={steps}
                currentStep={currentStep}
                waitingApproval={waitingApproval}
              />
            </section>

            {/* Pattern 4: Vertical Timeline */}
            <section>
              <div className="mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="w-6 h-6 rounded bg-cyan-600 text-white text-sm flex items-center justify-center">4</span>
                  垂直タイムライン
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  ダークプレミアムテーマ、展開可能なカード、リアルタイムログ、データリッチ
                </p>
              </div>
              <WorkflowPattern4_VerticalTimeline
                steps={steps}
                currentStep={currentStep}
                waitingApproval={waitingApproval}
                onRetry={(step) => alert(`${step}をリトライします`)}
              />
            </section>

            {/* Pattern 5: Radial Progress */}
            <section>
              <div className="mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="w-6 h-6 rounded bg-emerald-600 text-white text-sm flex items-center justify-center">5</span>
                  ラジアルプログレス
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  円形レイアウト、中央ハブ、アーク接続、ミッションコントロール風
                </p>
              </div>
              <WorkflowPattern5_RadialProgress
                steps={steps}
                currentStep={currentStep}
                waitingApproval={waitingApproval}
                onApprove={() => alert('承認しました')}
                onReject={() => alert('却下しました')}
              />
            </section>
          </div>
        )}

        {/* Summary - Only show in all patterns view */}
        {viewMode === 'all' && (
          <div className="mt-12 p-6 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              採用パターン比較
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">パターン</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">テーマ</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">レイアウト</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">特徴</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">推奨用途</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700 dark:text-gray-300">
                  <tr className="border-b border-gray-100 dark:border-gray-700/50">
                    <td className="py-3 px-4 font-medium">1. n8n</td>
                    <td className="py-3 px-4">ダーク</td>
                    <td className="py-3 px-4">水平フロー</td>
                    <td className="py-3 px-4">グラスモーフィズム、グロー効果、コンパクト</td>
                    <td className="py-3 px-4">デフォルト、全体俯瞰</td>
                  </tr>
                  <tr className="border-b border-gray-100 dark:border-gray-700/50">
                    <td className="py-3 px-4 font-medium">4. タイムライン</td>
                    <td className="py-3 px-4">ダーク</td>
                    <td className="py-3 px-4">垂直リスト</td>
                    <td className="py-3 px-4">展開可能、詳細表示、ログ確認</td>
                    <td className="py-3 px-4">デバッグ、詳細確認</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium">5. ラジアル</td>
                    <td className="py-3 px-4">ダーク</td>
                    <td className="py-3 px-4">円形</td>
                    <td className="py-3 px-4">中央ハブ、進捗率強調、未来的</td>
                    <td className="py-3 px-4">デモ、プレゼン</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
