"use client";

import { use, useState, useCallback, useEffect, useRef, useMemo } from "react";
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
  DollarSign,
  X,
  Loader2,
  Pause,
  Play,
} from "lucide-react";
import { useRun } from "@/hooks/useRun";
import { useRunProgress } from "@/hooks/useRunProgress";
import { useArtifacts } from "@/hooks/useArtifact";
import { RunStatusBadge } from "@/components/runs/RunStatusBadge";
import { GitHubFixButton } from "@/components/runs/GitHubFixButton";
import { GitHubFixStatus } from "@/components/runs/GitHubFixStatus";
import { RetryRecommendationBanner } from "@/components/runs/RetryRecommendationBanner";
import { WorkflowProgressView } from "@/components/workflow";
import { StepDetailPanel } from "@/components/steps/StepDetailPanel";
import { ApprovalDialog, type ApprovalType } from "@/components/common/ApprovalDialog";
import { HelpButton } from "@/components/common/HelpButton";
import { Step3ReviewDialog } from "@/components/approval/Step3ReviewDialog";
import { ImageGenerationWizard } from "@/components/imageGeneration";
import { ResumeConfirmDialog } from "@/components/approval/ResumeConfirmDialog";
import { ArtifactViewer } from "@/components/artifacts/ArtifactViewer";
import { LoadingPage } from "@/components/common/Loading";
import { ErrorMessage } from "@/components/common/ErrorBoundary";
import { formatDate } from "@/lib/utils";
import { STEP_LABELS, getStep11Phase, getKeywordFromInput } from "@/lib/types";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type TabType = "timeline" | "artifacts" | "events" | "settings" | "cost";

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
  const [selectedStep, _setSelectedStep] = useState<string | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalType, setApprovalType] = useState<ApprovalType>("step3");  // 承認タイプ
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
  const [_imageGenLoading, setImageGenLoading] = useState(false);
  const [pauseLoading, setPauseLoading] = useState(false);
  const [isPauseRequested, setIsPauseRequested] = useState(false);
  const [showStep3ReviewDialog, setShowStep3ReviewDialog] = useState(false);
  const [stepCompletedCount, setStepCompletedCount] = useState(0);

  const { run, loading, error, fetch, approve, reject, retry, resume, pause, continueRun, isPolling } = useRun(id);

  // 一時停止リクエスト後、実際にpausedになったらフラグをリセット
  useEffect(() => {
    if (run?.status === "paused" && isPauseRequested) {
      setIsPauseRequested(false);
    }
  }, [run?.status, isPauseRequested]);
  const { artifacts, fetch: fetchArtifacts } = useArtifacts(id);

  // 自動ポップアップは無効化 - 手動で開く必要あり
  // useEffect(() => {
  //   if (run?.status === "waiting_image_input" && !showImageGenDialog) {
  //     setShowImageGenDialog(true);
  //   }
  // }, [run?.status, showImageGenDialog]);

  // Ref to access fetchArtifacts in event handler without stale closure
  const fetchArtifactsRef = useRef(fetchArtifacts);
  fetchArtifactsRef.current = fetchArtifacts;

  const { events, wsStatus } = useRunProgress(id, {
    onEvent: (event) => {
      if (
        event.type === "step_completed" ||
        event.type === "step_failed" ||
        event.type === "run_completed"
      ) {
        fetch();
        // Also refresh artifacts when steps complete
        fetchArtifactsRef.current();
        // Increment counter to trigger CostPanel refresh
        setStepCompletedCount((c) => c + 1);
      }
    },
  });

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
    const result = await resume(resumeStep);
    router.push(`/runs/${result.new_run_id}`);
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

  const handleOpenPreview = useCallback(async (articleNumber?: number) => {
    // Use provided articleNumber, fallback to current previewArticle
    const targetArticle = articleNumber ?? previewArticle;
    setPreviewArticle(targetArticle);
    setPreviewModal({ isOpen: true, loading: true, error: null, content: null });
    try {
      const htmlContent = await api.artifacts.getPreview(id, targetArticle);
      setPreviewModal({ isOpen: true, loading: false, error: null, content: htmlContent });
    } catch (err) {
      setPreviewModal({
        isOpen: true,
        loading: false,
        error: err instanceof Error ? err.message : "プレビューの取得に失敗しました",
        content: null,
      });
    }
    // Intentionally exclude previewArticle to avoid stale closure on rapid clicks
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

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

  const handlePause = useCallback(async () => {
    setPauseLoading(true);
    try {
      await pause();
      setIsPauseRequested(true);
    } catch (err) {
      console.error("Pause failed:", err);
    } finally {
      setPauseLoading(false);
    }
  }, [pause]);

  const handleContinue = useCallback(async () => {
    setPauseLoading(true);
    try {
      await continueRun();
    } catch (err) {
      console.error("Continue failed:", err);
    } finally {
      setPauseLoading(false);
    }
  }, [continueRun]);

  // Step3レビュー完了ハンドラー
  const handleStep3ReviewComplete = useCallback(() => {
    setShowStep3ReviewDialog(false);
    fetch(); // ステータスを更新
  }, [fetch]);

  // Step3レビュー待ち状態かどうか判定
  const isWaitingForStep3Review = useCallback(() => {
    if (!run) return false;

    // waiting_approval状態で、かつcurrent_stepがstep3関連の場合
    if (run.status === "waiting_approval") {
      // current_stepがstep3a/3b/3c、waiting_approval、waiting_step3_approval、またはpost_step3のいずれか
      // Note: waiting_approvalは承認待ち状態を表す（ワークフローがこの値を設定）
      const step3RelatedSteps = ["step3a", "step3b", "step3c", "waiting_approval", "waiting_step3_approval", "post_step3"];
      if (step3RelatedSteps.includes(run.current_step ?? "")) {
        return true;
      }

      // Step3a/3b/3cが完了していて、Step4以降がpendingの場合
      const step3a = run.steps.find((s) => s.step_name === "step3a");
      const step3b = run.steps.find((s) => s.step_name === "step3b");
      const step3c = run.steps.find((s) => s.step_name === "step3c");
      const step4 = run.steps.find((s) => s.step_name === "step4");

      const step3Complete =
        step3a?.status === "completed" &&
        step3b?.status === "completed" &&
        step3c?.status === "completed";

      if (step3Complete && (!step4 || step4.status === "pending")) {
        return true;
      }
    }

    return false;
  }, [run]);

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
              <HelpButton helpKey="workflow.overview" size="sm" />
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
            {/* 停止/続行ボタン */}
            {run.status === "running" && (
              <div className="flex items-center gap-2">
                {isPauseRequested ? (
                  <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-md border border-amber-300 dark:border-amber-700">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">このステップが終わったら停止します</span>
                  </div>
                ) : (
                  <button
                    onClick={handlePause}
                    disabled={pauseLoading}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors disabled:opacity-50"
                  >
                    {pauseLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Pause className="h-4 w-4" />
                    )}
                    一時停止
                  </button>
                )}
              </div>
            )}
            {run.status === "paused" && (
              <button
                onClick={handleContinue}
                disabled={pauseLoading}
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors disabled:opacity-50"
              >
                {pauseLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                続行
              </button>
            )}
            {/* 画像生成待ち（step10完了後）の場合は画像生成ボタン */}
            {isWaitingForImageGeneration() ? (
              <button
                onClick={() => setShowImageGenDialog(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                画像を生成
              </button>
            ) : isWaitingForStep3Review() ? (
              /* Step3レビュー待ちの場合はレビューボタン */
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    fetchArtifacts();
                    setShowStep3ReviewDialog(true);
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
                >
                  Step3 レビュー
                </button>
                <HelpButton helpKey="workflow.step3" size="sm" />
              </div>
            ) : run.status === "waiting_step1_approval" ? (
              /* Step1承認待ち（競合取得・関連KW抽出後）の場合 */
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    fetchArtifacts();
                    setApprovalType("step1");
                    setShowApprovalDialog(true);
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition-colors"
                >
                  Step1 承認待ち
                </button>
                <HelpButton helpKey="workflow.approval" size="sm" />
              </div>
            ) : run.status === "waiting_approval" ? (
              /* その他の承認待ちの場合は承認ボタン（Step3）*/
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    fetchArtifacts();  // Ensure artifacts are loaded before showing dialog
                    setApprovalType("step3");
                    setShowApprovalDialog(true);
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition-colors"
                >
                  承認待ち
                </button>
                <HelpButton helpKey="workflow.approval" size="sm" />
              </div>
            ) : run.status === "failed" && run.needs_github_fix ? (
              /* GitHub Fix Guidance: resume後に同一ステップで再失敗した場合 */
              run.fix_issue_number ? (
                <GitHubFixStatus
                  runId={id}
                  issueNumber={run.fix_issue_number}
                />
              ) : (
                <GitHubFixButton
                  runId={id}
                  onIssueCreated={() => fetch()}
                />
              )
            ) : run.status === "failed" && run.retry_recommendation && !run.needs_github_fix ? (
              /* Retry Recommendation: 失敗時の推奨リトライ方法を表示 */
              <RetryRecommendationBanner
                recommendation={run.retry_recommendation}
                onRetry={(step) => retry(step)}
                onResume={(step) => setResumeStep(step)}
              />
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
          <TabButton
            active={activeTab === "cost"}
            onClick={() => setActiveTab("cost")}
            icon={<DollarSign className="h-4 w-4" />}
            label="コスト"
          />
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

      {activeTab === "artifacts" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">成果物</h2>
            <HelpButton helpKey="workflow.artifacts" size="sm" />
          </div>
          <ArtifactViewer
            runId={id}
            artifacts={artifacts}
            githubRepoUrl={run?.github_repo_url}
            githubDirPath={run?.github_dir_path}
          />
        </div>
      )}

      {activeTab === "events" && <EventsList runId={id} wsEvents={events} />}

      {activeTab === "settings" && <SettingsPanel run={run} />}

      {activeTab === "cost" && <CostPanel runId={id} stepCompletedCount={stepCompletedCount} />}

      {/* ダイアログ */}
      <ApprovalDialog
        isOpen={showApprovalDialog}
        onClose={() => setShowApprovalDialog(false)}
        onApprove={handleApprove}
        onReject={handleReject}
        runId={id}
        artifacts={artifacts}
        loading={approvalLoading}
        approvalType={approvalType}
        onApprovalTypeChange={setApprovalType}
      />

      <Step3ReviewDialog
        isOpen={showStep3ReviewDialog}
        onClose={() => setShowStep3ReviewDialog(false)}
        onComplete={handleStep3ReviewComplete}
        runId={id}
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

// Event type categories for filtering and styling
const EVENT_CATEGORIES = {
  success: ["step.succeeded", "run.completed", "validation.passed", "repair.applied", "step_completed", "run_completed"],
  error: ["step.failed", "run.failed", "validation.failed", "repair.failed", "llm.error", "error", "run_failed"],
  retry: ["step.retrying", "step_retrying"],
  started: ["step.started", "run.started", "run.created", "step_started"],
  info: ["run.paused", "run.resumed", "llm.request_sent", "llm.response_received", "approval_requested"],
};

function getEventCategory(eventType: string): keyof typeof EVENT_CATEGORIES | "other" {
  for (const [category, types] of Object.entries(EVENT_CATEGORIES)) {
    if (types.some((t) => eventType.includes(t) || t.includes(eventType))) {
      return category as keyof typeof EVENT_CATEGORIES;
    }
  }
  return "other";
}

function getEventBadgeStyle(eventType: string): string {
  const category = getEventCategory(eventType);
  switch (category) {
    case "success":
      return "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300";
    case "error":
      return "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300";
    case "retry":
      return "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300";
    case "started":
      return "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300";
    case "info":
      return "bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300";
    default:
      return "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300";
  }
}

interface EventsListProps {
  runId: string;
  wsEvents: Array<{ type: string; timestamp: string; message: string; step?: string; attempt?: number; details?: Record<string, unknown> }>;
}

function EventsList({ runId, wsEvents }: EventsListProps) {
  const [filter, setFilter] = useState<string>("all");
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [dbEvents, setDbEvents] = useState<Array<{
    id: string;
    event_type: string;
    step?: string;
    payload: Record<string, unknown>;
    details?: {
      step?: string;
      attempt?: number;
      duration_ms?: number;
      error?: string;
      error_category?: string;
      reason?: string;
    };
    created_at: string;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch DB events on mount
  useEffect(() => {
    const fetchDbEvents = async () => {
      try {
        setLoading(true);
        const events = await api.events.list(runId, { limit: 200 });
        setDbEvents(events);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "イベントの取得に失敗しました");
      } finally {
        setLoading(false);
      }
    };
    fetchDbEvents();
  }, [runId]);

  // Combine and deduplicate events
  const allEvents = useMemo(() => {
    const seenIds = new Set<string>();
    const combined: Array<{
      id: string;
      type: string;
      step?: string;
      message: string;
      timestamp: string;
      attempt?: number;
      duration_ms?: number;
      error?: string;
      error_category?: string;
      reason?: string;
      details?: Record<string, unknown>;
      source: "db" | "ws";
    }> = [];

    // Add DB events first (authoritative)
    for (const e of dbEvents) {
      const id = e.id;
      if (seenIds.has(id)) continue;
      seenIds.add(id);

      combined.push({
        id,
        type: e.event_type,
        step: e.step || e.details?.step as string | undefined,
        message: e.payload?.message as string || formatEventMessage(e.event_type, e.details),
        timestamp: e.created_at,
        attempt: e.details?.attempt,
        duration_ms: e.details?.duration_ms,
        error: e.details?.error,
        error_category: e.details?.error_category,
        reason: e.details?.reason,
        details: e.payload,
        source: "db",
      });
    }

    // Add WS events that aren't in DB yet
    for (const e of wsEvents) {
      const wsId = `ws-${e.timestamp}-${e.type}`;
      // Check for duplicates by timestamp and type combination
      const isDuplicate = combined.some(
        (existing) =>
          Math.abs(new Date(existing.timestamp).getTime() - new Date(e.timestamp).getTime()) < 1000 &&
          existing.type.replace(".", "_") === e.type.replace(".", "_")
      );
      if (isDuplicate) continue;

      combined.push({
        id: wsId,
        type: e.type,
        step: e.step,
        message: e.message,
        timestamp: e.timestamp,
        attempt: e.attempt,
        details: e.details,
        source: "ws",
      });
    }

    // Sort by timestamp (newest first)
    combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    return combined;
  }, [dbEvents, wsEvents]);

  // Filter events
  const filteredEvents = useMemo(() => {
    if (filter === "all") return allEvents;
    return allEvents.filter((e) => getEventCategory(e.type) === filter);
  }, [allEvents, filter]);

  const toggleExpanded = (id: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            イベントログ
            <span className="ml-2 text-xs font-normal text-gray-500">
              ({filteredEvents.length}件)
            </span>
          </h3>
          <div className="flex items-center gap-2">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            >
              <option value="all">すべて</option>
              <option value="success">成功</option>
              <option value="error">エラー</option>
              <option value="retry">リトライ</option>
              <option value="started">開始</option>
              <option value="info">情報</option>
            </select>
            {loading && (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
            )}
          </div>
        </div>
      </div>
      <div className="max-h-[600px] overflow-y-auto">
        {error ? (
          <div className="p-4 text-center text-red-500 dark:text-red-400">
            {error}
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            {loading ? "読み込み中..." : "イベントがありません"}
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {filteredEvents.map((event) => (
              <div
                key={event.id}
                className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                onClick={() => toggleExpanded(event.id)}
              >
                <div className="flex items-center gap-2 text-xs">
                  <span className={cn("px-2 py-0.5 rounded", getEventBadgeStyle(event.type))}>
                    {event.type}
                  </span>
                  {event.step && (
                    <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                      {STEP_LABELS[event.step] || event.step}
                    </span>
                  )}
                  {event.attempt && event.attempt > 1 && (
                    <span className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                      リトライ #{event.attempt}
                    </span>
                  )}
                  {event.duration_ms && (
                    <span className="text-gray-400 dark:text-gray-500">
                      {event.duration_ms}ms
                    </span>
                  )}
                  <span className="text-gray-400 dark:text-gray-500 ml-auto">
                    {formatDate(event.timestamp)}
                  </span>
                  {event.source === "ws" && (
                    <span className="px-1 py-0.5 rounded text-[10px] bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
                      LIVE
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{event.message}</p>

                {/* Expanded details */}
                {expandedEvents.has(event.id) && (
                  <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-900/50 rounded text-xs">
                    {event.error && (
                      <div className="mb-2">
                        <span className="font-semibold text-red-600 dark:text-red-400">エラー: </span>
                        <span className="text-red-600 dark:text-red-400">{event.error}</span>
                        {event.error_category && (
                          <span className="ml-2 text-gray-500">({event.error_category})</span>
                        )}
                      </div>
                    )}
                    {event.reason && (
                      <div className="mb-2">
                        <span className="font-semibold text-gray-600 dark:text-gray-400">理由: </span>
                        <span className="text-gray-600 dark:text-gray-300">{event.reason}</span>
                      </div>
                    )}
                    {event.details && Object.keys(event.details).length > 0 && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                          詳細データ
                        </summary>
                        <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-x-auto text-[10px]">
                          {JSON.stringify(event.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function formatEventMessage(eventType: string, details?: Record<string, unknown>): string {
  const step = details?.step as string | undefined;
  const stepLabel = step ? (STEP_LABELS[step] || step) : "";

  switch (eventType) {
    case "step.started":
      return `${stepLabel} を開始しました`;
    case "step.succeeded":
      return `${stepLabel} が完了しました`;
    case "step.failed":
      return `${stepLabel} が失敗しました: ${details?.error || "不明なエラー"}`;
    case "step.retrying":
      return `${stepLabel} をリトライします (試行 #${details?.attempt || "?"})`;
    case "run.created":
      return "ワークフローを作成しました";
    case "run.started":
      return "ワークフローを開始しました";
    case "run.completed":
      return "ワークフローが完了しました";
    case "run.failed":
      return "ワークフローが失敗しました";
    case "run.paused":
      return "ワークフローを一時停止しました";
    case "run.resumed":
      return "ワークフローを再開しました";
    case "repair.applied":
      return `${stepLabel} の修正を適用しました`;
    case "repair.failed":
      return `${stepLabel} の修正に失敗しました`;
    case "validation.passed":
      return `${stepLabel} の検証に成功しました`;
    case "validation.failed":
      return `${stepLabel} の検証に失敗しました`;
    default:
      return eventType;
  }
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

// コストパネルコンポーネント
import type { CostResponse, CostBreakdown } from "@/lib/types";

interface CostPanelProps {
  runId: string;
  stepCompletedCount?: number; // Increment this to trigger auto-refresh
}

function CostPanel({ runId, stepCompletedCount = 0 }: CostPanelProps) {
  const [costData, setCostData] = useState<CostResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastFetchRef = useRef<number>(0);

  const fetchCost = useCallback(async (force = false) => {
    // Debounce: prevent rapid fetches within 2 seconds (unless forced)
    const now = Date.now();
    if (!force && now - lastFetchRef.current < 2000 && costData) {
      return;
    }
    lastFetchRef.current = now;

    setLoading(true);
    setError(null);
    try {
      const data = await api.cost.get(runId);
      setCostData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "コスト情報の取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [runId, costData]);

  // Initial fetch
  useEffect(() => {
    fetchCost(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // Auto-refresh when step completes
  useEffect(() => {
    if (stepCompletedCount > 0) {
      fetchCost(true);
    }
  }, [stepCompletedCount, fetchCost]);

  const formatCost = (cost: number) => {
    return cost < 0.01 ? `$${cost.toFixed(6)}` : `$${cost.toFixed(4)}`;
  };

  // USD to JPY conversion (approximate rate - can be updated)
  const USD_TO_JPY_RATE = 155;
  const formatCostJPY = (costUSD: number) => {
    const jpy = costUSD * USD_TO_JPY_RATE;
    return jpy < 1 ? `¥${jpy.toFixed(2)}` : `¥${Math.round(jpy).toLocaleString()}`;
  };

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(2)}M`;
    }
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  const getModelColor = (model: string) => {
    if (model.includes("gemini")) return "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300";
    if (model.includes("gpt")) return "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300";
    if (model.includes("claude")) return "bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300";
    return "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300";
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-500 dark:text-gray-400">コスト情報を取得中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="text-center">
          <p className="text-red-500 dark:text-red-400 mb-4">{error}</p>
          <button
            onClick={() => fetchCost(true)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
          >
            再読み込み
          </button>
        </div>
      </div>
    );
  }

  if (!costData || costData.breakdown.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>コスト情報がありません</p>
          <p className="text-sm mt-2">ワークフロー実行後にトークン使用量が表示されます</p>
        </div>
      </div>
    );
  }

  // Check if any thinking tokens are present
  const hasThinkingTokens = costData.total_thinking_tokens > 0;

  return (
    <div className="space-y-6">
      {/* サマリーカード */}
      <div className={cn("grid grid-cols-1 gap-4", hasThinkingTokens ? "md:grid-cols-5" : "md:grid-cols-4")}>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">総コスト</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {formatCost(costData.total_cost)}
          </div>
          <div className="text-sm font-medium text-primary-600 dark:text-primary-400">
            {formatCostJPY(costData.total_cost)}
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">1 USD = ¥{USD_TO_JPY_RATE}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">入力トークン</div>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {formatTokens(costData.total_input_tokens)}
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">
            {costData.total_input_tokens.toLocaleString()} tokens
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">出力トークン</div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {formatTokens(costData.total_output_tokens)}
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">
            {costData.total_output_tokens.toLocaleString()} tokens
          </div>
        </div>
        {hasThinkingTokens && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">推論トークン</div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {formatTokens(costData.total_thinking_tokens)}
            </div>
            <div className="text-xs text-gray-400 dark:text-gray-500">
              {costData.total_thinking_tokens.toLocaleString()} tokens
            </div>
          </div>
        )}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400">使用工程数</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {costData.breakdown.length}
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">steps with LLM usage</div>
        </div>
      </div>

      {/* 工程別内訳 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            工程別コスト内訳
          </h3>
          <button
            onClick={() => fetchCost(true)}
            className="px-3 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" />
            更新
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-gray-500 dark:text-gray-400 font-medium">工程</th>
                <th className="px-4 py-3 text-left text-gray-500 dark:text-gray-400 font-medium">モデル</th>
                <th className="px-4 py-3 text-right text-gray-500 dark:text-gray-400 font-medium">入力</th>
                <th className="px-4 py-3 text-right text-gray-500 dark:text-gray-400 font-medium">出力</th>
                {hasThinkingTokens && (
                  <th className="px-4 py-3 text-right text-gray-500 dark:text-gray-400 font-medium">推論</th>
                )}
                <th className="px-4 py-3 text-right text-gray-500 dark:text-gray-400 font-medium">コスト</th>
              </tr>
            </thead>
            <tbody>
              {costData.breakdown.map((item: CostBreakdown, idx: number) => (
                <tr
                  key={idx}
                  className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                    {STEP_LABELS[item.step] || item.step}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", getModelColor(item.model))}>
                      {item.model}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400 font-mono">
                    {item.input_tokens.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400 font-mono">
                    {item.output_tokens.toLocaleString()}
                  </td>
                  {hasThinkingTokens && (
                    <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400 font-mono">
                      {(item.thinking_tokens || 0).toLocaleString()}
                    </td>
                  )}
                  <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-gray-100 font-mono">
                    {formatCost(item.cost)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 dark:bg-gray-900 font-medium">
              <tr className="border-t-2 border-gray-200 dark:border-gray-600">
                <td className="px-4 py-3 text-gray-900 dark:text-gray-100" colSpan={2}>合計</td>
                <td className="px-4 py-3 text-right text-blue-600 dark:text-blue-400 font-mono">
                  {costData.total_input_tokens.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-green-600 dark:text-green-400 font-mono">
                  {costData.total_output_tokens.toLocaleString()}
                </td>
                {hasThinkingTokens && (
                  <td className="px-4 py-3 text-right text-amber-600 dark:text-amber-400 font-mono">
                    {costData.total_thinking_tokens.toLocaleString()}
                  </td>
                )}
                <td className="px-4 py-3 text-right font-mono">
                  <div className="text-gray-900 dark:text-gray-100">{formatCost(costData.total_cost)}</div>
                  <div className="text-xs text-primary-600 dark:text-primary-400">{formatCostJPY(costData.total_cost)}</div>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
