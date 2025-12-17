'use client';

import { use, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  Copy,
  Settings,
  Activity,
  FileText,
  Wifi,
  WifiOff,
  Network,
} from 'lucide-react';
import { useRun } from '@/hooks/useRun';
import { useRunProgress } from '@/hooks/useRunProgress';
import { useArtifacts } from '@/hooks/useArtifact';
import { RunStatusBadge } from '@/components/runs/RunStatusBadge';
import { WorkflowProgressView } from '@/components/workflow';
import { StepDetailPanel } from '@/components/steps/StepDetailPanel';
import { ApprovalDialog } from '@/components/approval/ApprovalDialog';
import { ResumeConfirmDialog } from '@/components/approval/ResumeConfirmDialog';
import { ArtifactViewer } from '@/components/artifacts/ArtifactViewer';
import { LoadingPage } from '@/components/common/Loading';
import { ErrorMessage } from '@/components/common/ErrorBoundary';
import { formatDate } from '@/lib/utils';
import { STEP_LABELS } from '@/lib/types';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

// ===== DEBUG_LOG_START =====
type TabType = 'timeline' | 'artifacts' | 'events' | 'settings' | 'network';
// ===== DEBUG_LOG_END =====

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  // Next.js 15 では params が Promise の場合がある
  const resolvedParams = params instanceof Promise ? use(params) : params;
  const { id } = resolvedParams;
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('timeline');
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [resumeStep, setResumeStep] = useState<string | null>(null);

  const { run, loading, error, fetch, approve, reject, retry, resume } = useRun(id);
  const { events, wsStatus } = useRunProgress(id, {
    onEvent: (event) => {
      if (
        event.type === 'step_completed' ||
        event.type === 'step_failed' ||
        event.type === 'run_completed'
      ) {
        fetch();
      }
    },
  });
  const { artifacts, fetch: fetchArtifacts } = useArtifacts(id);

  const handleRetry = useCallback(
    async (stepName: string) => {
      try {
        await retry(stepName);
      } catch (err) {
        console.error('Retry failed:', err);
      }
    },
    [retry]
  );

  const handleResume = useCallback((stepName: string) => {
    setResumeStep(stepName);
  }, []);

  const handleResumeConfirm = useCallback(async () => {
    if (!resumeStep) return;
    try {
      const result = await resume(resumeStep);
      router.push(`/runs/${result.new_run_id}`);
    } catch (err) {
      throw err;
    }
  }, [resumeStep, resume, router]);

  if (loading) {
    return <LoadingPage text="Run を読み込み中..." />;
  }

  if (error || !run) {
    return <ErrorMessage message={error || 'Run not found'} onRetry={fetch} />;
  }

  const step = run.steps.find((s) => s.step_name === selectedStep);
  const previewUrl = api.artifacts.getPreviewUrl(id);

  return (
    <div>
      {/* ヘッダー */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={() => router.push('/runs')}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">
                {run.input.keyword}
              </h1>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
              <span>ID: {run.id.slice(0, 8)}</span>
              <span>作成: {formatDate(run.created_at)}</span>
              <span className="flex items-center gap-1">
                {wsStatus === 'connected' ? (
                  <Wifi className="h-4 w-4 text-green-500" />
                ) : (
                  <WifiOff className="h-4 w-4 text-gray-400" />
                )}
                {wsStatus}
              </span>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetch}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              更新
            </button>
            {run.status === 'waiting_approval' && (
              <button
                onClick={() => setShowApprovalDialog(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition-colors"
              >
                承認待ち
              </button>
            )}
            {run.status === 'completed' && (
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                プレビュー
              </a>
            )}
          </div>
        </div>

        {/* タブ */}
        <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
          <TabButton
            active={activeTab === 'timeline'}
            onClick={() => setActiveTab('timeline')}
            icon={<Activity className="h-4 w-4" />}
            label="タイムライン"
          />
          <TabButton
            active={activeTab === 'artifacts'}
            onClick={() => {
              setActiveTab('artifacts');
              fetchArtifacts();
            }}
            icon={<FileText className="h-4 w-4" />}
            label="成果物"
          />
          <TabButton
            active={activeTab === 'events'}
            onClick={() => setActiveTab('events')}
            icon={<Activity className="h-4 w-4" />}
            label={`イベント (${events.length})`}
          />
          <TabButton
            active={activeTab === 'settings'}
            onClick={() => setActiveTab('settings')}
            icon={<Settings className="h-4 w-4" />}
            label="設定"
          />
          {/* ===== DEBUG_LOG_START ===== */}
          <TabButton
            active={activeTab === 'network'}
            onClick={() => setActiveTab('network')}
            icon={<Network className="h-4 w-4" />}
            label="Network (Debug)"
          />
          {/* ===== DEBUG_LOG_END ===== */}
        </div>
      </div>

      {/* コンテンツ */}
      {activeTab === 'timeline' && (
        <div className="space-y-6">
          {/* New Workflow Progress View with pattern switching */}
          <WorkflowProgressView
            steps={run.steps}
            currentStep={run.current_step ?? ''}
            waitingApproval={run.status === 'waiting_approval'}
            onApprove={approve}
            onReject={reject}
            onRetry={handleRetry}
          />

          {/* Legacy detail panel (optional - can be removed) */}
          {step && (
            <div className="mt-6">
              <StepDetailPanel step={step} />
            </div>
          )}
        </div>
      )}

      {activeTab === 'artifacts' && (
        <ArtifactViewer runId={id} artifacts={artifacts} />
      )}

      {activeTab === 'events' && (
        <EventsList events={events} />
      )}

      {activeTab === 'settings' && (
        <SettingsPanel run={run} />
      )}

      {/* ===== DEBUG_LOG_START ===== */}
      {activeTab === 'network' && (
        <NetworkDebugPanel runId={id} />
      )}
      {/* ===== DEBUG_LOG_END ===== */}

      {/* ダイアログ */}
      <ApprovalDialog
        isOpen={showApprovalDialog}
        onClose={() => setShowApprovalDialog(false)}
        onApprove={approve}
        onReject={reject}
        runId={id}
      />

      {resumeStep && (
        <ResumeConfirmDialog
          isOpen={true}
          onClose={() => setResumeStep(null)}
          onConfirm={handleResumeConfirm}
          stepName={resumeStep}
          stepLabel={STEP_LABELS[resumeStep] || resumeStep}
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors',
        active
          ? 'border-primary-600 text-primary-600 dark:text-primary-400'
          : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function EventsList({ events }: { events: Array<{ type: string; timestamp: string; message: string }> }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">イベントログ</h3>
      </div>
      <div className="max-h-96 overflow-y-auto">
        {events.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            イベントがありません
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {events.map((event, index) => (
              <div key={index} className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <div className="flex items-center gap-2 text-xs">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded',
                      event.type.includes('completed') && 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
                      event.type.includes('failed') && 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
                      event.type.includes('started') && 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
                      !event.type.includes('completed') &&
                        !event.type.includes('failed') &&
                        !event.type.includes('started') &&
                        'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                    )}
                  >
                    {event.type}
                  </span>
                  <span className="text-gray-400 dark:text-gray-500">
                    {formatDate(event.timestamp)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{event.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SettingsPanel({ run }: { run: { model_config: { platform: string; model: string; options: { grounding?: boolean; temperature?: number } }; tool_config?: { serp_fetch: boolean; page_fetch: boolean; url_verify: boolean; pdf_extract: boolean }; options?: { retry_limit: number; repair_enabled: boolean } } }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Run設定</h3>

      <div className="space-y-6">
        <div>
          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">モデル設定</h4>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">プラットフォーム</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">{run.model_config.platform}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">モデル</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">{run.model_config.model}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Grounding</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {run.model_config.options?.grounding ? '有効' : '無効'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Temperature</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {run.model_config.options?.temperature ?? 0.7}
              </dd>
            </div>
          </dl>
        </div>

        {run.tool_config && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">ツール設定</h4>
            <div className="flex flex-wrap gap-2">
              {run.tool_config.serp_fetch && (
                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
                  SERP取得
                </span>
              )}
              {run.tool_config.page_fetch && (
                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
                  ページ取得
                </span>
              )}
              {run.tool_config.url_verify && (
                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
                  URL検証
                </span>
              )}
              {run.tool_config.pdf_extract && (
                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
                  PDF抽出
                </span>
              )}
            </div>
          </div>
        )}

        {run.options && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">実行オプション</h4>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-gray-500 dark:text-gray-400">リトライ上限</dt>
                <dd className="font-medium text-gray-900 dark:text-gray-100">{run.options.retry_limit}回</dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">決定的修正</dt>
                <dd className="font-medium text-gray-900 dark:text-gray-100">
                  {run.options.repair_enabled ? '有効' : '無効'}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}

// ===== DEBUG_LOG_START =====
import { useEffect, useRef } from 'react';

interface NetworkLog {
  timestamp: string;
  method: string;
  url: string;
  status: number | string;
  duration: number;
  response?: unknown;
  error?: string;
}

function NetworkDebugPanel({ runId }: { runId: string }) {
  const [logs, setLogs] = useState<NetworkLog[]>([]);
  const [polling, setPolling] = useState(false);
  const [interval, setIntervalValue] = useState(2000);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchRunStatus = async () => {
    const start = Date.now();
    try {
      const res = await fetch(`/api/runs/${runId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
      });
      const data = await res.json();
      const duration = Date.now() - start;

      setLogs(prev => [{
        timestamp: new Date().toISOString(),
        method: 'GET',
        url: `/api/runs/${runId}`,
        status: res.status,
        duration,
        response: { status: data.status, current_step: data.current_step, steps: data.steps?.length }
      }, ...prev].slice(0, 50));
    } catch (err) {
      const duration = Date.now() - start;
      setLogs(prev => [{
        timestamp: new Date().toISOString(),
        method: 'GET',
        url: `/api/runs/${runId}`,
        status: 'ERR',
        duration,
        error: String(err)
      }, ...prev].slice(0, 50));
    }
  };

  const fetchHealthDetailed = async () => {
    const start = Date.now();
    try {
      const res = await fetch('/api/health/detailed');
      const data = await res.json();
      const duration = Date.now() - start;

      setLogs(prev => [{
        timestamp: new Date().toISOString(),
        method: 'GET',
        url: '/api/health/detailed',
        status: res.status,
        duration,
        response: data
      }, ...prev].slice(0, 50));
    } catch (err) {
      const duration = Date.now() - start;
      setLogs(prev => [{
        timestamp: new Date().toISOString(),
        method: 'GET',
        url: '/api/health/detailed',
        status: 'ERR',
        duration,
        error: String(err)
      }, ...prev].slice(0, 50));
    }
  };

  useEffect(() => {
    if (polling) {
      intervalRef.current = setInterval(fetchRunStatus, interval);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [polling, interval]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Network Debug Panel</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchRunStatus}
            className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
          >
            Fetch Run
          </button>
          <button
            onClick={fetchHealthDetailed}
            className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
          >
            Health Check
          </button>
          <label className="flex items-center gap-1 text-xs text-gray-700 dark:text-gray-300">
            <input
              type="checkbox"
              checked={polling}
              onChange={(e) => setPolling(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900"
            />
            Auto-poll
          </label>
          <select
            value={interval}
            onChange={(e) => setIntervalValue(Number(e.target.value))}
            className="text-xs border border-gray-300 dark:border-gray-600 rounded px-1 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          >
            <option value={1000}>1s</option>
            <option value={2000}>2s</option>
            <option value={5000}>5s</option>
          </select>
          <button
            onClick={() => setLogs([])}
            className="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            Clear
          </button>
        </div>
      </div>
      <div className="max-h-96 overflow-y-auto font-mono text-xs text-gray-900 dark:text-gray-100">
        {logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No network logs. Click buttons above to fetch.
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900 sticky top-0">
              <tr>
                <th className="px-2 py-1 text-left text-gray-700 dark:text-gray-300">Time</th>
                <th className="px-2 py-1 text-left text-gray-700 dark:text-gray-300">Method</th>
                <th className="px-2 py-1 text-left text-gray-700 dark:text-gray-300">URL</th>
                <th className="px-2 py-1 text-left text-gray-700 dark:text-gray-300">Status</th>
                <th className="px-2 py-1 text-left text-gray-700 dark:text-gray-300">Duration</th>
                <th className="px-2 py-1 text-left text-gray-700 dark:text-gray-300">Response</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, idx) => (
                <tr key={idx} className={cn(
                  'border-t border-gray-100 dark:border-gray-700',
                  log.status === 200 && 'bg-green-50 dark:bg-green-900/30',
                  (log.status === 'ERR' || (typeof log.status === 'number' && log.status >= 400)) && 'bg-red-50 dark:bg-red-900/30'
                )}>
                  <td className="px-2 py-1 whitespace-nowrap">{log.timestamp.split('T')[1]?.slice(0,12)}</td>
                  <td className="px-2 py-1">{log.method}</td>
                  <td className="px-2 py-1 truncate max-w-48">{log.url}</td>
                  <td className="px-2 py-1">{log.status}</td>
                  <td className="px-2 py-1">{log.duration}ms</td>
                  <td className="px-2 py-1 truncate max-w-64">
                    {log.error ? <span className="text-red-600 dark:text-red-400">{log.error}</span> : JSON.stringify(log.response)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
// ===== DEBUG_LOG_END =====
