"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  Loader2,
  CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { ImagePosition, Section, GeneratedImage, Step11Phase } from "@/lib/types";
import {
  Phase11A_Settings,
  Phase11B_Positions,
  Phase11C_Instructions,
  Phase11D_Review,
  Phase11E_Preview,
} from "./phases";

interface ImageGenerationWizardProps {
  isOpen: boolean;
  runId: string;
  currentPhase: Step11Phase | null;
  /** completed状態のRunから画像を追加する場合はtrue */
  isCompletedRun?: boolean;
  onClose: () => void;
  onComplete: () => void;
}

interface WizardState {
  phase: Step11Phase;
  loading: boolean;
  error: string | null;
  // Phase data
  settings: { imageCount: number; positionRequest: string } | null;
  positions: ImagePosition[];
  sections: Section[];
  analysisSummary: string;
  confirmedPositions: ImagePosition[];
  images: GeneratedImage[];
  warnings: string[];
  previewHtml: string;
  previewAvailable: boolean;
}

const PHASE_LABELS: Record<Step11Phase, string> = {
  waiting_11A: "設定入力",
  "11B_analyzing": "位置分析中",
  waiting_11B: "位置確認",
  waiting_11C: "画像指示",
  "11D_generating": "画像生成中",
  waiting_11D: "画像確認",
  "11E_inserting": "挿入中",
  waiting_11E: "プレビュー確認",
  completed: "完了",
  skipped: "スキップ",
};

const PHASE_STEPS: Step11Phase[] = [
  "waiting_11A",
  "waiting_11B",
  "waiting_11C",
  "waiting_11D",
  "waiting_11E",
];

export function ImageGenerationWizard({
  isOpen,
  runId,
  currentPhase,
  isCompletedRun = false,
  onClose,
  onComplete,
}: ImageGenerationWizardProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const prevPhaseRef = useRef<Step11Phase | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<WizardState>({
    phase: currentPhase || "waiting_11A",
    loading: false,
    error: null,
    settings: null,
    positions: [],
    sections: [],
    analysisSummary: "",
    confirmedPositions: [],
    images: [],
    warnings: [],
    previewHtml: "",
    previewAvailable: false,
  });

  // Update phase when currentPhase prop changes
  useEffect(() => {
    if (currentPhase) {
      setState((prev) => ({ ...prev, phase: currentPhase }));
    }
  }, [currentPhase]);

  // Dialog open/close
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  // ダイアログが開いたときにDBから状態を復元
  const hasLoadedStateRef = useRef(false);
  useEffect(() => {
    if (!isOpen || hasLoadedStateRef.current) return;

    const loadState = async () => {
      try {
        setState((prev) => ({ ...prev, loading: true }));
        const data = await api.runs.getStep11State(runId);

        // DBの状態からUIフェーズにマッピング
        const phaseMap: Record<string, Step11Phase> = {
          idle: "waiting_11A",
          "11A": "waiting_11A",
          "11B": "waiting_11B",
          "11C": "waiting_11C",
          "11D": "waiting_11D",
          "11E": "waiting_11E",
          completed: "completed",
          skipped: "skipped",
        };

        const uiPhase = phaseMap[data.phase] || currentPhase || "waiting_11A";

        setState((prev) => ({
          ...prev,
          loading: false,
          phase: uiPhase,
          settings: data.settings
            ? { imageCount: data.settings.image_count, positionRequest: data.settings.position_request }
            : null,
          positions: data.positions,
          sections: data.sections,
          analysisSummary: data.analysis_summary,
          images: data.images,
          warnings: [],
          error: data.error,
        }));

        hasLoadedStateRef.current = true;
      } catch (err) {
        console.warn("Failed to load step11 state:", err);
        setState((prev) => ({ ...prev, loading: false }));
        hasLoadedStateRef.current = true;
      }
    };

    loadState();
  }, [isOpen, runId, currentPhase]);

  // ダイアログが閉じたらフラグをリセット
  useEffect(() => {
    if (!isOpen) {
      hasLoadedStateRef.current = false;
    }
  }, [isOpen]);

  // Fetch data based on current phase (only when phase actually changes)
  useEffect(() => {
    if (!isOpen) return;
    // Skip if phase hasn't changed to prevent infinite loop
    if (prevPhaseRef.current === state.phase) return;
    prevPhaseRef.current = state.phase;

    // Cancel any in-flight request
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const fetchPhaseData = async () => {
      try {
        switch (state.phase) {
          case "waiting_11B": {
            // すでにpositionsがあればスキップ（戻るボタンで戻った場合）
            if (state.positions.length > 0) break;
            setState((prev) => ({ ...prev, loading: true }));
            const data = await api.runs.getStep11Positions(runId);
            if (abortController.signal.aborted) return;
            setState((prev) => ({
              ...prev,
              loading: false,
              positions: data.positions,
              sections: data.sections,
              analysisSummary: data.analysis_summary,
            }));
            break;
          }
          case "waiting_11D": {
            // すでにimagesがあればスキップ（戻るボタンで戻った場合）
            if (state.images.length > 0) break;
            setState((prev) => ({ ...prev, loading: true }));
            const data = await api.runs.getStep11Images(runId);
            if (abortController.signal.aborted) return;
            setState((prev) => ({
              ...prev,
              loading: false,
              images: data.images,
              warnings: data.warnings,
            }));
            break;
          }
          case "waiting_11E": {
            // すでにpreviewHtmlがあればスキップ（戻るボタンで戻った場合）
            if (state.previewHtml) break;
            setState((prev) => ({ ...prev, loading: true }));
            const data = await api.runs.getStep11Preview(runId);
            if (abortController.signal.aborted) return;
            setState((prev) => ({
              ...prev,
              loading: false,
              previewHtml: data.preview_html,
              previewAvailable: data.preview_available,
            }));
            break;
          }
        }
      } catch (err) {
        if (abortController.signal.aborted) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : "データの取得に失敗しました",
        }));
      }
    };

    fetchPhaseData();

    return () => {
      abortController.abort();
    };
  }, [isOpen, state.phase, runId]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === dialogRef.current && !state.loading) {
      onClose();
    }
  };

  // Phase handlers
  const handleSettingsSubmit = useCallback(
    async (settings: { imageCount: number; positionRequest: string }) => {
      setState((prev) => ({ ...prev, loading: true, error: null, settings }));
      try {
        if (isCompletedRun) {
          // completed Runの場合は addImagesToRun を使用
          await api.runs.addImagesToRun(runId, {
            image_count: settings.imageCount,
            position_request: settings.positionRequest,
          });
        } else {
          // 通常のワークフロー中の場合は submitStep11Settings を使用
          await api.runs.submitStep11Settings(runId, {
            image_count: settings.imageCount,
            position_request: settings.positionRequest,
          });
        }
        setState((prev) => ({ ...prev, loading: false, phase: "11B_analyzing" }));
        // Polling to wait for analysis completion would happen here
        // For now, we'll assume WebSocket will update the phase
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : "設定の送信に失敗しました",
        }));
      }
    },
    [runId, isCompletedRun]
  );

  const handleSkip = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      await api.runs.skipImageGeneration(runId);
      setState((prev) => ({ ...prev, loading: false, phase: "skipped" }));
      onComplete();
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "スキップに失敗しました",
      }));
    }
  }, [runId, onComplete]);

  const handlePositionsConfirm = useCallback(
    async (positions: ImagePosition[]) => {
      setState((prev) => ({ ...prev, loading: true, error: null, confirmedPositions: positions }));
      try {
        await api.runs.submitPositionReview(runId, {
          approved: true,
          modified_positions: positions,
        });
        setState((prev) => ({ ...prev, loading: false, phase: "waiting_11C" }));
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : "位置確認の送信に失敗しました",
        }));
      }
    },
    [runId]
  );

  const handlePositionsReanalyze = useCallback(
    async (request: string) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        await api.runs.submitPositionReview(runId, {
          approved: false,
          reanalyze: true,
          reanalyze_request: request,
        });
        setState((prev) => ({ ...prev, loading: false, phase: "11B_analyzing" }));
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : "再分析リクエストに失敗しました",
        }));
      }
    },
    [runId]
  );

  const handleInstructionsSubmit = useCallback(
    async (instructions: Array<{ index: number; instruction: string }>) => {
      // 新規生成を選んだ場合は画像をクリアして生成
      setState((prev) => ({ ...prev, loading: true, error: null, images: [], previewHtml: "" }));
      try {
        await api.runs.submitImageInstructions(runId, { instructions });
        setState((prev) => ({ ...prev, loading: false, phase: "11D_generating" }));
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : "指示の送信に失敗しました",
        }));
      }
    },
    [runId]
  );

  const handleImagesReview = useCallback(
    async (
      reviews: Array<{
        index: number;
        accepted: boolean;
        retry?: boolean;
        retryInstruction?: string;
      }>
    ) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const hasRetries = reviews.some((r) => r.retry);
        await api.runs.submitImageReview(runId, {
          reviews: reviews.map((r) => ({
            index: r.index,
            accepted: r.accepted,
            retry: r.retry,
            retry_instruction: r.retryInstruction,
          })),
        });
        if (hasRetries) {
          // リトライがある場合は画像生成中に戻る
          setState((prev) => ({ ...prev, loading: false, phase: "11D_generating" }));
        } else {
          // リトライがない場合はプレビューを取得して次へ
          const previewData = await api.runs.getStep11Preview(runId);
          setState((prev) => ({
            ...prev,
            loading: false,
            phase: "waiting_11E",
            previewHtml: previewData.preview_html,
            previewAvailable: previewData.preview_available,
          }));
        }
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : "レビューの送信に失敗しました",
        }));
      }
    },
    [runId]
  );

  const handleFinalize = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      await api.runs.finalizeStep11(runId, { confirmed: true });
      setState((prev) => ({ ...prev, loading: false, phase: "completed" }));
      onComplete();
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "完了処理に失敗しました",
      }));
    }
  }, [runId, onComplete]);

  const handleRestartFrom = useCallback(
    async (phase: string, clearImages: boolean = false) => {
      // 11D に戻る場合、または画像を保持したまま戻る場合は API を呼ばない
      if (phase === "11D") {
        setState((prev) => ({ ...prev, phase: "waiting_11D" }));
        return;
      }

      // 画像をクリアして再生成する場合のみ API を呼ぶ
      if (clearImages) {
        setState((prev) => ({ ...prev, loading: true, error: null }));
        try {
          await api.runs.finalizeStep11(runId, {
            confirmed: false,
            restart_from: phase,
          });
          setState((prev) => ({
            ...prev,
            loading: false,
            phase: phase === "11C" ? "waiting_11C" : "waiting_11A",
            images: [], // 画像をクリア
            previewHtml: "", // プレビューもクリア
          }));
        } catch (err) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: err instanceof Error ? err.message : "再開に失敗しました",
          }));
        }
      } else {
        // 画像を保持したまま戻る
        const phaseMap: Record<string, Step11Phase> = {
          "11A": "waiting_11A",
          "11B": "waiting_11B",
          "11C": "waiting_11C",
          "11D": "waiting_11D",
          "11E": "waiting_11E",
        };
        setState((prev) => ({
          ...prev,
          phase: phaseMap[phase] || "waiting_11C",
        }));
      }
    },
    [runId]
  );

  const handleBack = useCallback(() => {
    // Navigate to previous phase
    const currentIndex = PHASE_STEPS.indexOf(state.phase);
    if (currentIndex > 0) {
      setState((prev) => ({ ...prev, phase: PHASE_STEPS[currentIndex - 1] }));
    }
  }, [state.phase]);

  if (!isOpen) return null;

  const currentStepIndex = PHASE_STEPS.indexOf(state.phase);

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 w-full max-w-2xl p-0 bg-transparent backdrop:bg-black/50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl overflow-hidden">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">画像生成</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {PHASE_LABELS[state.phase]}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={state.loading}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* 進捗インジケーター */}
        <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            {PHASE_STEPS.map((step, index) => {
              const isActive = index === currentStepIndex;
              const isCompleted = index < currentStepIndex;
              const stepLabel = ["設定", "位置", "指示", "確認", "完了"][index];

              return (
                <div key={step} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                        isCompleted
                          ? "bg-green-500 text-white"
                          : isActive
                            ? "bg-primary-600 text-white"
                            : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                      )}
                    >
                      {isCompleted ? (
                        <CheckCircle className="h-4 w-4" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    <span
                      className={cn(
                        "text-xs mt-1",
                        isActive
                          ? "text-primary-600 dark:text-primary-400 font-medium"
                          : "text-gray-500 dark:text-gray-400"
                      )}
                    >
                      {stepLabel}
                    </span>
                  </div>
                  {index < PHASE_STEPS.length - 1 && (
                    <div
                      className={cn(
                        "w-12 h-0.5 mx-2",
                        isCompleted
                          ? "bg-green-500"
                          : "bg-gray-200 dark:bg-gray-700"
                      )}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* エラー表示 */}
        {state.error && (
          <div className="px-6 py-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
            {state.error}
          </div>
        )}

        {/* コンテンツ */}
        <div className="p-6">
          {/* ローディング中の表示（分析中・生成中など） */}
          {(state.phase === "11B_analyzing" ||
            state.phase === "11D_generating" ||
            state.phase === "11E_inserting") && (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <Loader2 className="h-12 w-12 animate-spin text-primary-600" />
              <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
                {state.phase === "11B_analyzing" && "位置を分析中..."}
                {state.phase === "11D_generating" && "画像を生成中..."}
                {state.phase === "11E_inserting" && "画像を挿入中..."}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                しばらくお待ちください
              </p>
            </div>
          )}

          {/* Phase 11A: 設定入力 */}
          {state.phase === "waiting_11A" && (
            <Phase11A_Settings
              onSubmit={handleSettingsSubmit}
              onSkip={handleSkip}
              loading={state.loading}
            />
          )}

          {/* Phase 11B: 位置確認 */}
          {state.phase === "waiting_11B" && (
            <Phase11B_Positions
              positions={state.positions}
              sections={state.sections}
              analysisSummary={state.analysisSummary}
              onConfirm={handlePositionsConfirm}
              onReanalyze={handlePositionsReanalyze}
              onBack={handleBack}
              loading={state.loading}
            />
          )}

          {/* Phase 11C: 画像指示 */}
          {state.phase === "waiting_11C" && (
            <Phase11C_Instructions
              positions={state.confirmedPositions.length > 0 ? state.confirmedPositions : state.positions}
              onSubmit={handleInstructionsSubmit}
              onBack={handleBack}
              hasExistingImages={state.images.length > 0}
              onUseExistingImages={() => setState((prev) => ({ ...prev, phase: "waiting_11D" }))}
              loading={state.loading}
            />
          )}

          {/* Phase 11D: 画像確認 */}
          {state.phase === "waiting_11D" && (
            <Phase11D_Review
              runId={runId}
              images={state.images}
              warnings={state.warnings}
              maxRetries={3}
              onSubmit={handleImagesReview}
              onBack={handleBack}
              onRestartFrom={handleRestartFrom}
              loading={state.loading}
            />
          )}

          {/* Phase 11E: プレビュー確認 */}
          {state.phase === "waiting_11E" && (
            <Phase11E_Preview
              previewHtml={state.previewHtml}
              previewAvailable={state.previewAvailable}
              onComplete={handleFinalize}
              onRestartFrom={handleRestartFrom}
              loading={state.loading}
            />
          )}
        </div>
      </div>
    </dialog>
  );
}
