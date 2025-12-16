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
} from 'lucide-react';
import { useRun } from '@/hooks/useRun';
import { useRunProgress } from '@/hooks/useRunProgress';
import { useArtifacts } from '@/hooks/useArtifact';
import { RunStatusBadge } from '@/components/runs/RunStatusBadge';
import { StepTimeline } from '@/components/steps/StepTimeline';
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

type TabType = 'timeline' | 'artifacts' | 'events' | 'settings';

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
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
            className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 truncate">
                {run.keyword}
              </h1>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
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
              className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
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
        <div className="flex gap-2 border-b border-gray-200">
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
        </div>
      </div>

      {/* コンテンツ */}
      {activeTab === 'timeline' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <StepTimeline
              steps={run.steps}
              currentStep={run.current_step}
              waitingApproval={run.status === 'waiting_approval'}
              onRetry={handleRetry}
              onResume={handleResume}
            />
          </div>
          <div className="lg:col-span-2">
            {step ? (
              <StepDetailPanel step={step} />
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-500">
                タイムラインからステップを選択してください
              </div>
            )}
          </div>
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
          ? 'border-primary-600 text-primary-600'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function EventsList({ events }: { events: Array<{ type: string; timestamp: string; message: string }> }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">イベントログ</h3>
      </div>
      <div className="max-h-96 overflow-y-auto">
        {events.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            イベントがありません
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {events.map((event, index) => (
              <div key={index} className="p-3 hover:bg-gray-50">
                <div className="flex items-center gap-2 text-xs">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded',
                      event.type.includes('completed') && 'bg-green-100 text-green-700',
                      event.type.includes('failed') && 'bg-red-100 text-red-700',
                      event.type.includes('started') && 'bg-blue-100 text-blue-700',
                      !event.type.includes('completed') &&
                        !event.type.includes('failed') &&
                        !event.type.includes('started') &&
                        'bg-gray-100 text-gray-700'
                    )}
                  >
                    {event.type}
                  </span>
                  <span className="text-gray-400">
                    {formatDate(event.timestamp)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600">{event.message}</p>
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
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Run設定</h3>

      <div className="space-y-6">
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-2">モデル設定</h4>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">プラットフォーム</dt>
              <dd className="font-medium">{run.model_config.platform}</dd>
            </div>
            <div>
              <dt className="text-gray-500">モデル</dt>
              <dd className="font-medium">{run.model_config.model}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Grounding</dt>
              <dd className="font-medium">
                {run.model_config.options?.grounding ? '有効' : '無効'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Temperature</dt>
              <dd className="font-medium">
                {run.model_config.options?.temperature ?? 0.7}
              </dd>
            </div>
          </dl>
        </div>

        {run.tool_config && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 mb-2">ツール設定</h4>
            <div className="flex flex-wrap gap-2">
              {run.tool_config.serp_fetch && (
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                  SERP取得
                </span>
              )}
              {run.tool_config.page_fetch && (
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                  ページ取得
                </span>
              )}
              {run.tool_config.url_verify && (
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                  URL検証
                </span>
              )}
              {run.tool_config.pdf_extract && (
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                  PDF抽出
                </span>
              )}
            </div>
          </div>
        )}

        {run.options && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 mb-2">実行オプション</h4>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-gray-500">リトライ上限</dt>
                <dd className="font-medium">{run.options.retry_limit}回</dd>
              </div>
              <div>
                <dt className="text-gray-500">決定的修正</dt>
                <dd className="font-medium">
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
