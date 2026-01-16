"use client";

import { use, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  FileText,
  Image,
  Code,
  Clock,
  Calendar,
  Github,
  CheckCircle,
  ExternalLink,
  Eye,
  RefreshCw,
  Download,
  MessageSquareText,
  ChevronDown,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ArticleDetail } from "@/lib/types";
import { ListSkeleton } from "@/components/common/Loading";
import { ErrorMessage } from "@/components/common/ErrorBoundary";
import { GitHubActions } from "@/components/artifacts/GitHubActions";
import {
  ReviewResultPanel,
  type ReviewResult,
  type ReviewStatus,
  type ReviewIssue,
} from "@/components/review/ReviewResultPanel";
import { cn } from "@/lib/utils";

type ReviewType = "fact_check" | "seo" | "quality" | "all";

export default function ArticleDetailPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  const resolvedParams = params instanceof Promise ? use(params) : params;
  const { id } = resolvedParams;

  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "preview" | "github">(
    "overview"
  );
  const [articleNumber, setArticleNumber] = useState(1);

  // Review state
  const [showReviewMenu, setShowReviewMenu] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [showReviewPanel, setShowReviewPanel] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const fetchArticle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.articles.get(id);
      setArticle(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "記事の取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchArticle();
  }, [fetchArticle]);

  // Fetch review status
  const fetchReviewStatus = useCallback(async () => {
    try {
      const status = await api.github.getReviewStatus(id, "step10");
      setReviewStatus(status);

      if (status.has_result && status.result_path) {
        const content = await api.artifacts.download(id, `${id}:step10:review.json`);
        if (content && content.content) {
          const result = JSON.parse(content.content) as ReviewResult;
          setReviewResult(result);
        }
      }
    } catch {
      // No review yet
    }
  }, [id]);

  useEffect(() => {
    fetchReviewStatus();
  }, [fetchReviewStatus]);

  // Poll for review status
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
      window.open(response.issue_url, "_blank");
      setReviewStatus({
        status: "in_progress",
        issue_number: response.issue_number,
        issue_url: response.issue_url,
        has_result: false,
        result_path: null,
      });
      setShowReviewPanel(true);
    } catch (err) {
      setReviewError(
        err instanceof Error ? err.message : "レビューの開始に失敗しました"
      );
    } finally {
      setReviewLoading(false);
    }
  };

  const handleEditWithClaude = useCallback((issue: ReviewIssue) => {
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

    navigator.clipboard.writeText(instruction).then(() => {
      alert(
        "編集指示をクリップボードにコピーしました。\nGitHub Issue で Claude Code に送信してください。"
      );
    });
  }, []);

  const handleDownload = useCallback(
    async (step: "step10" | "step11" | "step12") => {
      try {
        const content = await api.articles.getContent(id, step);
        const blob = new Blob([JSON.stringify(content, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${step}_output_${id.slice(0, 8)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "ダウンロードに失敗しました"
        );
      }
    },
    [id]
  );

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-4">
          <Link
            href="/articles"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            記事詳細
          </h1>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <ListSkeleton count={6} />
        </div>
      </div>
    );
  }

  if (error || !article) {
    return <ErrorMessage message={error || "記事が見つかりません"} onRetry={fetchArticle} />;
  }

  const previewUrl = api.artifacts.getPreviewUrl(id, articleNumber);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/articles"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {article.title || article.keyword}
            </h1>
            {article.description && (
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {article.description}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={fetchArticle}
          className="btn btn-ghost"
        >
          <RefreshCw className="h-4 w-4" />
          更新
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4">
          {(["overview", "preview", "github"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                activeTab === tab
                  ? "border-accent-500 text-accent-600 dark:text-accent-400"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              )}
            >
              {tab === "overview" && "概要"}
              {tab === "preview" && "プレビュー"}
              {tab === "github" && "GitHub"}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Metadata Card */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                記事情報
              </h2>
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400">キーワード</dt>
                  <dd className="text-gray-900 dark:text-gray-100 font-medium">
                    {article.keyword}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400">記事数</dt>
                  <dd className="text-gray-900 dark:text-gray-100 font-medium">
                    {article.article_count}記事
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    作成日時
                  </dt>
                  <dd className="text-gray-900 dark:text-gray-100">
                    {formatDate(article.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    完了日時
                  </dt>
                  <dd className="text-gray-900 dark:text-gray-100">
                    {formatDate(article.completed_at)}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Content Availability */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                成果物
              </h2>
              <div className="space-y-3">
                {/* Step 10 - Markdown */}
                <div
                  className={cn(
                    "flex items-center justify-between p-3 rounded-lg",
                    article.has_step10
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-gray-50 dark:bg-gray-700"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <FileText
                      className={cn(
                        "h-5 w-5",
                        article.has_step10
                          ? "text-green-600 dark:text-green-400"
                          : "text-gray-400"
                      )}
                    />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Step 10: Markdown記事
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        記事本文（マークダウン形式）
                      </p>
                    </div>
                  </div>
                  {article.has_step10 && (
                    <button
                      onClick={() => handleDownload("step10")}
                      className="btn btn-ghost btn-sm"
                    >
                      <Download className="h-4 w-4" />
                      DL
                    </button>
                  )}
                </div>

                {/* Step 11 - Images */}
                <div
                  className={cn(
                    "flex items-center justify-between p-3 rounded-lg",
                    article.has_step11
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-gray-50 dark:bg-gray-700"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Image
                      className={cn(
                        "h-5 w-5",
                        article.has_step11
                          ? "text-green-600 dark:text-green-400"
                          : "text-gray-400"
                      )}
                    />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Step 11: 画像生成
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        AI生成画像
                      </p>
                    </div>
                  </div>
                  {article.has_step11 && (
                    <button
                      onClick={() => handleDownload("step11")}
                      className="btn btn-ghost btn-sm"
                    >
                      <Download className="h-4 w-4" />
                      DL
                    </button>
                  )}
                </div>

                {/* Step 12 - WordPress HTML */}
                <div
                  className={cn(
                    "flex items-center justify-between p-3 rounded-lg",
                    article.has_step12
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-gray-50 dark:bg-gray-700"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Code
                      className={cn(
                        "h-5 w-5",
                        article.has_step12
                          ? "text-green-600 dark:text-green-400"
                          : "text-gray-400"
                      )}
                    />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Step 12: WordPress HTML
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        WordPress用HTML
                      </p>
                    </div>
                  </div>
                  {article.has_step12 && (
                    <button
                      onClick={() => handleDownload("step12")}
                      className="btn btn-ghost btn-sm"
                    >
                      <Download className="h-4 w-4" />
                      DL
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Review Status */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                レビュー
              </h2>

              {/* Review Status Badge */}
              <div className="mb-4">
                {article.review_status === "completed" ? (
                  <span className="inline-flex items-center gap-1 px-3 py-1 text-sm font-medium text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/30 rounded-full">
                    <CheckCircle className="h-4 w-4" />
                    レビュー済み
                  </span>
                ) : reviewStatus?.status === "in_progress" ? (
                  <span className="inline-flex items-center gap-1 px-3 py-1 text-sm font-medium text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/30 rounded-full">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    レビュー中
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-3 py-1 text-sm font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 rounded-full">
                    未レビュー
                  </span>
                )}
              </div>

              {/* Review Actions */}
              <div className="relative">
                <button
                  onClick={() => setShowReviewMenu(!showReviewMenu)}
                  disabled={reviewLoading || !article.has_step10}
                  className="w-full btn btn-primary"
                >
                  {reviewLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <MessageSquareText className="h-4 w-4" />
                  )}
                  Claude でレビュー
                  <ChevronDown className="h-4 w-4 ml-auto" />
                </button>

                {showReviewMenu && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10">
                    <button
                      onClick={() => handleReview("all")}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 font-medium"
                    >
                      総合レビュー
                    </button>
                    <hr className="border-gray-200 dark:border-gray-700" />
                    <button
                      onClick={() => handleReview("fact_check")}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      ファクトチェック
                    </button>
                    <button
                      onClick={() => handleReview("seo")}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      SEO最適化
                    </button>
                    <button
                      onClick={() => handleReview("quality")}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      文章品質
                    </button>
                  </div>
                )}
              </div>

              {/* Review Error */}
              {reviewError && (
                <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded text-sm text-red-600 dark:text-red-400">
                  {reviewError}
                </div>
              )}

              {/* Review Result Button */}
              {(reviewStatus?.has_result || reviewResult) && (
                <button
                  onClick={() => setShowReviewPanel(!showReviewPanel)}
                  className={cn(
                    "w-full mt-3 btn",
                    reviewResult?.passed
                      ? "btn-ghost text-green-600 dark:text-green-400"
                      : "btn-ghost text-amber-600 dark:text-amber-400"
                  )}
                >
                  {reviewResult?.passed ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  レビュー結果を見る
                </button>
              )}
            </div>

            {/* Quick Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                クイックアクション
              </h2>
              <div className="space-y-2">
                <button
                  onClick={() => setActiveTab("preview")}
                  className="w-full btn btn-ghost justify-start"
                >
                  <Eye className="h-4 w-4" />
                  プレビューを表示
                </button>
                <Link
                  href={`/runs/${id}`}
                  className="w-full btn btn-ghost justify-start"
                >
                  <ExternalLink className="h-4 w-4" />
                  Run詳細を開く
                </Link>
                {article.github_repo_url && (
                  <a
                    href={article.github_repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full btn btn-ghost justify-start"
                  >
                    <Github className="h-4 w-4" />
                    GitHubで開く
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "preview" && (
        <div className="space-y-4">
          {/* Preview Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {Array.from({ length: article.article_count }, (_, i) => i + 1).map(
                (num) => (
                  <button
                    key={num}
                    onClick={() => setArticleNumber(num)}
                    className={cn(
                      "px-3 py-1.5 text-sm rounded-md transition-colors",
                      articleNumber === num
                        ? "bg-accent-600 text-white"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                    )}
                  >
                    記事{num}
                  </button>
                )
              )}
            </div>
            <div className="flex items-center gap-2">
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost"
              >
                <ExternalLink className="h-4 w-4" />
                新しいタブで開く
              </a>
            </div>
          </div>

          {/* Preview iframe */}
          <div className="flex gap-4">
            <div
              className={cn(
                "flex-1 bg-white border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden",
                showReviewPanel && reviewResult ? "w-2/3" : "w-full"
              )}
            >
              <iframe
                src={previewUrl}
                title="Article Preview"
                className="w-full h-[calc(100vh-300px)] bg-white"
                sandbox="allow-same-origin allow-scripts"
              />
            </div>

            {/* Review Result Panel */}
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
      )}

      {activeTab === "github" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            GitHub連携
          </h2>

          {article.github_repo_url ? (
            <div className="space-y-6">
              {/* Repo Info */}
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Github className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    リポジトリ
                  </span>
                </div>
                <a
                  href={article.github_repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-600 dark:text-accent-400 hover:underline"
                >
                  {article.github_repo_url}
                </a>
                {article.github_dir_path && (
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    ディレクトリ: {article.github_dir_path}
                  </p>
                )}
              </div>

              {/* Step 10 Actions */}
              {article.has_step10 && (
                <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
                    Step 10: Markdown記事
                  </h3>
                  <GitHubActions
                    runId={id}
                    step="step10"
                    githubRepoUrl={article.github_repo_url}
                    githubDirPath={article.github_dir_path ?? undefined}
                  />
                </div>
              )}

              {/* Step 12 Actions */}
              {article.has_step12 && (
                <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
                    Step 12: WordPress HTML
                  </h3>
                  <GitHubActions
                    runId={id}
                    step="step12"
                    githubRepoUrl={article.github_repo_url}
                    githubDirPath={article.github_dir_path ?? undefined}
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="flex justify-center mb-4">
                <div className="p-4 bg-gray-100 dark:bg-gray-700 rounded-2xl">
                  <Github className="h-8 w-8 text-gray-400" />
                </div>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                GitHub未連携
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-sm mx-auto">
                この記事はGitHubリポジトリと連携されていません。
                Run詳細ページからGitHub連携を設定してください。
              </p>
              <Link href={`/runs/${id}`} className="btn btn-primary">
                Run詳細へ
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
