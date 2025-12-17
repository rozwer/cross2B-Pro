'use client';

import { useState } from 'react';
import { LayoutGrid, Clock, Target } from 'lucide-react';
import type { Step } from '@/lib/types';
import { cn } from '@/lib/utils';
import { WorkflowPattern1_N8nStyle } from './WorkflowPattern1_N8nStyle';
import { WorkflowPattern4_VerticalTimeline } from './WorkflowPattern4_VerticalTimeline';
import { WorkflowPattern5_RadialProgress } from './WorkflowPattern5_RadialProgress';

/**
 * WorkflowProgressView
 * - Unified component with pattern switching (n8n, Timeline, Radial)
 * - Each pattern handles its own sub-step expansion inline
 * - Saves user preference to localStorage
 */

export type WorkflowViewPattern = 'n8n' | 'timeline' | 'radial';

interface WorkflowProgressViewProps {
  steps: Step[];
  currentStep: string | null;
  waitingApproval: boolean;
  onApprove?: () => void;
  onReject?: (reason: string) => void;
  onRetry?: (stepName: string) => void;
  defaultPattern?: WorkflowViewPattern;
}

const PATTERN_CONFIG: Record<WorkflowViewPattern, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
  n8n: { label: 'フロー', icon: LayoutGrid },
  timeline: { label: 'タイムライン', icon: Clock },
  radial: { label: 'ラジアル', icon: Target },
};

const STORAGE_KEY = 'workflow-view-pattern';

export function WorkflowProgressView({
  steps,
  currentStep,
  waitingApproval,
  onApprove,
  onReject,
  onRetry,
  defaultPattern = 'n8n',
}: WorkflowProgressViewProps) {
  // Load saved pattern from localStorage
  const [pattern, setPattern] = useState<WorkflowViewPattern>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && (saved === 'n8n' || saved === 'timeline' || saved === 'radial')) {
        return saved as WorkflowViewPattern;
      }
    }
    return defaultPattern;
  });

  const handlePatternChange = (newPattern: WorkflowViewPattern) => {
    setPattern(newPattern);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, newPattern);
    }
  };

  return (
    <div className="relative">
      {/* Pattern Switcher */}
      <div className="absolute top-4 right-4 z-10 flex rounded-lg overflow-hidden border border-white/20 bg-black/20 backdrop-blur-sm">
        {(Object.keys(PATTERN_CONFIG) as WorkflowViewPattern[]).map((key) => {
          const config = PATTERN_CONFIG[key];
          const Icon = config.icon;
          const isActive = pattern === key;

          return (
            <button
              key={key}
              onClick={() => handlePatternChange(key)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-all",
                isActive
                  ? "bg-white/20 text-white"
                  : "text-white/60 hover:text-white hover:bg-white/10"
              )}
              title={config.label}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{config.label}</span>
            </button>
          );
        })}
      </div>

      {/* Workflow View - each pattern handles sub-step expansion internally */}
      <div className="transition-all duration-300">
        {pattern === 'n8n' && (
          <WorkflowPattern1_N8nStyle
            steps={steps}
            currentStep={currentStep}
            waitingApproval={waitingApproval}
          />
        )}
        {pattern === 'timeline' && (
          <WorkflowPattern4_VerticalTimeline
            steps={steps}
            currentStep={currentStep}
            waitingApproval={waitingApproval}
            onRetry={onRetry}
          />
        )}
        {pattern === 'radial' && (
          <WorkflowPattern5_RadialProgress
            steps={steps}
            currentStep={currentStep}
            waitingApproval={waitingApproval}
            onApprove={onApprove}
            onReject={onReject}
          />
        )}
      </div>
    </div>
  );
}
