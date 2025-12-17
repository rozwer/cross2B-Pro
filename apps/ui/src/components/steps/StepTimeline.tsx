'use client';

import type { Step } from '@/lib/types';
import { STEP_LABELS } from '@/lib/types';
import { StepNode } from './StepNode';

interface StepTimelineProps {
  steps: Step[];
  currentStep: string | null;
  waitingApproval: boolean;
  onRetry?: (stepName: string) => void;
  onResume?: (stepName: string) => void;
}

export function StepTimeline({
  steps,
  currentStep,
  waitingApproval,
  onRetry,
  onResume,
}: StepTimelineProps) {
  const stepMap = new Map(steps.map((s) => [s.step_name, s]));

  // STEP_NAMESの順序でstepsを表示
  const orderedSteps = Object.keys(STEP_LABELS).map((stepName) => {
    const step = stepMap.get(stepName);
    return {
      name: stepName,
      label: STEP_LABELS[stepName],
      step,
    };
  });

  // Calculate progress percentage
  const completedCount = orderedSteps.filter((s) => s.step?.status === 'completed').length;
  const progress = Math.round((completedCount / orderedSteps.length) * 100);

  return (
    <div className="card overflow-hidden animate-fade-in">
      {/* Header with progress */}
      <div className="p-4 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">ワークフロー進捗</h3>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{progress}%</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="p-4 space-y-0.5 max-h-[500px] overflow-y-auto">
        {orderedSteps.map((item, index) => (
          <StepNode
            key={item.name}
            stepName={item.name}
            label={item.label}
            step={item.step}
            index={index}
            isCurrent={item.name === currentStep}
            isWaitingApproval={waitingApproval && item.name === currentStep}
            isLast={index === orderedSteps.length - 1}
            onRetry={onRetry}
            onResume={onResume}
          />
        ))}
      </div>
    </div>
  );
}
