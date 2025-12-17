'use client';

import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { RunCreateForm } from '@/components/runs/RunCreateForm';

export default function NewRunPage() {
  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/runs"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Run一覧
        </Link>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
          新規Run作成
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          SEO記事生成の設定を入力してください
        </p>
      </div>

      <RunCreateForm />
    </div>
  );
}
