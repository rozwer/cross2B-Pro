"use client";

import { useMemo, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { ImagePlus, Check, X } from "lucide-react";
import type { ImagePosition, Section } from "@/lib/types";

interface ArticlePreviewWithMarkersProps {
  markdown: string;
  sections: Section[];
  positions: ImagePosition[];
  onAddPosition: (section: Section, position: "before" | "after") => void;
  onRemovePosition: (index: number) => void;
}

/**
 * 記事プレビューコンポーネント（画像挿入マーカー付き）
 *
 * 見出しの前後にクリッカブルなマーカーを表示し、
 * ユーザーが視覚的に画像挿入位置を選択できるようにする
 */
export function ArticlePreviewWithMarkers({
  markdown,
  sections,
  positions,
  onAddPosition,
  onRemovePosition,
}: ArticlePreviewWithMarkersProps) {
  // セクションタイトルと位置からインデックスを検索
  const findPositionIndex = useCallback(
    (sectionTitle: string, pos: "before" | "after"): number => {
      return positions.findIndex(
        (p) => p.section_title === sectionTitle && p.position === pos
      );
    },
    [positions]
  );

  // セクションタイトルから Section オブジェクトを検索
  const findSection = useCallback(
    (title: string): Section | undefined => {
      return sections.find((s) => s.title === title);
    },
    [sections]
  );

  const sizeClasses: Record<number, string> = {
    1: "text-xl font-bold mt-6 mb-3",
    2: "text-lg font-bold mt-5 mb-2",
    3: "text-base font-semibold mt-4 mb-2",
    4: "text-sm font-semibold mt-3 mb-1",
    5: "text-sm font-medium mt-2 mb-1",
    6: "text-xs font-medium mt-2 mb-1",
  };

  // 見出しをラップするヘルパーコンポーネント
  const HeadingWrapper = useCallback(
    ({
      level,
      children,
      className,
    }: {
      level: number;
      children: React.ReactNode;
      className?: string;
    }) => {
      const headingText = extractTextFromChildren(children);
      const section = findSection(headingText);

      const baseClass = sizeClasses[level] || sizeClasses[2];
      const Tag = `h${level}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6";

      if (!section) {
        // セクション一覧に含まれない見出し（タイトルなど）はそのまま表示
        return <Tag className={`${baseClass} ${className || ""}`}>{children}</Tag>;
      }

      const beforeIndex = findPositionIndex(headingText, "before");
      const afterIndex = findPositionIndex(headingText, "after");
      const hasBeforePosition = beforeIndex >= 0;
      const hasAfterPosition = afterIndex >= 0;

      return (
        <div className="relative group">
          {/* Before マーカー */}
          <InsertionMarker
            position="before"
            isSelected={hasBeforePosition}
            positionNumber={hasBeforePosition ? beforeIndex + 1 : undefined}
            onClick={() => {
              if (hasBeforePosition) {
                onRemovePosition(beforeIndex);
              } else {
                onAddPosition(section, "before");
              }
            }}
          />

          {/* 見出し本体 */}
          <Tag
            className={`${baseClass} ${
              hasBeforePosition || hasAfterPosition
                ? "bg-primary-50 dark:bg-primary-900/20 -mx-2 px-2 rounded"
                : ""
            } ${className || ""}`}
          >
            {children}
          </Tag>

          {/* After マーカー */}
          <InsertionMarker
            position="after"
            isSelected={hasAfterPosition}
            positionNumber={hasAfterPosition ? afterIndex + 1 : undefined}
            onClick={() => {
              if (hasAfterPosition) {
                onRemovePosition(afterIndex);
              } else {
                onAddPosition(section, "after");
              }
            }}
          />
        </div>
      );
    },
    [findSection, findPositionIndex, onAddPosition, onRemovePosition]
  );

  // react-markdown 用のカスタムコンポーネント
  const components: Components = useMemo(
    () => ({
      h1: ({ children }) => <HeadingWrapper level={1}>{children}</HeadingWrapper>,
      h2: ({ children }) => <HeadingWrapper level={2}>{children}</HeadingWrapper>,
      h3: ({ children }) => <HeadingWrapper level={3}>{children}</HeadingWrapper>,
      h4: ({ children }) => <HeadingWrapper level={4}>{children}</HeadingWrapper>,
      h5: ({ children }) => <HeadingWrapper level={5}>{children}</HeadingWrapper>,
      h6: ({ children }) => <HeadingWrapper level={6}>{children}</HeadingWrapper>,
      // 以下は MarkdownViewer と同様のスタイリング
      a: ({ href, children, ...props }) => {
        const isExternal = href?.startsWith("http://") || href?.startsWith("https://");
        if (href?.startsWith("javascript:") || href?.startsWith("data:")) {
          return <span className="text-gray-500">{children}</span>;
        }
        return (
          <a
            href={href}
            target={isExternal ? "_blank" : undefined}
            rel={isExternal ? "noopener noreferrer" : undefined}
            className="text-primary-600 hover:underline"
            {...props}
          >
            {children}
          </a>
        );
      },
      pre: ({ children, ...props }) => (
        <pre
          className="p-3 bg-gray-800 text-gray-100 rounded-lg text-xs overflow-auto my-2"
          {...props}
        >
          {children}
        </pre>
      ),
      code: ({ children, className, ...props }) => {
        const isBlock = className?.includes("language-");
        if (isBlock) {
          return (
            <code className={className} {...props}>
              {children}
            </code>
          );
        }
        return (
          <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono" {...props}>
            {children}
          </code>
        );
      },
      ul: ({ children, ...props }) => (
        <ul className="ml-4 list-disc my-2" {...props}>
          {children}
        </ul>
      ),
      ol: ({ children, ...props }) => (
        <ol className="ml-4 list-decimal my-2" {...props}>
          {children}
        </ol>
      ),
      li: ({ children, ...props }) => (
        <li className="my-0.5" {...props}>
          {children}
        </li>
      ),
      p: ({ children, ...props }) => (
        <p className="my-2 text-sm text-gray-700 dark:text-gray-300" {...props}>
          {children}
        </p>
      ),
      blockquote: ({ children, ...props }) => (
        <blockquote
          className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 my-2 italic text-gray-600 dark:text-gray-400"
          {...props}
        >
          {children}
        </blockquote>
      ),
      table: ({ children, ...props }) => (
        <div className="overflow-x-auto my-2">
          <table className="min-w-full border-collapse border border-gray-200 dark:border-gray-700 text-xs" {...props}>
            {children}
          </table>
        </div>
      ),
      thead: ({ children, ...props }) => (
        <thead className="bg-gray-50 dark:bg-gray-800" {...props}>
          {children}
        </thead>
      ),
      tbody: ({ children, ...props }) => <tbody {...props}>{children}</tbody>,
      tr: ({ children, ...props }) => (
        <tr className="border-b border-gray-200 dark:border-gray-700" {...props}>
          {children}
        </tr>
      ),
      th: ({ children, ...props }) => (
        <th
          className="px-2 py-1 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700"
          {...props}
        >
          {children}
        </th>
      ),
      td: ({ children, ...props }) => (
        <td className="px-2 py-1 text-xs border border-gray-200 dark:border-gray-700" {...props}>
          {children}
        </td>
      ),
      hr: ({ ...props }) => <hr className="my-4 border-gray-300 dark:border-gray-600" {...props} />,
      img: ({ src, alt, ...props }) => {
        const isAllowed = src?.startsWith("https://") || src?.startsWith("data:image/");
        if (src && !isAllowed) {
          return (
            <span className="inline-block p-2 bg-gray-100 dark:bg-gray-800 rounded text-gray-400 text-xs">
              [Image blocked]
            </span>
          );
        }
        return (
          <img
            src={src}
            alt={alt || ""}
            className="max-w-full h-auto rounded my-2"
            loading="lazy"
            {...props}
          />
        );
      },
      strong: ({ children, ...props }) => (
        <strong className="font-bold" {...props}>
          {children}
        </strong>
      ),
      em: ({ children, ...props }) => (
        <em className="italic" {...props}>
          {children}
        </em>
      ),
    }),
    [HeadingWrapper]
  );

  if (!markdown) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        記事プレビューを読み込み中...
      </div>
    );
  }

  return (
    <div className="prose prose-sm max-w-none p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-y-auto max-h-[600px]">
      <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-xs text-blue-700 dark:text-blue-300">
        <strong>使い方:</strong> 見出しの上下に表示される「+ 画像を追加」をクリックして挿入位置を選択できます。
        選択済みの位置をクリックすると解除できます。
      </div>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

/**
 * 挿入位置マーカーコンポーネント
 */
interface InsertionMarkerProps {
  position: "before" | "after";
  isSelected: boolean;
  positionNumber?: number;
  onClick: () => void;
}

function InsertionMarker({
  position,
  isSelected,
  positionNumber,
  onClick,
}: InsertionMarkerProps) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full py-1 px-2 my-1 rounded text-xs font-medium
        transition-all duration-150
        flex items-center justify-center gap-1
        ${
          isSelected
            ? "bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 border border-primary-300 dark:border-primary-600"
            : "bg-gray-50 dark:bg-gray-800 text-gray-400 dark:text-gray-500 border border-dashed border-gray-300 dark:border-gray-600 opacity-0 group-hover:opacity-100 hover:bg-primary-50 dark:hover:bg-primary-900/20 hover:text-primary-600 dark:hover:text-primary-400 hover:border-primary-300 dark:hover:border-primary-600"
        }
      `}
      title={
        isSelected
          ? `画像 #${positionNumber} - クリックで削除`
          : `この${position === "before" ? "上" : "下"}に画像を追加`
      }
    >
      {isSelected ? (
        <>
          <Check className="h-3 w-3" />
          <span>画像 #{positionNumber}</span>
          <X className="h-3 w-3 ml-1 opacity-60" />
        </>
      ) : (
        <>
          <ImagePlus className="h-3 w-3" />
          <span>画像を追加</span>
        </>
      )}
    </button>
  );
}

/**
 * React children からテキストを抽出するヘルパー
 */
function extractTextFromChildren(children: React.ReactNode): string {
  if (typeof children === "string") {
    return children;
  }
  if (Array.isArray(children)) {
    return children.map(extractTextFromChildren).join("");
  }
  if (children && typeof children === "object" && "props" in children) {
    return extractTextFromChildren((children as React.ReactElement).props.children);
  }
  return "";
}
