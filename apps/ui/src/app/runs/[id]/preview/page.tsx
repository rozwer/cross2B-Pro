"use client";

import { use, useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  ExternalLink,
  Maximize2,
  Minimize2,
  MessageSquareText,
  ChevronDown,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  Download,
  Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  ReviewResultPanel,
  type ReviewResult,
  type ReviewStatus,
  type ReviewIssue,
} from "@/components/review/ReviewResultPanel";

type ReviewType = "fact_check" | "seo" | "quality" | "all";

export default function PreviewPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  const resolvedParams = params instanceof Promise ? use(params) : params;
  const { id } = resolvedParams;
  const [fullscreen, setFullscreen] = useState(false);
  const [article, setArticle] = useState(1);
  const previewUrl = api.artifacts.getPreviewUrl(id, article);

  // Review state
  const [showReviewMenu, setShowReviewMenu] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [showReviewPanel, setShowReviewPanel] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Upload state
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [invalidateCache, setInvalidateCache] = useState(false);

  // Fetch review status on mount
  const fetchReviewStatus = useCallback(async () => {
    try {
      const status = await api.github.getReviewStatus(id, "step10");
      setReviewStatus(status);

      // Use result directly from API response if available (from GitHub or storage)
      if (status.result) {
        setReviewResult(status.result as ReviewResult);
      } else if (status.has_result && status.result_path) {
        // Fallback: try to download from storage
        try {
          const content = await api.artifacts.download(id, `${id}:step10:review.json`);
          if (content && content.content) {
            const result = JSON.parse(content.content) as ReviewResult;
            setReviewResult(result);
          }
        } catch {
          // Storage download failed, but we might still have the result from GitHub
        }
      }
    } catch {
      // No review yet, that's OK
    }
  }, [id]);

  useEffect(() => {
    fetchReviewStatus();
  }, [fetchReviewStatus]);

  // Poll for review status when in progress
  useEffect(() => {
    if (reviewStatus?.status === "in_progress") {
      const interval = setInterval(fetchReviewStatus, 30000);
      return () => clearInterval(interval);
    }
  }, [reviewStatus?.status, fetchReviewStatus]);

  const handleReview = async (type: ReviewType) => {
    setShowReviewMenu(false);
    setReviewLoading(true);
    setReviewError(null);

    try {
      const response = await api.github.createReview(id, "step10", type);

      // Open issue in new tab
      window.open(response.issue_url, "_blank");

      // Update status
      setReviewStatus({
        status: "in_progress",
        issue_number: response.issue_number,
        issue_url: response.issue_url,
        has_result: false,
        result_path: null,
      });

      setShowReviewPanel(true);
    } catch (error) {
      setReviewError(
        error instanceof Error ? error.message : "レビューの開始に失敗しました"
      );
    } finally {
      setReviewLoading(false);
    }
  };

  const handleEditWithClaude = useCallback(
    (issue: ReviewIssue) => {
      // Build edit instruction from the issue
      const instruction = `
## 編集依頼

**対象箇所**: ${issue.location}
**カテゴリ**: ${issue.category}
**問題**: ${issue.issue}

### 現在のテキスト
${issue.original}

### 修正案
${issue.suggestion}

上記の問題を修正してください。
      `.trim();

      // For now, copy to clipboard and show a message
      navigator.clipboard.writeText(instruction).then(() => {
        alert(
          "編集指示をクリップボードにコピーしました。\nGitHub Issue で Claude Code に送信してください。"
        );
      });
    },
    []
  );

  // Download artifact
  const handleDownload = useCallback(async () => {
    try {
      const content = await api.artifacts.download(id, `${id}:step10:output.json`);
      const blob = new Blob([content.content], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `step10_output_${id.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "ダウンロードに失敗しました"
      );
    }
  }, [id]);

  // Handle file upload
  const handleFileUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      setUploadLoading(true);
      setUploadError(null);
      setUploadSuccess(null);

      try {
        const content = await file.text();

        // Validate JSON
        try {
          JSON.parse(content);
        } catch {
          throw new Error("無効なJSONファイルです");
        }

        const result = await api.artifacts.upload(id, "step10", content, {
          invalidateCache,
        });

        setUploadSuccess(
          `アップロード完了${result.cache_invalidated ? "（キャッシュ無効化済み）" : ""}`
        );
        setShowUploadDialog(false);

        // Reload preview
        const iframe = document.querySelector("iframe");
        if (iframe) {
          iframe.src = iframe.src;
        }
      } catch (error) {
        setUploadError(
          error instanceof Error ? error.message : "アップロードに失敗しました"
        );
      } finally {
        setUploadLoading(false);
        // Reset file input
        event.target.value = "";
      }
    },
    [id, invalidateCache]
  );

  return (
    <div className={fullscreen ? "fixed inset-0 z-50 bg-white" : ""}>
      {/* ヘッダー */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <a
            href={`/runs/${id}`}
            className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </a>
          <h1 className="text-lg font-semibold text-gray-900">プレビュー</h1>
          <span className="text-sm text-gray-500">Run ID: {id.slice(0, 8)}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* 記事選択 */}
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4].map((num) => (
              <button
                key={num}
                onClick={() => setArticle(num)}
                className={
                  article === num
                    ? "px-2 py-1 text-xs rounded-md bg-primary-600 text-white"
                    : "px-2 py-1 text-xs rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200"
                }
              >
                記事{num}
              </button>
            ))}
          </div>

          {/* レビューボタン */}
          <div className="relative">
            <button
              onClick={() => setShowReviewMenu(!showReviewMenu)}
              disabled={reviewLoading}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-purple-600 hover:bg-purple-50 rounded-md transition-colors disabled:opacity-50"
            >
              {reviewLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <MessageSquareText className="h-4 w-4" />
              )}
              Claude でレビュー
              <ChevronDown className="h-3 w-3" />
            </button>

            {showReviewMenu && (
              <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                <button
                  onClick={() => handleReview("all")}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 font-medium"
                >
                  総合レビュー
                </button>
                <hr className="border-gray-100" />
                <button
                  onClick={() => handleReview("fact_check")}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                >
                  ファクトチェック
                </button>
                <button
                  onClick={() => handleReview("seo")}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                >
                  SEO最適化
                </button>
                <button
                  onClick={() => handleReview("quality")}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                >
                  文章品質
                </button>
              </div>
            )}
          </div>

          {/* レビュー結果表示ボタン */}
          {(reviewStatus?.has_result || reviewResult) && (
            <button
              onClick={() => setShowReviewPanel(!showReviewPanel)}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors ${
                reviewResult?.passed
                  ? "text-green-600 hover:bg-green-50"
                  : "text-amber-600 hover:bg-amber-50"
              }`}
            >
              {reviewResult?.passed ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              レビュー結果
            </button>
          )}

          {/* ダウンロード・アップロードボタン */}
          <div className="flex items-center gap-1 border-l border-gray-200 pl-2 ml-1">
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
              title="JSONファイルをダウンロード"
            >
              <Download className="h-4 w-4" />
              DL
            </button>
            <button
              onClick={() => setShowUploadDialog(true)}
              disabled={uploadLoading}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50"
              title="編集したJSONファイルをアップロード"
            >
              {uploadLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              UL
            </button>
          </div>

          <button
            onClick={() => setFullscreen(!fullscreen)}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          >
            {fullscreen ? (
              <>
                <Minimize2 className="h-4 w-4" />
                縮小
              </>
            ) : (
              <>
                <Maximize2 className="h-4 w-4" />
                拡大
              </>
            )}
          </button>
          <a
            href={previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            新しいタブで開く
          </a>
        </div>
      </div>

      {/* アップロードダイアログ */}
      {showUploadDialog && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">成果物をアップロード</h2>
              <button
                onClick={() => setShowUploadDialog(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              編集したJSONファイルを選択してアップロードしてください。
              既存のファイルはバックアップされます。
            </p>
            <div className="mb-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={invalidateCache}
                  onChange={(e) => setInvalidateCache(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span>次回実行時に再生成する（キャッシュ無効化）</span>
              </label>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                チェックすると、このステップを再実行した際に新たに生成されます
              </p>
            </div>
            <label className="block">
              <span className="sr-only">ファイルを選択</span>
              <input
                type="file"
                accept=".json"
                onChange={handleFileUpload}
                disabled={uploadLoading}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100
                  disabled:opacity-50"
              />
            </label>
          </div>
        </div>
      )}

      {/* エラー表示 */}
      {(reviewError || uploadError) && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center justify-between">
          <span className="text-sm text-red-600">{reviewError || uploadError}</span>
          <button
            onClick={() => {
              setReviewError(null);
              setUploadError(null);
            }}
            className="text-red-400 hover:text-red-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 成功表示 */}
      {uploadSuccess && (
        <div className="bg-green-50 border-b border-green-200 px-4 py-2 flex items-center justify-between">
          <span className="text-sm text-green-600">{uploadSuccess}</span>
          <button
            onClick={() => setUploadSuccess(null)}
            className="text-green-400 hover:text-green-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* レビュー進行中バナー */}
      {reviewStatus?.status === "in_progress" && !reviewResult && (
        <div className="bg-purple-50 border-b border-purple-200 px-4 py-2 flex items-center gap-3">
          <Loader2 className="h-4 w-4 animate-spin text-purple-600" />
          <span className="text-sm text-purple-700">
            Claude がレビュー中です...{" "}
            {reviewStatus.issue_url && (
              <a
                href={reviewStatus.issue_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                Issue #{reviewStatus.issue_number} を確認
              </a>
            )}
          </span>
        </div>
      )}

      {/* レビュー完了（結果なし）バナー */}
      {reviewStatus?.status === "completed" &&
        !reviewStatus?.has_result &&
        !reviewResult && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center gap-3">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <span className="text-sm text-amber-700">
              レビューは完了しましたが、結果ファイルが見つかりません。{" "}
              {reviewStatus.issue_url && (
                <a
                  href={reviewStatus.issue_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline inline-flex items-center gap-1"
                >
                  Issue #{reviewStatus.issue_number} を確認
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </span>
          </div>
        )}

      <div className="flex">
        {/* プレビュー iframe */}
        <div
          className={`${
            showReviewPanel && reviewResult ? "w-2/3" : "w-full"
          } transition-all ${
            fullscreen
              ? "h-[calc(100vh-57px)]"
              : "h-[calc(100vh-180px)] mt-4 border border-gray-200 rounded-lg overflow-hidden"
          }`}
        >
          <iframe
            src={previewUrl}
            title="Article Preview"
            className="w-full h-full bg-white"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>

        {/* レビュー結果パネル */}
        {showReviewPanel && reviewResult && (
          <ReviewResultPanel
            reviewResult={reviewResult}
            reviewStatus={reviewStatus}
            onClose={() => setShowReviewPanel(false)}
            onEditWithClaude={handleEditWithClaude}
          />
        )}
      </div>
    </div>
  );
}
