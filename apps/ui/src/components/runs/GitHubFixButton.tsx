"use client";

import { useState } from "react";
import { Github, Loader2, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface GitHubFixButtonProps {
  runId: string;
  onIssueCreated?: (issueUrl: string, issueNumber: number) => void;
  className?: string;
}

/**
 * GitHub Fix Button Component
 *
 * Displayed when a workflow fails after resume on the same step.
 * Creates a GitHub issue with @claude mention for automated fixing.
 */
export function GitHubFixButton({
  runId,
  onIssueCreated,
  className,
}: GitHubFixButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [issueUrl, setIssueUrl] = useState<string | null>(null);

  const handleCreateIssue = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.github.createFixIssue(runId);
      setIssueUrl(result.issue_url);
      onIssueCreated?.(result.issue_url, result.issue_number);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Issue作成に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  // Issue created - show link
  if (issueUrl) {
    return (
      <a
        href={issueUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "inline-flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors",
          className
        )}
      >
        <Github className="h-4 w-4" />
        Issue を確認
        <ExternalLink className="h-3 w-3" />
      </a>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        onClick={handleCreateIssue}
        disabled={loading}
        className={cn(
          "inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
          className
        )}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Github className="h-4 w-4" />
        )}
        @claude に修正依頼
      </button>
      {error && (
        <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
