'use client';

import { Clock, AlertTriangle, CheckCircle, FileText, Activity } from 'lucide-react';
import type { Step, StepAttempt, ValidationReport } from '@/lib/types';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface StepDetailPanelProps {
  step: Step;
}

export function StepDetailPanel({ step }: StepDetailPanelProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          {step.step_name} 詳細
        </h3>
      </div>

      <div className="p-4 space-y-4">
        {/* タイミング情報 */}
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Clock className="h-4 w-4" />
          <span>
            {step.started_at ? formatDate(step.started_at) : '未開始'}
            {step.completed_at && ` → ${formatDate(step.completed_at)}`}
          </span>
        </div>

        {/* 試行履歴 */}
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
            <Activity className="h-3.5 w-3.5" />
            試行履歴
          </h4>
          <div className="space-y-2">
            {step.attempts.map((attempt, index) => (
              <AttemptCard key={attempt.id} attempt={attempt} index={index} />
            ))}
            {step.attempts.length === 0 && (
              <p className="text-xs text-gray-400">試行なし</p>
            )}
          </div>
        </div>

        {/* バリデーションレポート */}
        {step.validation_report && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              バリデーション
            </h4>
            <ValidationReportSummary report={step.validation_report} />
          </div>
        )}
      </div>
    </div>
  );
}

function AttemptCard({ attempt, index }: { attempt: StepAttempt; index: number }) {
  return (
    <div
      className={cn(
        'p-2 rounded border text-xs',
        attempt.status === 'succeeded' && 'bg-green-50 border-green-200',
        attempt.status === 'failed' && 'bg-red-50 border-red-200',
        attempt.status === 'running' && 'bg-blue-50 border-blue-200'
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium">
          試行 #{attempt.attempt_num}
        </span>
        <span
          className={cn(
            'px-1.5 py-0.5 rounded text-xs',
            attempt.status === 'succeeded' && 'bg-green-100 text-green-700',
            attempt.status === 'failed' && 'bg-red-100 text-red-700',
            attempt.status === 'running' && 'bg-blue-100 text-blue-700'
          )}
        >
          {attempt.status}
        </span>
      </div>
      <div className="text-gray-500 mt-1">
        {formatDate(attempt.started_at)}
        {attempt.completed_at && ` → ${formatDate(attempt.completed_at)}`}
      </div>
      {attempt.error && (
        <div className="mt-1 text-red-600">
          [{attempt.error.type}] {attempt.error.message}
        </div>
      )}
      {attempt.repairs && attempt.repairs.length > 0 && (
        <div className="mt-1 text-amber-600">
          修正適用: {attempt.repairs.map((r) => r.repair_type).join(', ')}
        </div>
      )}
    </div>
  );
}

function ValidationReportSummary({ report }: { report: ValidationReport }) {
  return (
    <div
      className={cn(
        'p-2 rounded border text-xs',
        report.valid ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
      )}
    >
      <div className="flex items-center gap-2">
        {report.valid ? (
          <CheckCircle className="h-4 w-4 text-green-500" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-red-500" />
        )}
        <span className="font-medium">
          {report.valid ? '検証OK' : '検証NG'}
        </span>
        <span className="text-gray-500">({report.format})</span>
      </div>
      {report.errors.length > 0 && (
        <ul className="mt-2 space-y-1">
          {report.errors.slice(0, 3).map((err, i) => (
            <li key={i} className="text-red-600">
              {err.path && `[${err.path}] `}
              {err.message}
            </li>
          ))}
          {report.errors.length > 3 && (
            <li className="text-gray-500">
              ...他 {report.errors.length - 3} 件
            </li>
          )}
        </ul>
      )}
      {report.warnings.length > 0 && (
        <ul className="mt-2 space-y-1">
          {report.warnings.slice(0, 3).map((warn, i) => (
            <li key={i} className="text-amber-600">
              {warn.path && `[${warn.path}] `}
              {warn.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
