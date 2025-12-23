"use client";

/**
 * Markdown Viewer Component
 *
 * VULN-007: セキュリティ改善
 * - react-markdown でレンダリング（dangerouslySetInnerHTML 不使用）
 * - リンクの javascript:/data: スキームをブロック
 * - 画像は HTTPS のみ許可
 * - 外部リンクは noopener/noreferrer 付与
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface MarkdownViewerProps {
  content: string;
}

/**
 * Secure Markdown viewer using react-markdown
 *
 * Security:
 * - react-markdown は dangerouslySetInnerHTML を使用しない
 * - 全てのコンテンツが React コンポーネントとしてレンダリング
 * - 危険な URI スキームをブロック
 */
export function MarkdownViewer({ content }: MarkdownViewerProps) {
  // Custom components for styling and security
  const components: Components = {
    // Security: External links open in new tab with proper rel attributes
    a: ({ href, children, ...props }) => {
      const isExternal = href?.startsWith("http://") || href?.startsWith("https://");
      // Block dangerous URI schemes
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
    // Code blocks with syntax highlighting container
    pre: ({ children, ...props }) => (
      <pre
        className="p-3 bg-gray-800 text-gray-100 rounded-lg text-xs overflow-auto my-2"
        {...props}
      >
        {children}
      </pre>
    ),
    // Inline code
    code: ({ children, className, ...props }) => {
      // Check if this is a code block (has language class) or inline
      const isBlock = className?.includes("language-");
      if (isBlock) {
        return (
          <code className={className} {...props}>
            {children}
          </code>
        );
      }
      return (
        <code className="px-1 py-0.5 bg-gray-100 rounded text-xs font-mono" {...props}>
          {children}
        </code>
      );
    },
    // Headings
    h1: ({ children, ...props }) => (
      <h1 className="text-xl font-bold mt-4 mb-2" {...props}>
        {children}
      </h1>
    ),
    h2: ({ children, ...props }) => (
      <h2 className="text-lg font-bold mt-3 mb-2" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }) => (
      <h3 className="text-base font-bold mt-2 mb-1" {...props}>
        {children}
      </h3>
    ),
    h4: ({ children, ...props }) => (
      <h4 className="text-sm font-bold mt-2 mb-1" {...props}>
        {children}
      </h4>
    ),
    h5: ({ children, ...props }) => (
      <h5 className="text-sm font-semibold mt-1 mb-1" {...props}>
        {children}
      </h5>
    ),
    h6: ({ children, ...props }) => (
      <h6 className="text-sm font-medium mt-1 mb-1" {...props}>
        {children}
      </h6>
    ),
    // Lists
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
    // Paragraphs
    p: ({ children, ...props }) => (
      <p className="my-1" {...props}>
        {children}
      </p>
    ),
    // Blockquote
    blockquote: ({ children, ...props }) => (
      <blockquote className="border-l-4 border-gray-300 pl-4 my-2 italic text-gray-600" {...props}>
        {children}
      </blockquote>
    ),
    // Table elements (GFM)
    table: ({ children, ...props }) => (
      <div className="overflow-x-auto my-2">
        <table className="min-w-full border-collapse border border-gray-200" {...props}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children, ...props }) => (
      <thead className="bg-gray-50" {...props}>
        {children}
      </thead>
    ),
    tbody: ({ children, ...props }) => <tbody {...props}>{children}</tbody>,
    tr: ({ children, ...props }) => (
      <tr className="border-b border-gray-200" {...props}>
        {children}
      </tr>
    ),
    th: ({ children, ...props }) => (
      <th
        className="px-3 py-2 text-left text-xs font-semibold text-gray-700 border border-gray-200"
        {...props}
      >
        {children}
      </th>
    ),
    td: ({ children, ...props }) => (
      <td className="px-3 py-2 text-xs border border-gray-200" {...props}>
        {children}
      </td>
    ),
    // Horizontal rule
    hr: ({ ...props }) => <hr className="my-4 border-gray-300" {...props} />,
    // Images - sanitize src (allow HTTPS and data: URLs for Base64 images)
    img: ({ src, alt, ...props }) => {
      // Allow https images and data: URLs (for Base64 embedded images)
      const isAllowed =
        src?.startsWith("https://") ||
        src?.startsWith("data:image/");

      if (src && !isAllowed) {
        return (
          <span className="inline-block p-2 bg-gray-100 rounded text-gray-400 text-xs">
            [Image blocked: insecure source]
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
    // Strong/Bold
    strong: ({ children, ...props }) => (
      <strong className="font-bold" {...props}>
        {children}
      </strong>
    ),
    // Emphasis/Italic
    em: ({ children, ...props }) => (
      <em className="italic" {...props}>
        {children}
      </em>
    ),
    // Strikethrough (GFM)
    del: ({ children, ...props }) => (
      <del className="line-through text-gray-500" {...props}>
        {children}
      </del>
    ),
  };

  return (
    <div className="prose prose-sm max-w-none p-4 bg-white rounded-lg">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
