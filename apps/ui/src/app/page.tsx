"use client";

import { Activity, CheckCircle, Clock, XCircle, TrendingUp } from "lucide-react";
import { RunList } from "@/components/runs/RunList";
import { useRuns } from "@/hooks/useRuns";

export default function Home() {
  const { runs, loading } = useRuns();

  // Calculate statistics
  const stats = {
    total: runs.length,
    completed: runs.filter((r) => r.status === "completed").length,
    running: runs.filter((r) => r.status === "running").length,
    waiting: runs.filter(
      (r) => r.status === "waiting_approval" || r.status === "waiting_image_input"
    ).length,
    failed: runs.filter((r) => r.status === "failed").length,
  };

  const successRate = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">ダッシュボード</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          SEO記事生成ワークフローの管理
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {loading ? "-" : stats.total}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">総実行数</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {loading ? "-" : stats.completed}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">完了</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {loading ? "-" : stats.running + stats.waiting}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">進行中</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {loading ? "-" : stats.failed}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">失敗</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {loading ? "-" : `${successRate}%`}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">成功率</p>
            </div>
          </div>
        </div>
      </div>

      {/* Run List */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">実行履歴</h2>
        </div>
        <RunList />
      </div>
    </div>
  );
}
