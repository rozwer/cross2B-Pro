"use client";

import { use, useState } from "react";
import { ArrowLeft, ExternalLink, Maximize2, Minimize2 } from "lucide-react";
import { api } from "@/lib/api";

export default function PreviewPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  // Next.js 15 では params が Promise の場合がある
  const resolvedParams = params instanceof Promise ? use(params) : params;
  const { id } = resolvedParams;
  const [fullscreen, setFullscreen] = useState(false);
  const previewUrl = api.artifacts.getPreviewUrl(id);

  return (
    <div className={fullscreen ? "fixed inset-0 z-50 bg-white" : ""}>
      {/* ヘッダー */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <a href={`/runs/${id}`} className="p-2 hover:bg-gray-100 rounded-md transition-colors">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </a>
          <h1 className="text-lg font-semibold text-gray-900">プレビュー</h1>
          <span className="text-sm text-gray-500">Run ID: {id.slice(0, 8)}</span>
        </div>
        <div className="flex gap-2">
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

      {/* プレビュー iframe */}
      <div
        className={
          fullscreen
            ? "h-[calc(100vh-57px)]"
            : "h-[calc(100vh-180px)] mt-4 border border-gray-200 rounded-lg overflow-hidden"
        }
      >
        <iframe
          src={previewUrl}
          title="Article Preview"
          className="w-full h-full bg-white"
          sandbox="allow-same-origin allow-scripts"
        />
      </div>
    </div>
  );
}
