"use client";

export default function RunError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h2 className="text-xl font-bold text-red-600 mb-4">エラーが発生しました</h2>
      <pre className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-sm overflow-auto whitespace-pre-wrap mb-4">
        {error.message}
      </pre>
      {error.stack && (
        <details className="mb-4">
          <summary className="cursor-pointer text-sm text-gray-500">スタックトレース</summary>
          <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg text-xs overflow-auto whitespace-pre-wrap mt-2">
            {error.stack}
          </pre>
        </details>
      )}
      <button
        onClick={reset}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        再試行
      </button>
    </div>
  );
}
