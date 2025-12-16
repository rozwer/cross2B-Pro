import { RunCreateForm } from '@/components/runs/RunCreateForm';

export default function NewRunPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">新規Run作成</h1>
        <p className="text-sm text-gray-500 mt-1">
          SEO記事生成の設定を入力してください
        </p>
      </div>
      <RunCreateForm />
    </div>
  );
}
