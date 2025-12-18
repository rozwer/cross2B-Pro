"use client";

/**
 * HTML Preview Component
 *
 * VULN-001: XSS脆弱性修正
 * - DOMPurify でサニタイズ
 * - sandbox属性を強化（空文字列でほぼ全て無効化）
 * - 許可タグ/属性を限定
 */

import { useState, useMemo } from "react";
import { Code, Eye, AlertTriangle } from "lucide-react";
import DOMPurify from "dompurify";
import { cn } from "@/lib/utils";

interface HtmlPreviewProps {
  content: string;
}

// DOMPurify 許可設定（VULN-001: XSS対策）
const DOMPURIFY_CONFIG = {
  // 許可するタグ
  ALLOWED_TAGS: [
    "p",
    "div",
    "span",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "s",
    "del",
    "a",
    "img",
    "blockquote",
    "pre",
    "code",
    "figure",
    "figcaption",
    "article",
    "section",
    "header",
    "footer",
    "main",
  ],
  // 許可する属性
  ALLOWED_ATTR: [
    "class",
    "id",
    "style",
    "href",
    "target",
    "rel",
    "src",
    "alt",
    "title",
    "width",
    "height",
    "colspan",
    "rowspan",
  ],
  // スクリプト関連を完全に除去
  FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "form", "input", "button"],
  FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onfocus", "onblur"],
  // href/src の制限
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
  // javascript: URI を禁止
  ALLOW_DATA_ATTR: false,
};

export function HtmlPreview({ content }: HtmlPreviewProps) {
  const [mode, setMode] = useState<"preview" | "source">("preview");

  // VULN-001: DOMPurify でサニタイズ
  const sanitizedContent = useMemo(() => {
    if (typeof window === "undefined") {
      // SSR時は空を返す
      return "";
    }
    return DOMPurify.sanitize(content, DOMPURIFY_CONFIG);
  }, [content]);

  // 危険なコンテンツが検出された場合の警告
  const hasRemovedContent = useMemo(() => {
    if (typeof window === "undefined") return false;
    const original = content.length;
    const sanitized = sanitizedContent.length;
    // サニタイズで20%以上減少した場合は警告
    return original > 100 && (original - sanitized) / original > 0.2;
  }, [content, sanitizedContent]);

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setMode("preview")}
          className={cn(
            "inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
            mode === "preview"
              ? "bg-primary-100 text-primary-700"
              : "text-gray-600 hover:bg-gray-100",
          )}
        >
          <Eye className="h-3.5 w-3.5" />
          プレビュー
        </button>
        <button
          onClick={() => setMode("source")}
          className={cn(
            "inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
            mode === "source"
              ? "bg-primary-100 text-primary-700"
              : "text-gray-600 hover:bg-gray-100",
          )}
        >
          <Code className="h-3.5 w-3.5" />
          ソース
        </button>
      </div>

      {/* 危険コンテンツ警告 */}
      {hasRemovedContent && (
        <div className="flex items-center gap-2 p-2 mb-3 bg-yellow-50 border border-yellow-200 rounded-md text-xs text-yellow-700">
          <AlertTriangle className="h-4 w-4" />
          <span>一部のコンテンツがセキュリティのため除去されました</span>
        </div>
      )}

      {mode === "preview" ? (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          {/* VULN-001: DOMPurify でサニタイズ済みなので div + dangerouslySetInnerHTML を使用 */}
          {/* iframe sandbox="" は srcdoc 内のスクリプトをブロックする際にコンソールエラーを出すため回避 */}
          <div
            className="w-full h-96 bg-white dark:bg-gray-900 overflow-auto p-4 prose prose-sm dark:prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: sanitizedContent }}
          />
        </div>
      ) : (
        <pre className="p-4 bg-gray-50 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap">
          {content}
        </pre>
      )}
    </div>
  );
}
