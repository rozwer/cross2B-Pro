'use client';

import { useState } from 'react';
import { CheckCircle, XCircle, Loader2, Clock, Pause, Sparkles, Search, FileText, Pencil, Eye, Package, ChevronDown, ChevronRight, type LucideIcon } from 'lucide-react';
import type { Step } from '@/lib/types';
import { STEP_LABELS } from '@/lib/types';
import { cn } from '@/lib/utils';
import { SUB_STEPS, getSubStepStatus } from './subStepsData';

/**
 * Pattern 1: n8n Style
 * - Dark glassmorphism theme
 * - Horizontal flow with curved bezier connections
 * - Nodes as rounded cards with glow effects
 * - Click to expand inline sub-steps
 */

interface WorkflowPattern1Props {
  steps: Step[];
  currentStep: string;
  waitingApproval: boolean;
  onStepClick?: (stepName: string) => void;
}

const STEP_ICONS: Record<string, LucideIcon> = {
  'step-1': Package,
  'step0': Sparkles,
  'step1': Search,
  'step3': FileText,
  'step2': Search,
  'step3a': Sparkles,
  'step3b': Sparkles,
  'step3c': Sparkles,
  'step4': FileText,
  'step5': Pencil,
  'step6': Eye,
  'step6.5': Package,
  'step7a': FileText,
  'step7b': FileText,
  'step8': Eye,
  'step9': Sparkles,
  'step10': CheckCircle,
};

const STEP_COLORS: Record<string, string> = {
  'step-1': '#3b82f6',
  'step0': '#8b5cf6',
  'step1': '#8b5cf6',
  'step3': '#10b981',
  'step2': '#10b981',
  'step3a': '#f59e0b',
  'step3b': '#f59e0b',
  'step3c': '#f59e0b',
  'step4': '#06b6d4',
  'step5': '#06b6d4',
  'step6': '#ec4899',
  'step6.5': '#8b5cf6',
  'step7a': '#10b981',
  'step7b': '#10b981',
  'step8': '#f59e0b',
  'step9': '#8b5cf6',
  'step10': '#10b981',
};

// Simplified step groups for visualization
const STEP_GROUPS = [
  ['step-1'],
  ['step0'],
  ['step1'],
  ['step2', 'step3'],
  ['step3a', 'step3b', 'step3c'],
  ['step4'],
  ['step5'],
  ['step6'],
  ['step6.5'],
  ['step7a', 'step7b'],
  ['step8'],
  ['step9'],
  ['step10'],
];

function getStatusIcon(status?: string, isWaiting?: boolean) {
  if (isWaiting) return Pause;
  switch (status) {
    case 'completed': return CheckCircle;
    case 'failed': return XCircle;
    case 'running': return Loader2;
    default: return Clock;
  }
}

export function WorkflowPattern1_N8nStyle({ steps, currentStep, waitingApproval }: WorkflowPattern1Props) {
  const stepMap = new Map(steps.map((s) => [s.step_name, s]));
  const completedCount = steps.filter(s => s.status === 'completed').length;
  const totalSteps = Object.keys(STEP_LABELS).length;
  const progress = Math.round((completedCount / totalSteps) * 100);

  // Track expanded steps
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const handleStepClick = (stepName: string) => {
    setExpandedStep(expandedStep === stepName ? null : stepName);
  };

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">ワークフロー</h3>
              <p className="text-xs text-gray-400">SEO Article Generation</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-white">{progress}%</span>
            <span className="text-xs text-gray-400">完了</span>
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #8b5cf6 0%, #06b6d4 50%, #10b981 100%)'
            }}
          />
        </div>
      </div>

      {/* Flow Canvas */}
      <div className="p-6 overflow-x-auto">
        <div className="flex items-start gap-2 min-w-max">
          {STEP_GROUPS.map((group, groupIndex) => (
            <div key={groupIndex} className="flex items-start gap-2">
              {/* Node Group */}
              <div className={cn(
                "flex gap-2",
                group.length > 1 ? "flex-col" : ""
              )}>
                {group.map((stepName) => {
                  const step = stepMap.get(stepName);
                  const status = step?.status;
                  const isCurrent = stepName === currentStep;
                  const isWaiting = waitingApproval && isCurrent;
                  const Icon = STEP_ICONS[stepName] || Sparkles;
                  const StatusIcon = getStatusIcon(status, isWaiting);
                  const color = STEP_COLORS[stepName] || '#8b5cf6';
                  const isExpanded = expandedStep === stepName;
                  const subSteps = SUB_STEPS[stepName] || [];

                  return (
                    <div key={stepName} className="relative">
                      <button
                        onClick={() => handleStepClick(stepName)}
                        className={cn(
                          "relative group text-left",
                          "px-4 py-3 rounded-xl",
                          "border transition-all duration-300",
                          "backdrop-blur-sm cursor-pointer",
                          "hover:scale-105 hover:z-10",
                          status === 'completed' && "bg-white/5 border-emerald-500/50 hover:border-emerald-400",
                          status === 'running' && "bg-white/10 border-cyan-500/50 hover:border-cyan-400",
                          status === 'failed' && "bg-white/5 border-red-500/50 hover:border-red-400",
                          isWaiting && "bg-amber-500/10 border-amber-500/50 hover:border-amber-400",
                          !status && "bg-white/5 border-white/10 opacity-50 hover:opacity-70",
                          isCurrent && !isWaiting && "ring-2 ring-cyan-500/50",
                          isExpanded && "ring-2 ring-violet-500/50"
                        )}
                        style={{
                          boxShadow: status === 'completed' ? `0 0 20px ${color}30` :
                                     status === 'running' ? `0 0 30px ${color}40` : 'none'
                        }}
                      >
                        <div className="flex items-center gap-3">
                          {/* Icon */}
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center"
                            style={{ backgroundColor: `${color}20` }}
                          >
                            <Icon className="w-4 h-4" style={{ color }} />
                          </div>
                          {/* Label */}
                          <div className="min-w-[80px]">
                            <p className="text-xs font-medium text-white truncate">
                              {STEP_LABELS[stepName]}
                            </p>
                          </div>
                          {/* Status indicator */}
                          <div className={cn(
                            "w-5 h-5 rounded-full flex items-center justify-center",
                            status === 'completed' && "bg-emerald-500",
                            status === 'running' && "bg-cyan-500",
                            status === 'failed' && "bg-red-500",
                            isWaiting && "bg-amber-500",
                            !status && "bg-gray-600"
                          )}>
                            <StatusIcon className={cn(
                              "w-3 h-3 text-white",
                              status === 'running' && "animate-spin"
                            )} />
                          </div>
                          {/* Expand indicator */}
                          {subSteps.length > 0 && (
                            <div className="text-white/50">
                              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            </div>
                          )}
                        </div>

                        {/* Glow effect for running */}
                        {status === 'running' && (
                          <div className="absolute inset-0 rounded-xl animate-pulse-soft pointer-events-none"
                               style={{ boxShadow: `0 0 30px ${color}50` }} />
                        )}
                      </button>

                      {/* Expanded Sub-steps */}
                      {isExpanded && subSteps.length > 0 && (
                        <div className={cn(
                          "absolute left-0 top-full mt-2 z-20",
                          "min-w-[200px] p-3 rounded-xl",
                          "bg-slate-900/95 backdrop-blur-lg border border-white/20",
                          "shadow-xl shadow-black/30"
                        )}>
                          <div className="text-xs font-medium text-white/70 mb-2 px-1">
                            内部ステップ
                          </div>
                          <div className="space-y-1.5">
                            {subSteps.map((subStep, idx) => {
                              const subStatus = getSubStepStatus(status, idx, subSteps.length);
                              return (
                                <div
                                  key={subStep.id}
                                  className={cn(
                                    "flex items-center gap-2 px-2 py-1.5 rounded-lg",
                                    "transition-colors",
                                    subStatus === 'completed' && "bg-emerald-500/10",
                                    subStatus === 'running' && "bg-cyan-500/10",
                                    subStatus === 'failed' && "bg-red-500/10",
                                    subStatus === 'pending' && "bg-white/5 opacity-50"
                                  )}
                                >
                                  <div className={cn(
                                    "w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0",
                                    subStatus === 'completed' && "bg-emerald-500",
                                    subStatus === 'running' && "bg-cyan-500",
                                    subStatus === 'failed' && "bg-red-500",
                                    subStatus === 'pending' && "bg-gray-600"
                                  )}>
                                    {subStatus === 'completed' && <CheckCircle className="w-2.5 h-2.5 text-white" />}
                                    {subStatus === 'running' && <Loader2 className="w-2.5 h-2.5 text-white animate-spin" />}
                                    {subStatus === 'failed' && <XCircle className="w-2.5 h-2.5 text-white" />}
                                    {subStatus === 'pending' && <Clock className="w-2.5 h-2.5 text-white" />}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className={cn(
                                      "text-xs font-medium truncate",
                                      subStatus === 'completed' && "text-emerald-400",
                                      subStatus === 'running' && "text-cyan-400",
                                      subStatus === 'failed' && "text-red-400",
                                      subStatus === 'pending' && "text-gray-400"
                                    )}>
                                      {subStep.name}
                                    </p>
                                  </div>
                                  {subStatus === 'running' && (
                                    <span className="text-[10px] text-cyan-400">処理中</span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Connector */}
              {groupIndex < STEP_GROUPS.length - 1 && (
                <div className="flex items-center pt-3">
                  <svg width="40" height="20" className="text-white/30">
                    <defs>
                      <linearGradient id={`grad-${groupIndex}`} x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor={STEP_COLORS[group[0]] || '#8b5cf6'} stopOpacity="0.5" />
                        <stop offset="100%" stopColor={STEP_COLORS[STEP_GROUPS[groupIndex + 1]?.[0]] || '#8b5cf6'} stopOpacity="0.5" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M 0 10 Q 20 10 40 10"
                      stroke={`url(#grad-${groupIndex})`}
                      strokeWidth="2"
                      fill="none"
                      strokeDasharray={stepMap.get(group[group.length - 1])?.status === 'completed' ? "0" : "4 4"}
                    />
                    <polygon
                      points="35,7 40,10 35,13"
                      fill={STEP_COLORS[STEP_GROUPS[groupIndex + 1]?.[0]] || '#8b5cf6'}
                      opacity="0.5"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 border-t border-white/10 flex items-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
          <span className="text-gray-400">完了</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan-500 animate-pulse" />
          <span className="text-gray-400">実行中</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500" />
          <span className="text-gray-400">承認待ち</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gray-600" />
          <span className="text-gray-400">待機中</span>
        </div>
        <div className="ml-auto text-gray-500">
          クリックで内部ステップを表示
        </div>
      </div>
    </div>
  );
}
