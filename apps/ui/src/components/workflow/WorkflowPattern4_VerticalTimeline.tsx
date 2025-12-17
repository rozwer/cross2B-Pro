'use client';

import { CheckCircle, XCircle, Loader2, Clock, Pause, Sparkles, Search, FileText, Pencil, Eye, Package, ChevronDown, ChevronRight, AlertTriangle, RotateCcw } from 'lucide-react';
import type { Step } from '@/lib/types';
import { STEP_LABELS } from '@/lib/types';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { SUB_STEPS, getSubStepStatus } from './subStepsData';

/**
 * Pattern 4: Vertical Timeline with Rich Cards
 * - Dark premium theme
 * - Expandable step cards with sub-step details
 * - Real-time logs for current step
 * - Output preview thumbnails
 * - Data-rich design for power users
 */

interface WorkflowPattern4Props {
  steps: Step[];
  currentStep: string;
  waitingApproval: boolean;
  onRetry?: (stepName: string) => void;
  onStepClick?: (stepName: string) => void;
}

const STEP_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; description: string }> = {
  'step-1': { icon: Package, color: '#3b82f6', description: 'キーワードと要件を入力' },
  'step0': { icon: Sparkles, color: '#8b5cf6', description: '初期設定と準備処理' },
  'step1': { icon: Search, color: '#8b5cf6', description: 'キーワード分析とSERP調査' },
  'step3': { icon: FileText, color: '#10b981', description: '記事構成の生成' },
  'step2': { icon: Search, color: '#f59e0b', description: '競合サイトの調査' },
  'step3a': { icon: Sparkles, color: '#ec4899', description: '並列コンテンツ生成 A' },
  'step3b': { icon: Sparkles, color: '#ec4899', description: '並列コンテンツ生成 B' },
  'step3c': { icon: Sparkles, color: '#ec4899', description: '並列コンテンツ生成 C' },
  'step4': { icon: FileText, color: '#06b6d4', description: '執筆準備と構成確定' },
  'step5': { icon: Pencil, color: '#8b5cf6', description: '本文の生成' },
  'step6': { icon: Eye, color: '#f59e0b', description: '編集と品質チェック' },
  'step6.5': { icon: Package, color: '#6366f1', description: '成果物の統合' },
  'step7a': { icon: FileText, color: '#10b981', description: 'HTML形式で出力' },
  'step7b': { icon: FileText, color: '#10b981', description: 'メタ情報の生成' },
  'step8': { icon: Eye, color: '#f59e0b', description: '最終検証' },
  'step9': { icon: Sparkles, color: '#8b5cf6', description: '最終調整' },
  'step10': { icon: CheckCircle, color: '#10b981', description: 'ワークフロー完了' },
};

const ORDERED_STEPS = [
  'step-1', 'step0', 'step1', 'step2', 'step3',
  'step3a', 'step3b', 'step3c',
  'step4', 'step5', 'step6', 'step6.5',
  'step7a', 'step7b', 'step8', 'step9', 'step10'
];

export function WorkflowPattern4_VerticalTimeline({ steps, currentStep, waitingApproval, onRetry }: WorkflowPattern4Props) {
  const stepMap = new Map(steps.map((s) => [s.step_name, s]));
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set([currentStep]));
  const completedCount = steps.filter(s => s.status === 'completed').length;
  const progress = Math.round((completedCount / ORDERED_STEPS.length) * 100);

  const toggleExpand = (stepName: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepName)) {
      newExpanded.delete(stepName);
    } else {
      newExpanded.add(stepName);
    }
    setExpandedSteps(newExpanded);
  };

  const getStatusIcon = (status?: string, isWaiting?: boolean) => {
    if (isWaiting) return <Pause className="w-4 h-4" />;
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'running': return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'failed': return <XCircle className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status?: string, isWaiting?: boolean) => {
    if (isWaiting) return { bg: 'bg-amber-500', text: 'text-amber-400', glow: 'shadow-amber-500/50' };
    switch (status) {
      case 'completed': return { bg: 'bg-emerald-500', text: 'text-emerald-400', glow: 'shadow-emerald-500/50' };
      case 'running': return { bg: 'bg-cyan-500', text: 'text-cyan-400', glow: 'shadow-cyan-500/50' };
      case 'failed': return { bg: 'bg-red-500', text: 'text-red-400', glow: 'shadow-red-500/50' };
      default: return { bg: 'bg-gray-600', text: 'text-gray-500', glow: '' };
    }
  };

  // Group parallel steps
  const groupedSteps: Array<string | string[]> = [];
  for (let i = 0; i < ORDERED_STEPS.length; i++) {
    const step = ORDERED_STEPS[i];
    if (step === 'step3a') {
      groupedSteps.push(['step3a', 'step3b', 'step3c']);
      i += 2;
    } else if (step === 'step7a') {
      groupedSteps.push(['step7a', 'step7b']);
      i += 1;
    } else {
      groupedSteps.push(step);
    }
  }

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)' }}>
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">実行履歴</h3>
            <p className="text-sm text-gray-400">リアルタイム進捗トラッカー</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-3xl font-bold text-white">{progress}%</p>
              <p className="text-xs text-gray-400">{completedCount} / {ORDERED_STEPS.length}</p>
            </div>
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #06b6d4 0%, #10b981 100%)'
            }}
          />
        </div>
      </div>

      {/* Timeline */}
      <div className="p-6 max-h-[500px] overflow-y-auto">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyan-500/50 via-emerald-500/50 to-gray-700/50" />

          {/* Steps */}
          <div className="space-y-3">
            {groupedSteps.map((item, index) => {
              const isParallel = Array.isArray(item);
              const stepNames = isParallel ? item : [item];

              return (
                <div key={index} className={cn(isParallel && "flex gap-3 pl-10")}>
                  {stepNames.map((stepName) => {
                    const step = stepMap.get(stepName);
                    const status = step?.status;
                    const isCurrent = stepName === currentStep;
                    const isWaiting = waitingApproval && isCurrent;
                    const isExpanded = expandedSteps.has(stepName);
                    const config = STEP_CONFIG[stepName];
                    const statusColors = getStatusColor(status, isWaiting);
                    const Icon = config?.icon || Sparkles;
                    const attempts = step?.attempts || [];
                    const subSteps = SUB_STEPS[stepName] || [];

                    return (
                      <div
                        key={stepName}
                        className={cn(
                          "relative",
                          !isParallel && "pl-10",
                          isParallel && "flex-1"
                        )}
                      >
                        {/* Timeline dot */}
                        {!isParallel && (
                          <div className={cn(
                            "absolute left-0 top-3 w-10 h-10 rounded-xl flex items-center justify-center",
                            "transition-all duration-300",
                            statusColors.bg,
                            (status === 'running' || isWaiting) && `shadow-lg ${statusColors.glow}`
                          )}>
                            <span className="text-white">
                              {getStatusIcon(status, isWaiting)}
                            </span>
                          </div>
                        )}

                        {/* Card */}
                        <div
                          className={cn(
                            "rounded-xl border transition-all duration-200",
                            "bg-white/5 backdrop-blur-sm",
                            status === 'completed' && "border-emerald-500/30",
                            status === 'running' && "border-cyan-500/50",
                            status === 'failed' && "border-red-500/50",
                            isWaiting && "border-amber-500/50 shadow-lg shadow-amber-500/20",
                            !status && "border-white/10 opacity-60",
                            isCurrent && "ring-1 ring-cyan-500/50"
                          )}
                        >
                          {/* Card header */}
                          <button
                            onClick={() => toggleExpand(stepName)}
                            className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className="w-8 h-8 rounded-lg flex items-center justify-center"
                                style={{ backgroundColor: `${config?.color}20` }}
                              >
                                <Icon className="w-4 h-4" style={{ color: config?.color }} />
                              </div>
                              <div>
                                <h4 className={cn(
                                  "text-sm font-medium",
                                  status ? "text-white" : "text-gray-400"
                                )}>
                                  {STEP_LABELS[stepName]}
                                </h4>
                                <p className="text-xs text-gray-500">{config?.description}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {attempts.length > 1 && (
                                <span className="text-xs text-amber-400 flex items-center gap-1">
                                  <AlertTriangle className="w-3 h-3" />
                                  {attempts.length}回
                                </span>
                              )}
                              {isExpanded ? (
                                <ChevronDown className="w-4 h-4 text-gray-400" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-gray-400" />
                              )}
                            </div>
                          </button>

                          {/* Expanded content with sub-steps */}
                          {isExpanded && (
                            <div className="px-4 pb-4 border-t border-white/10">
                              {/* Sub-steps */}
                              {subSteps.length > 0 && (
                                <div className="pt-3 space-y-1.5">
                                  <p className="text-xs font-medium text-white/60 mb-2">内部ステップ</p>
                                  {subSteps.map((subStep, idx) => {
                                    const subStatus = getSubStepStatus(status, idx, subSteps.length);
                                    return (
                                      <div
                                        key={subStep.id}
                                        className={cn(
                                          "flex items-center gap-2.5 px-2.5 py-2 rounded-lg",
                                          "transition-colors",
                                          subStatus === 'completed' && "bg-emerald-500/10",
                                          subStatus === 'running' && "bg-cyan-500/10",
                                          subStatus === 'failed' && "bg-red-500/10",
                                          subStatus === 'pending' && "bg-white/5 opacity-50"
                                        )}
                                      >
                                        <div className={cn(
                                          "w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0",
                                          subStatus === 'completed' && "bg-emerald-500",
                                          subStatus === 'running' && "bg-cyan-500",
                                          subStatus === 'failed' && "bg-red-500",
                                          subStatus === 'pending' && "bg-gray-600"
                                        )}>
                                          {subStatus === 'completed' && <CheckCircle className="w-3 h-3 text-white" />}
                                          {subStatus === 'running' && <Loader2 className="w-3 h-3 text-white animate-spin" />}
                                          {subStatus === 'failed' && <XCircle className="w-3 h-3 text-white" />}
                                          {subStatus === 'pending' && <Clock className="w-3 h-3 text-white" />}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                          <p className={cn(
                                            "text-xs font-medium",
                                            subStatus === 'completed' && "text-emerald-400",
                                            subStatus === 'running' && "text-cyan-400",
                                            subStatus === 'failed' && "text-red-400",
                                            subStatus === 'pending' && "text-gray-400"
                                          )}>
                                            {subStep.name}
                                          </p>
                                          <p className="text-[10px] text-gray-500 truncate">
                                            {subStep.description}
                                          </p>
                                        </div>
                                        {subStatus === 'running' && (
                                          <span className="text-[10px] text-cyan-400 flex items-center gap-1">
                                            <Loader2 className="w-2.5 h-2.5 animate-spin" />
                                            処理中
                                          </span>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              )}

                              {/* Status info */}
                              <div className="pt-3 space-y-2">
                                {status === 'completed' && (
                                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                                    <p className="text-xs text-emerald-400">✓ 正常に完了</p>
                                    {step?.completed_at && (
                                      <p className="text-xs text-gray-500 mt-1">
                                        完了: {new Date(step.completed_at).toLocaleTimeString()}
                                      </p>
                                    )}
                                  </div>
                                )}
                                {status === 'failed' && (
                                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                    <p className="text-xs text-red-400 mb-2">エラーが発生しました</p>
                                    {onRetry && (
                                      <button
                                        onClick={() => onRetry(stepName)}
                                        className="inline-flex items-center gap-1 px-2 py-1 text-xs text-red-400 hover:bg-red-500/20 rounded transition-colors"
                                      >
                                        <RotateCcw className="w-3 h-3" />
                                        リトライ
                                      </button>
                                    )}
                                  </div>
                                )}
                                {isWaiting && (
                                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                    <p className="text-xs text-amber-400">承認待ち状態です</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-white/10 flex items-center justify-between text-xs text-gray-500">
        <span>クリックでサブステップを表示</span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> 完了
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500" /> 実行中
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> 承認待ち
          </span>
        </div>
      </div>
    </div>
  );
}
