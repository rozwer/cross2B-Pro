import { RunList } from '@/components/runs/RunList';

export default function RunsPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Runs</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          SEO記事生成の実行一覧
        </p>
      </div>
      <RunList />
    </div>
  );
}
