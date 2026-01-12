"use client";

import { use, useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  Settings,
  Activity,
  FileText,
  Wifi,
  WifiOff,
  Network,
  X,
  Loader2,
} from "lucide-react";
import { useRun } from "@/hooks/useRun";
import { useRunProgress } from "@/hooks/useRunProgress";
import { useArtifacts } from "@/hooks/useArtifact";
import { RunStatusBadge } from "@/components/runs/RunStatusBadge";
import { WorkflowProgressView } from "@/components/workflow";
import { StepDetailPanel } from "@/components/steps/StepDetailPanel";
import { ApprovalDialog } from "@/components/common/ApprovalDialog";
import { ImageGenerationWizard } from "@/components/imageGeneration";
import { ResumeConfirmDialog } from "@/components/approval/ResumeConfirmDialog";
import { ArtifactViewer } from "@/components/artifacts/ArtifactViewer";
import { LoadingPage } from "@/components/common/Loading";
import { ErrorMessage } from "@/components/common/ErrorBoundary";
import { formatDate } from "@/lib/utils";
import { STEP_LABELS, getStep11Phase, getKeywordFromInput } from "@/lib/types";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

// ===== DEBUG_LOG_START =====
type TabType = "timeline" | "artifacts" | "events" | "settings" | "network";
// ===== DEBUG_LOG_END =====

// プレビューモーダル用状態の型
interface PreviewModalState {
  isOpen: boolean;
  loading: boolean;
  error: string | null;
  content: string | null;
}

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  // Next.js 15 では params が Promise の場合がある
  const resolvedParams = params instanceof Promise ? use(params) : params;
  const { id } = resolvedParams;
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>("timeline");
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [resumeStep, setResumeStep] = useState<string | null>(null);
  const [previewModal, setPreviewModal] = useState<PreviewModalState>({
    isOpen: false,
    loading: false,
    error: null,
    content: null,
  });
  const [previewArticle, setPreviewArticle] = useState(1);
  const [showImageGenDialog, setShowImageGenDialog] = useState(false);
  const [imageGenLoading, setImageGenLoading] = useState(false);

  const { run, loading, error, fetch, approve, reject, retry, resume, isPolling } = useRun(id);
  const { events, wsStatus } = useRunProgress(id, {
    onEvent: (event) => {
      if (
        event.type === "step_completed" ||
        event.type === "step_failed" ||
        event.type === "run_completed"
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
        console.error("Retry failed:", err);
      }
    },
    [retry],
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

  const handleApprove = useCallback(async () => {
    setApprovalLoading(true);
    try {
      await approve();
      setShowApprovalDialog(false);
    } catch (err) {
      console.error("Approval failed:", err);
    } finally {
      setApprovalLoading(false);
    }
  }, [approve]);

  const handleReject = useCallback(async (reason: string) => {
    setApprovalLoading(true);
    try {
      await reject(reason);
      setShowApprovalDialog(false);
    } catch (err) {
      console.error("Rejection failed:", err);
    } finally {
      setApprovalLoading(false);
    }
  }, [reject]);

  const handleOpenPreview = useCallback(async (articleNumber: number = previewArticle) => {
    setPreviewArticle(articleNumber);
    setPreviewModal({ isOpen: true, loading: true, error: null, content: null });
    try {
      const htmlContent = await api.artifacts.getPreview(id, articleNumber);
      setPreviewModal({ isOpen: true, loading: false, error: null, content: htmlContent });
    } catch (err) {
      setPreviewModal({
        isOpen: true,
        loading: false,
        error: err instanceof Error ? err.message : "プレビューの取得に失敗しました",
        content: null,
      });
    }
  }, [id, previewArticle]);

  const handleClosePreview = useCallback(() => {
    setPreviewModal({ isOpen: false, loading: false, error: null, content: null });
  }, []);

  // Step11 画像生成完了ハンドラー
  const handleImageGenComplete = useCallback(() => {
    setShowImageGenDialog(false);
    fetch(); // ステータスを更新
  }, [fetch]);

  const handleImageGenSkip = useCallback(async () => {
    setImageGenLoading(true);
    try {
      // waiting_approval状態の場合はTemporalにsignalを送る
      // それ以外（completed等）の場合は直接DBを更新
      if (run?.status === "waiting_approval") {
        await api.runs.skipImageGeneration(id);
      } else {
        await api.runs.completeStep11(id);
      }
      setShowImageGenDialog(false);
      fetch(); // ステータスを更新
    } catch (err) {
      console.error("Skip image generation failed:", err);
    } finally {
      setImageGenLoading(false);
    }
  }, [id, fetch, run?.status]);

  // Step10完了後、画像生成の判断待ち/マルチフェーズ待ちかどうか判定
  const isWaitingForImageGeneration = useCallback(() => {
    if (!run) return false;

    // Runが既に完了・失敗・キャンセルの場合は待機していない
    if (run.status === "completed" || run.status === "failed" || run.status === "cancelled") {
      return false;
    }

    // Step11のマルチフェーズのいずれかで待機中かチェック
    const step11Phase = getStep11Phase(run.current_step);
    if (step11Phase && step11Phase.startsWith("waiting_")) {
      return true;
    }

    // waiting_image_input状態の場合は常に画像生成ダイアログを表示
    if (run.status === "waiting_image_input") {
      return true;
    }

    // ワークフローが waiting_approval で current_step が waiting_image_generation の場合
    if (run.status === "waiting_approval" && run.current_step === "waiting_image_generation") {
      return true;
    }
    // フォールバック: step10完了済み、step11がpending、かつステータスがwaiting_approval
    const step10 = run.steps.find(s => s.step_name === "step10");
    const step11 = run.steps.find(s => s.step_name === "step11");
    return (
      run.status === "waiting_approval" &&
      step10?.status === "completed" &&
      (!step11 || step11.status === "pending")
    );
  }, [run]);

  // 現在のStep11フェーズを取得
  const currentStep11Phase = run ? getStep11Phase(run.current_step) : null;

  if (loading) {
    return <LoadingPage text="Run を読み込み中..." />;
  }

  if (error || !run) {
    return <ErrorMessage message={error || "Run not found"} onRetry={fetch} />;
  }

  const step = run.steps.find((s) => s.step_name === selectedStep);

  return (
    <div>
      {/* ヘッダー */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={() => router.push("/")}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">
                {getKeywordFromInput(run.input)}
              </h1>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
              <span>ID: {run.id.slice(0, 8)}</span>
              <span>作成: {formatDate(run.created_at)}</span>
              <span className="flex items-center gap-1">
                {wsStatus === "connected" ? (
                  <Wifi className="h-4 w-4 text-green-500" />
                ) : (
                  <WifiOff className="h-4 w-4 text-gray-400" />
                )}
                {wsStatus}
              </span>
            </div>
          </div>
          <div className="flex gap-2 items-center">
            {isPolling && (
              <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                自動更新中
              </span>
            )}
            <button
              onClick={() => fetch()}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
            >
              <RefreshCw className={cn("h-4 w-4", isPolling && "animate-spin")} />
              更新
            </button>
            {/* 画像生成待ち（step10完了後）の場合は画像生成ボタン */}
            {isWaitingForImageGeneration() ? (
              <button
                onClick={() => setShowImageGenDialog(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                画像を生成
              </button>
            ) : run.status === "waiting_approval" ? (
              /* step3完了後の承認待ちの場合は承認ボタン */
              <button
                onClick={() => setShowApprovalDialog(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition-colors"
              >
                承認待ち
              </button>
            ) : null}
            {run.status === "completed" && (
              <>
                <button
                  onClick={() => setShowImageGenDialog(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                >
                  画像を追加
                </button>
                <button
                  onClick={() => handleOpenPreview()}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                  プレビュー
                </button>
              </>
            )}
          </div>
        </div>

        {/* タブ */}
        <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
          <TabButton
            active={activeTab === "timeline"}
            onClick={() => setActiveTab("timeline")}
            icon={<Activity className="h-4 w-4" />}
            label="タイムライン"
          />
          <TabButton
            active={activeTab === "artifacts"}
            onClick={() => {
              setActiveTab("artifacts");
              fetchArtifacts();
            }}
            icon={<FileText className="h-4 w-4" />}
            label="成果物"
          />
          <TabButton
            active={activeTab === "events"}
            onClick={() => setActiveTab("events")}
            icon={<Activity className="h-4 w-4" />}
            label={`イベント (${events.length})`}
          />
          <TabButton
            active={activeTab === "settings"}
            onClick={() => setActiveTab("settings")}
            icon={<Settings className="h-4 w-4" />}
            label="設定"
          />
          {/* ===== DEBUG_LOG_START ===== */}
          <TabButton
            active={activeTab === "network"}
            onClick={() => setActiveTab("network")}
            icon={<Network className="h-4 w-4" />}
            label="Network (Debug)"
          />
          {/* ===== DEBUG_LOG_END ===== */}
        </div>
      </div>

      {/* コンテンツ */}
      {activeTab === "timeline" && (
        <div className="space-y-6">
          {/* New Workflow Progress View with pattern switching - 画面いっぱいに表示 */}
          <div className="relative w-screen left-1/2 right-1/2 -ml-[50vw] -mr-[50vw]">
            <div className="px-4 sm:px-6 lg:px-8">
              <WorkflowProgressView
                steps={run.steps}
                currentStep={run.current_step ?? ""}
                runStatus={run.status}
                waitingApproval={run.status === "waiting_approval"}
                waitingImageGeneration={isWaitingForImageGeneration()}
                onApprove={approve}
                onReject={reject}
                onRetry={handleRetry}
                onResumeFrom={handleResume}
                onImageGenerate={() => setShowImageGenDialog(true)}
                onImageGenSkip={handleImageGenSkip}
              />
            </div>
          </div>

          {/* Legacy detail panel (optional - can be removed) */}
          {step && (
            <div className="mt-6">
              <StepDetailPanel step={step} />
            </div>
          )}
        </div>
      )}

      {activeTab === "artifacts" && <ArtifactViewer runId={id} artifacts={artifacts} />}

      {activeTab === "events" && <EventsList events={events} />}

      {activeTab === "settings" && <SettingsPanel run={run} />}

      {/* ===== DEBUG_LOG_START ===== */}
      {activeTab === "network" && <NetworkDebugPanel runId={id} />}
      {/* ===== DEBUG_LOG_END ===== */}

      {/* ダイアログ */}
      <ApprovalDialog
        isOpen={showApprovalDialog}
        onClose={() => setShowApprovalDialog(false)}
        onApprove={handleApprove}
        onReject={handleReject}
        runId={id}
        artifacts={artifacts}
        loading={approvalLoading}
      />

      <ImageGenerationWizard
        isOpen={showImageGenDialog}
        runId={id}
        currentPhase={currentStep11Phase}
        isCompletedRun={run.status === "completed"}
        onClose={() => setShowImageGenDialog(false)}
        onComplete={handleImageGenComplete}
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

      {/* HTMLプレビューモーダル */}
      {previewModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* オーバーレイ */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={handleClosePreview}
          />
          {/* モーダル */}
          <div className="relative w-[90vw] h-[90vh] bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
            {/* ヘッダー */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  HTMLプレビュー
                </h2>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4].map((num) => (
                    <button
                      key={num}
                      onClick={() => handleOpenPreview(num)}
                      disabled={previewModal.loading}
                      className={cn(
                        "px-2 py-1 text-xs rounded-md transition-colors",
                        previewArticle === num
                          ? "bg-primary-600 text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                        previewModal.loading && "opacity-50 cursor-not-allowed",
                      )}
                    >
                      記事{num}
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={handleClosePreview}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
            {/* コンテンツ */}
            <div className="flex-1 overflow-hidden">
              {previewModal.loading && (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                  <span className="ml-2 text-gray-600 dark:text-gray-400">読み込み中...</span>
                </div>
              )}
              {previewModal.error && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <p className="text-red-600 dark:text-red-400 mb-2">{previewModal.error}</p>
                    <button
                      onClick={() => handleOpenPreview(previewArticle)}
                      className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
                    >
                      再試行
                    </button>
                  </div>
                </div>
              )}
              {previewModal.content && (
                <iframe
                  srcDoc={previewModal.content}
                  title="HTML Preview"
                  className="w-full h-full border-0"
                  sandbox="allow-same-origin"
                />
              )}
            </div>
          </div>
        </div>
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
        "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors",
        active
          ? "border-primary-600 text-primary-600 dark:text-primary-400"
          : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function EventsList({
  events,
}: {
  events: Array<{ type: string; timestamp: string; message: string }>;
}) {
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
                      "px-2 py-0.5 rounded",
                      event.type.includes("completed") &&
                        "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300",
                      event.type.includes("failed") &&
                        "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300",
                      event.type.includes("started") &&
                        "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300",
                      !event.type.includes("completed") &&
                        !event.type.includes("failed") &&
                        !event.type.includes("started") &&
                        "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300",
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

const PLATFORM_DISPLAY_NAMES: Record<string, string> = {
  gemini: "Gemini",
  openai: "OpenAI",
  anthropic: "Claude",
};

const PLATFORM_COLORS: Record<string, string> = {
  gemini: "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300",
  openai: "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300",
  anthropic: "bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300",
};

function SettingsPanel({
  run,
}: {
  run: {
    model_config: {
      platform: string;
      model: string;
      options: { grounding?: boolean; temperature?: number };
    };
    step_configs?: Array<{
      step_id: string;
      platform: string;
      model: string;
      temperature: number;
      grounding: boolean;
      retry_limit: number;
      repair_enabled: boolean;
    }>;
    tool_config?: {
      serp_fetch: boolean;
      page_fetch: boolean;
      url_verify: boolean;
      pdf_extract: boolean;
    };
    options?: { retry_limit: number; repair_enabled: boolean };
  };
}) {
  return (
    <div className="space-y-6">
      {/* デフォルトモデル設定 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
          デフォルトモデル設定
        </h3>

        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">プラットフォーム</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              <span
                className={cn(
                  "inline-block px-2 py-0.5 rounded text-xs font-medium",
                  PLATFORM_COLORS[run.model_config.platform] ||
                    "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300",
                )}
              >
                {PLATFORM_DISPLAY_NAMES[run.model_config.platform] || run.model_config.platform}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">モデル</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {run.model_config.model}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Grounding</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {run.model_config.options?.grounding ? "有効" : "無効"}
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

      {/* ステップ別モデル設定 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
          ステップ別モデル設定
        </h3>
        {run.step_configs && run.step_configs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">
                    ステップ
                  </th>
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">
                    プラットフォーム
                  </th>
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">
                    モデル
                  </th>
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">
                    Temperature
                  </th>
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">
                    Grounding
                  </th>
                </tr>
              </thead>
              <tbody>
                {run.step_configs.map((config) => (
                  <tr
                    key={config.step_id}
                    className="border-b border-gray-100 dark:border-gray-700/50"
                  >
                    <td className="py-2 px-3 text-gray-900 dark:text-gray-100 font-medium">
                      {STEP_LABELS[config.step_id] || config.step_id}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={cn(
                          "inline-block px-2 py-0.5 rounded text-xs font-medium",
                          PLATFORM_COLORS[config.platform] ||
                            "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300",
                        )}
                      >
                        {PLATFORM_DISPLAY_NAMES[config.platform] || config.platform}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-gray-700 dark:text-gray-300">{config.model}</td>
                    <td className="py-2 px-3 text-gray-700 dark:text-gray-300">
                      {config.temperature}
                    </td>
                    <td className="py-2 px-3 text-gray-700 dark:text-gray-300">
                      {config.grounding ? "有効" : "無効"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-400 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <p>このRunはステップ別モデル設定なしで作成されました。</p>
            <p className="mt-1">全ステップでデフォルトモデル設定が使用されます。</p>
          </div>
        )}
      </div>

      {/* ツール設定 */}
      {run.tool_config && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
            ツール設定
          </h3>
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

      {/* 実行オプション */}
      {run.options && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
            実行オプション
          </h3>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">リトライ上限</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {run.options.retry_limit}回
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">決定的修正</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {run.options.repair_enabled ? "有効" : "無効"}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

// ===== DEBUG_LOG_START =====
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
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` },
      });
      const data = await res.json();
      const duration = Date.now() - start;

      setLogs((prev) =>
        [
          {
            timestamp: new Date().toISOString(),
            method: "GET",
            url: `/api/runs/${runId}`,
            status: res.status,
            duration,
            response: {
              status: data.status,
              current_step: data.current_step,
              steps: data.steps?.length,
            },
          },
          ...prev,
        ].slice(0, 50),
      );
    } catch (err) {
      const duration = Date.now() - start;
      setLogs((prev) =>
        [
          {
            timestamp: new Date().toISOString(),
            method: "GET",
            url: `/api/runs/${runId}`,
            status: "ERR",
            duration,
            error: String(err),
          },
          ...prev,
        ].slice(0, 50),
      );
    }
  };

  const fetchHealthDetailed = async () => {
    const start = Date.now();
    try {
      const res = await fetch("/api/health/detailed");
      const data = await res.json();
      const duration = Date.now() - start;

      setLogs((prev) =>
        [
          {
            timestamp: new Date().toISOString(),
            method: "GET",
            url: "/api/health/detailed",
            status: res.status,
            duration,
            response: data,
          },
          ...prev,
        ].slice(0, 50),
      );
    } catch (err) {
      const duration = Date.now() - start;
      setLogs((prev) =>
        [
          {
            timestamp: new Date().toISOString(),
            method: "GET",
            url: "/api/health/detailed",
            status: "ERR",
            duration,
            error: String(err),
          },
          ...prev,
        ].slice(0, 50),
      );
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
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Network Debug Panel
        </h3>
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
                <tr
                  key={idx}
                  className={cn(
                    "border-t border-gray-100 dark:border-gray-700",
                    log.status === 200 && "bg-green-50 dark:bg-green-900/30",
                    (log.status === "ERR" ||
                      (typeof log.status === "number" && log.status >= 400)) &&
                      "bg-red-50 dark:bg-red-900/30",
                  )}
                >
                  <td className="px-2 py-1 whitespace-nowrap">
                    {log.timestamp.split("T")[1]?.slice(0, 12)}
                  </td>
                  <td className="px-2 py-1">{log.method}</td>
                  <td className="px-2 py-1 truncate max-w-48">{log.url}</td>
                  <td className="px-2 py-1">{log.status}</td>
                  <td className="px-2 py-1">{log.duration}ms</td>
                  <td className="px-2 py-1 truncate max-w-64">
                    {log.error ? (
                      <span className="text-red-600 dark:text-red-400">{log.error}</span>
                    ) : (
                      JSON.stringify(log.response)
                    )}
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
