"use client";

import { useState, useEffect, useCallback } from "react";
import { Github, ExternalLink, Loader2, Check, Clock, GitPullRequest } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface GitHubFixStatusProps {
  runId: string;
  issueNumber: number;
  className?: string;
}

type IssueStatus = "open" | "in_progress" | "closed";

interface FixIssueStatus {
  issue_number: number;
  state: string;
  status: string;
  pr_url: string | null;
  last_comment: string | null;
  issue_url: string;
}

/**
 * GitHub Fix Status Component
 *
 * Polls the fix issue status every 10 seconds and displays
 * the current state (open, in_progress, closed).
 * Stops polling when the issue is closed.
 */
export function GitHubFixStatus({
  runId,
  issueNumber: _issueNumber,
  className,
}: GitHubFixStatusProps) {
  // Note: _issueNumber is passed for prop interface consistency but we use the status from API
  const [status, setStatus] = useState<FixIssueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const result = await api.github.getFixIssueStatus(runId);
      setStatus(result);
      setError(null);
      return result.state === "closed"; // Return true if should stop polling
    } catch (err) {
      setError(err instanceof Error ? err.message : "ステータス取得に失敗しました");
      return false;
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    // Initial fetch
    fetchStatus();

    // Poll every 10 seconds
    const interval = setInterval(async () => {
      const shouldStop = await fetchStatus();
      if (shouldStop) {
        clearInterval(interval);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [fetchStatus]);

  const getStatusBadge = (issueStatus: IssueStatus) => {
    switch (issueStatus) {
      case "open":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300">
            <Clock className="h-3 w-3" />
            待機中
          </span>
        );
      case "in_progress":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
            <Loader2 className="h-3 w-3 animate-spin" />
            修正中
          </span>
        );
      case "closed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">
            <Check className="h-3 w-3" />
            完了
          </span>
        );
    }
  };

  if (loading && !status) {
    return (
      <div className={cn("flex items-center gap-2 text-gray-500", className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        ステータスを取得中...
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("text-sm text-red-500", className)}>
        {error}
      </div>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center gap-3">
        <Github className="h-5 w-5 text-gray-600 dark:text-gray-400" />
        <a
          href={status.issue_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
        >
          Issue #{status.issue_number}
          <ExternalLink className="h-3 w-3" />
        </a>
        {getStatusBadge(status.status as IssueStatus)}
        {loading && <Loader2 className="h-3 w-3 animate-spin text-gray-400" />}
      </div>

      {status.pr_url && (
        <div className="flex items-center gap-2 text-sm">
          <GitPullRequest className="h-4 w-4 text-green-600 dark:text-green-400" />
          <a
            href={status.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-green-600 dark:text-green-400 hover:underline flex items-center gap-1"
          >
            Pull Request
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}

      {status.last_comment && (
        <div className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md">
          最新コメント: {status.last_comment}
        </div>
      )}
    </div>
  );
}
