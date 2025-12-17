'use client';

import { useState } from 'react';
import { CheckCircle, XCircle, Loader2, Clock, Pause, Sparkles, Search, FileText, Pencil, Eye, Package, ThumbsUp, ThumbsDown, X } from 'lucide-react';
import type { Step } from '@/lib/types';
import { STEP_LABELS } from '@/lib/types';
import { cn } from '@/lib/utils';
import { SUB_STEPS, getSubStepStatus } from './subStepsData';

/**
 * Pattern 5: Radial/Circular Progress
 * - Center hub with overall progress
 * - Steps arranged in a circle
 * - Arc connections with gradients
 * - Futuristic mission control aesthetic
 * - Click node to show inline sub-step details
 */

interface WorkflowPattern5Props {
  steps: Step[];
  currentStep: string;
  waitingApproval: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onStepClick?: (stepName: string) => void;
}

const STEP_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string }> = {
  'step-1': { icon: Package, color: '#3b82f6' },
  'step0': { icon: Sparkles, color: '#8b5cf6' },
  'step1': { icon: Search, color: '#a855f7' },
  'step2': { icon: Search, color: '#f59e0b' },
  'step3': { icon: FileText, color: '#10b981' },
  'step3a': { icon: Sparkles, color: '#ec4899' },
  'step3b': { icon: Sparkles, color: '#ec4899' },
  'step3c': { icon: Sparkles, color: '#ec4899' },
  'step4': { icon: FileText, color: '#06b6d4' },
  'step5': { icon: Pencil, color: '#8b5cf6' },
  'step6': { icon: Eye, color: '#f59e0b' },
  'step6.5': { icon: Package, color: '#6366f1' },
  'step7a': { icon: FileText, color: '#10b981' },
  'step7b': { icon: FileText, color: '#22c55e' },
  'step8': { icon: Eye, color: '#eab308' },
  'step9': { icon: Sparkles, color: '#a855f7' },
  'step10': { icon: CheckCircle, color: '#10b981' },
};

// Simplified steps for radial view
const RADIAL_STEPS = [
  'step-1', 'step0', 'step1', 'step2', 'step3',
  'step3a', 'step4', 'step5', 'step6', 'step6.5',
  'step7a', 'step8', 'step9', 'step10'
];

export function WorkflowPattern5_RadialProgress({ steps, currentStep, waitingApproval, onApprove, onReject }: WorkflowPattern5Props) {
  const stepMap = new Map(steps.map((s) => [s.step_name, s]));
  const completedCount = steps.filter(s => s.status === 'completed').length;
  const totalSteps = Object.keys(STEP_LABELS).length;
  const progress = Math.round((completedCount / totalSteps) * 100);

  // Selected step for detail view
  const [selectedStep, setSelectedStep] = useState<string | null>(null);

  // Calculate positions for radial layout
  const centerX = 200;
  const centerY = 200;
  const radius = 150;
  const stepPositions = RADIAL_STEPS.map((step, index) => {
    const angle = (index / RADIAL_STEPS.length) * 2 * Math.PI - Math.PI / 2;
    return {
      step,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      angle,
    };
  });

  const getStatusStyle = (status?: string, isWaiting?: boolean) => {
    if (isWaiting) return { stroke: '#f59e0b', fill: '#f59e0b', glow: 'drop-shadow(0 0 8px #f59e0b)' };
    switch (status) {
      case 'completed': return { stroke: '#10b981', fill: '#10b981', glow: 'drop-shadow(0 0 6px #10b981)' };
      case 'running': return { stroke: '#06b6d4', fill: '#06b6d4', glow: 'drop-shadow(0 0 10px #06b6d4)' };
      case 'failed': return { stroke: '#ef4444', fill: '#ef4444', glow: 'drop-shadow(0 0 8px #ef4444)' };
      default: return { stroke: '#4b5563', fill: '#374151', glow: '' };
    }
  };

  // Progress ring calculation
  const progressRadius = 70;
  const progressCircumference = 2 * Math.PI * progressRadius;
  const progressOffset = progressCircumference - (progress / 100) * progressCircumference;

  const handleNodeClick = (stepName: string) => {
    setSelectedStep(selectedStep === stepName ? null : stepName);
  };

  const selectedStepData = selectedStep ? stepMap.get(selectedStep) : null;
  const selectedSubSteps = selectedStep ? SUB_STEPS[selectedStep] || [] : [];

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1e1b4b 100%)' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">ミッションコントロール</h3>
              <p className="text-sm text-gray-400">SEO Article Generation Pipeline</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10">
            <span className={cn(
              "w-2 h-2 rounded-full",
              steps.some(s => s.status === 'running') ? "bg-cyan-500 animate-pulse" :
              steps.every(s => s.status === 'completed') ? "bg-emerald-500" : "bg-amber-500"
            )} />
            <span className="text-sm text-white font-medium">
              {steps.some(s => s.status === 'running') ? '実行中' :
               steps.every(s => s.status === 'completed') ? '完了' : '処理中'}
            </span>
          </div>
        </div>
      </div>

      {/* Radial View + Detail Panel */}
      <div className="relative p-8 flex items-start justify-center gap-4">
        <svg width="400" height="400" className="overflow-visible flex-shrink-0">
          <defs>
            {/* Glow filter */}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Gradient for progress ring */}
            <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="50%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>

          {/* Background circles */}
          <circle cx={centerX} cy={centerY} r="180" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="40" />
          <circle cx={centerX} cy={centerY} r="120" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />

          {/* Connection arcs */}
          {stepPositions.map((pos, index) => {
            const nextPos = stepPositions[(index + 1) % stepPositions.length];
            const step = stepMap.get(pos.step);
            const isCompleted = step?.status === 'completed';

            return (
              <path
                key={`arc-${index}`}
                d={`M ${pos.x} ${pos.y} Q ${centerX} ${centerY} ${nextPos.x} ${nextPos.y}`}
                fill="none"
                stroke={isCompleted ? STEP_CONFIG[pos.step]?.color || '#8b5cf6' : '#374151'}
                strokeWidth="2"
                strokeDasharray={isCompleted ? "0" : "4 4"}
                opacity={isCompleted ? 0.6 : 0.3}
              />
            );
          })}

          {/* Step nodes */}
          {stepPositions.map((pos) => {
            const step = stepMap.get(pos.step);
            const status = step?.status;
            const isCurrent = pos.step === currentStep;
            const isWaiting = waitingApproval && isCurrent;
            const isSelected = selectedStep === pos.step;
            const config = STEP_CONFIG[pos.step];
            const statusStyle = getStatusStyle(status, isWaiting);
            const Icon = config?.icon || Sparkles;

            return (
              <g
                key={pos.step}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => handleNodeClick(pos.step)}
                className="cursor-pointer"
                style={{ cursor: 'pointer' }}
              >
                {/* Selection ring */}
                {isSelected && (
                  <circle
                    r="26"
                    fill="none"
                    stroke="#8b5cf6"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                  />
                )}
                {/* Hover area */}
                <circle r="22" fill="transparent" className="hover:fill-white/5" />
                {/* Outer glow for active */}
                {(status === 'running' || isWaiting) && (
                  <circle
                    r="24"
                    fill="none"
                    stroke={statusStyle.stroke}
                    strokeWidth="2"
                    opacity="0.5"
                    className="animate-pulse"
                  />
                )}
                {/* Node background */}
                <circle
                  r="18"
                  fill={status ? statusStyle.fill : '#1f2937'}
                  stroke={isSelected ? '#8b5cf6' : statusStyle.stroke}
                  strokeWidth={isSelected ? 3 : 2}
                  style={{ filter: status ? statusStyle.glow : '' }}
                />
                {/* Icon */}
                <foreignObject x="-10" y="-10" width="20" height="20">
                  <div className="w-full h-full flex items-center justify-center">
                    {status === 'running' ? (
                      <Loader2 className="w-4 h-4 text-white animate-spin" />
                    ) : status === 'completed' ? (
                      <CheckCircle className="w-4 h-4 text-white" />
                    ) : isWaiting ? (
                      <Pause className="w-4 h-4 text-white" />
                    ) : status === 'failed' ? (
                      <XCircle className="w-4 h-4 text-white" />
                    ) : (
                      <Icon className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </foreignObject>
              </g>
            );
          })}

          {/* Center hub */}
          <g transform={`translate(${centerX}, ${centerY})`}>
            {/* Background */}
            <circle r="85" fill="#0f172a" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
            {/* Progress track */}
            <circle
              r={progressRadius}
              fill="none"
              stroke="rgba(255,255,255,0.1)"
              strokeWidth="8"
            />
            {/* Progress ring */}
            <circle
              r={progressRadius}
              fill="none"
              stroke="url(#progressGradient)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={progressCircumference}
              strokeDashoffset={progressOffset}
              transform="rotate(-90)"
              style={{ transition: 'stroke-dashoffset 0.5s ease-out' }}
            />
            {/* Center text */}
            <text
              y="-8"
              textAnchor="middle"
              className="text-4xl font-bold fill-white"
            >
              {progress}%
            </text>
            <text
              y="15"
              textAnchor="middle"
              className="text-sm fill-gray-400"
            >
              完了
            </text>
            <text
              y="35"
              textAnchor="middle"
              className="text-xs fill-gray-500"
            >
              {completedCount} / {totalSteps}
            </text>
          </g>
        </svg>

        {/* Detail Panel - appears when step is selected */}
        {selectedStep && (
          <div className={cn(
            "w-64 rounded-xl",
            "bg-slate-900/95 backdrop-blur-lg border border-white/20",
            "shadow-xl shadow-black/30 overflow-hidden"
          )}>
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <div
                  className="w-6 h-6 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${STEP_CONFIG[selectedStep]?.color}30` }}
                >
                  {(() => {
                    const Icon = STEP_CONFIG[selectedStep]?.icon || Sparkles;
                    return <Icon className="w-3.5 h-3.5" style={{ color: STEP_CONFIG[selectedStep]?.color }} />;
                  })()}
                </div>
                <span className="text-sm font-medium text-white truncate">
                  {STEP_LABELS[selectedStep]}
                </span>
              </div>
              <button
                onClick={() => setSelectedStep(null)}
                className="p-1 hover:bg-white/10 rounded transition-colors"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Sub-steps */}
            <div className="p-3 max-h-[300px] overflow-y-auto">
              {selectedSubSteps.length > 0 ? (
                <div className="space-y-1.5">
                  {selectedSubSteps.map((subStep, idx) => {
                    const subStatus = getSubStepStatus(selectedStepData?.status, idx, selectedSubSteps.length);
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
              ) : (
                <p className="text-xs text-gray-500 text-center py-4">
                  サブステップなし
                </p>
              )}
            </div>

            {/* Status info */}
            {selectedStepData && (
              <div className="px-3 pb-3">
                <div className={cn(
                  "p-2 rounded-lg text-xs",
                  selectedStepData.status === 'completed' && "bg-emerald-500/10 text-emerald-400",
                  selectedStepData.status === 'running' && "bg-cyan-500/10 text-cyan-400",
                  selectedStepData.status === 'failed' && "bg-red-500/10 text-red-400",
                  !selectedStepData.status && "bg-gray-500/10 text-gray-400"
                )}>
                  {selectedStepData.status === 'completed' && '✓ 完了'}
                  {selectedStepData.status === 'running' && '処理中...'}
                  {selectedStepData.status === 'failed' && 'エラー発生'}
                  {!selectedStepData.status && '待機中'}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Floating labels for key steps */}
        {!selectedStep && (
          <div className="absolute inset-0 pointer-events-none">
            {stepPositions.filter((_, i) => i % 3 === 0).map((pos) => {
              const step = stepMap.get(pos.step);
              const labelX = pos.x > centerX ? pos.x + 30 : pos.x - 30;
              const labelY = pos.y;

              return (
                <div
                  key={`label-${pos.step}`}
                  className="absolute transform -translate-y-1/2"
                  style={{
                    left: `${(labelX / 400) * 100}%`,
                    top: `${(labelY / 400) * 100}%`,
                    textAlign: pos.x > centerX ? 'left' : 'right',
                  }}
                >
                  <span className={cn(
                    "text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap",
                    step?.status === 'completed' && "bg-emerald-500/20 text-emerald-400",
                    step?.status === 'running' && "bg-cyan-500/20 text-cyan-400",
                    !step?.status && "bg-gray-700/50 text-gray-500"
                  )}>
                    {STEP_LABELS[pos.step]}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Action bar for approval */}
      {waitingApproval && (
        <div className="mx-6 mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Pause className="w-5 h-5 text-amber-500" />
              <div>
                <p className="text-sm font-medium text-amber-400">承認が必要です</p>
                <p className="text-xs text-amber-500/70">レビュー結果を確認してください</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onReject}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg hover:bg-red-500/20 transition-colors"
              >
                <ThumbsDown className="w-4 h-4" />
                却下
              </button>
              <button
                onClick={onApprove}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-500 transition-colors"
              >
                <ThumbsUp className="w-4 h-4" />
                承認
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-3 border-t border-white/10 flex items-center justify-between text-xs">
        <span className="text-gray-500">ノードをクリックで詳細表示</span>
        <div className="flex items-center gap-4 text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Completed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" /> Running
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Waiting
          </span>
        </div>
      </div>
    </div>
  );
}
