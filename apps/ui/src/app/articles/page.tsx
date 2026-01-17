"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  RefreshCw,
  Search,
  Inbox,
  FileText,
  Image,
  CheckCircle,
  Clock,
  Github,
  Eye,
} from "lucide-react";
import Link from "next/link";
import type { ArticleSummary } from "@/lib/types";
import { api } from "@/lib/api";
import { ListSkeleton } from "@/components/common/Loading";
import { ErrorMessage } from "@/components/common/ErrorBoundary";
import { HelpButton } from "@/components/common/HelpButton";
import { cn } from "@/lib/utils";

const REVIEW_FILTERS = [
  { value: "all", label: "すべて" },
  { value: "reviewed", label: "レビュー済み" },
  { value: "unreviewed", label: "未レビュー" },
] as const;

type ReviewFilter = (typeof REVIEW_FILTERS)[number]["value"];

export default function ArticlesPage() {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("all");
  const [total, setTotal] = useState(0);

  const isMountedRef = useRef(true);

  const fetchArticles = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const params: {
          keyword?: string;
          has_review?: boolean;
        } = {};

        if (searchKeyword.trim()) {
          params.keyword = searchKeyword.trim();
        }
        if (reviewFilter === "reviewed") {
          params.has_review = true;
        } else if (reviewFilter === "unreviewed") {
          params.has_review = false;
        }

        const response = await api.articles.list(params);
        if (isMountedRef.current) {
          setArticles(response.articles ?? []);
          setTotal(response.total ?? 0);
        }
      } catch (err) {
        if (isMountedRef.current) {
          setError(err instanceof Error ? err.message : "Failed to fetch articles");
          setArticles([]);
        }
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [searchKeyword, reviewFilter]
  );

  useEffect(() => {
    isMountedRef.current = true;
    fetchArticles();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchArticles]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchArticles();
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            作成済み記事
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            完了した記事の管理・レビュー・編集
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <ListSkeleton count={6} />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => fetchArticles()} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            作成済み記事
          </h1>
          <HelpButton helpKey="articles.list" size="sm" />
        </div>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          完了した記事の管理・レビュー・編集
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                placeholder="キーワードで検索..."
                className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-accent-500 focus:border-transparent"
              />
            </div>
          </form>

          {/* Review filter */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 p-1 bg-gray-100 dark:bg-gray-700 rounded-lg">
              {REVIEW_FILTERS.map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => setReviewFilter(filter.value)}
                  className={cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                    reviewFilter === filter.value
                      ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                  )}
                >
                  {filter.label}
                </button>
              ))}
            </div>
            <HelpButton helpKey="articles.status" size="sm" />
          </div>

          {/* Refresh */}
          <button
            onClick={() => fetchArticles(true)}
            disabled={refreshing}
            className="btn btn-ghost"
          >
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            更新
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        {articles.length === 0 ? (
          <EmptyState hasFilter={!!searchKeyword.trim() || reviewFilter !== "all"} />
        ) : (
          <div className="space-y-4">
            {articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}

        {/* Count indicator */}
        {articles.length > 0 && (
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {total}件中 {articles.length}件を表示
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function ArticleCard({ article }: { article: ArticleSummary }) {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Link
      href={`/articles/${article.id}`}
      className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-accent-500 dark:hover:border-accent-400 hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Title/Keyword */}
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
            {article.keyword}
          </h3>

          {/* Metadata */}
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
            {/* Article count */}
            <span className="flex items-center gap-1">
              <FileText className="h-4 w-4" />
              {article.article_count}記事
            </span>

            {/* Images */}
            {article.has_images && (
              <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                <Image className="h-4 w-4" />
                画像あり
              </span>
            )}

            {/* GitHub */}
            {article.github_repo_url && (
              <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                <Github className="h-4 w-4" />
                GitHub連携
              </span>
            )}

            {/* Created date */}
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              {formatDate(article.completed_at || article.created_at)}
            </span>
          </div>
        </div>

        {/* Status badges */}
        <div className="flex flex-col items-end gap-2">
          {/* Review status */}
          {article.review_status === "completed" ? (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/30 rounded-full">
              <CheckCircle className="h-3 w-3" />
              レビュー済み
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 rounded-full">
              未レビュー
            </span>
          )}

          {/* View button */}
          <span className="inline-flex items-center gap-1 text-sm text-accent-600 dark:text-accent-400 font-medium">
            <Eye className="h-4 w-4" />
            詳細を見る
          </span>
        </div>
      </div>
    </Link>
  );
}

function EmptyState({ hasFilter }: { hasFilter: boolean }) {
  return (
    <div className="text-center py-12">
      <div className="flex justify-center mb-4">
        <div className="p-4 bg-gray-100 dark:bg-gray-700 rounded-2xl">
          <Inbox className="h-8 w-8 text-gray-400" />
        </div>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        {hasFilter ? "記事が見つかりません" : "作成済みの記事がありません"}
      </h3>
      <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-sm mx-auto">
        {hasFilter
          ? "検索条件を変更してみてください。"
          : "ワークフローを完了すると、ここに記事が表示されます。"}
      </p>
      {!hasFilter && (
        <Link href="/settings/runs/new" className="btn btn-primary">
          新規Run作成
        </Link>
      )}
    </div>
  );
}
