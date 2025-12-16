'use client';

/**
 * Markdown Viewer Component
 *
 * VULN-007: セキュリティ改善
 * - 入力のサニタイズ（HTMLエンティティエスケープ）
 * - dangerouslySetInnerHTML 不使用
 *
 * TODO: react-markdown + rehype-sanitize に置き換えることを推奨
 *   npm install react-markdown rehype-sanitize
 */

interface MarkdownViewerProps {
  content: string;
}

/**
 * HTMLエンティティをエスケープ（VULN-007: XSS対策）
 */
function escapeHtml(text: string): string {
  const htmlEscapes: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return text.replace(/[&<>"']/g, (char) => htmlEscapes[char] || char);
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
  // シンプルなMarkdownレンダリング（見出し、リスト、コード）
  const renderMarkdown = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeContent: string[] = [];

    lines.forEach((line, index) => {
      // コードブロックの開始/終了
      if (line.startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre
              key={`code-${index}`}
              className="p-3 bg-gray-800 text-gray-100 rounded-lg text-xs overflow-auto my-2"
            >
              {codeContent.join('\n')}
            </pre>
          );
          codeContent = [];
        }
        inCodeBlock = !inCodeBlock;
        return;
      }

      if (inCodeBlock) {
        codeContent.push(line);
        return;
      }

      // 見出し（VULN-007: エスケープ）
      if (line.startsWith('# ')) {
        elements.push(
          <h1 key={index} className="text-xl font-bold mt-4 mb-2">
            {escapeHtml(line.slice(2))}
          </h1>
        );
        return;
      }
      if (line.startsWith('## ')) {
        elements.push(
          <h2 key={index} className="text-lg font-bold mt-3 mb-2">
            {escapeHtml(line.slice(3))}
          </h2>
        );
        return;
      }
      if (line.startsWith('### ')) {
        elements.push(
          <h3 key={index} className="text-base font-bold mt-2 mb-1">
            {escapeHtml(line.slice(4))}
          </h3>
        );
        return;
      }

      // リスト（VULN-007: エスケープ）
      if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(
          <li key={index} className="ml-4 list-disc">
            {escapeHtml(line.slice(2))}
          </li>
        );
        return;
      }

      // 番号付きリスト（VULN-007: エスケープ）
      const numberedMatch = line.match(/^(\d+)\.\s(.*)$/);
      if (numberedMatch) {
        elements.push(
          <li key={index} className="ml-4 list-decimal">
            {escapeHtml(numberedMatch[2])}
          </li>
        );
        return;
      }

      // 空行
      if (line.trim() === '') {
        elements.push(<br key={index} />);
        return;
      }

      // 通常のテキスト
      elements.push(
        <p key={index} className="my-1">
          {renderInlineMarkdown(line)}
        </p>
      );
    });

    return elements;
  };

  const renderInlineMarkdown = (text: string) => {
    // **太字** と *イタリック* と `コード` を処理
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let keyIndex = 0;

    while (remaining.length > 0) {
      // インラインコード
      const codeMatch = remaining.match(/`([^`]+)`/);
      // 太字
      const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
      // イタリック
      const italicMatch = remaining.match(/\*([^*]+)\*/);

      // 最も早く出現するマッチを見つける
      type MatchType = 'code' | 'bold' | 'italic';
      let earliestMatch: RegExpMatchArray | null = null;
      let matchType: MatchType | null = null;
      let earliestIndex = Infinity;

      if (codeMatch && codeMatch.index !== undefined && codeMatch.index < earliestIndex) {
        earliestMatch = codeMatch;
        matchType = 'code';
        earliestIndex = codeMatch.index;
      }
      if (boldMatch && boldMatch.index !== undefined && boldMatch.index < earliestIndex) {
        earliestMatch = boldMatch;
        matchType = 'bold';
        earliestIndex = boldMatch.index;
      }
      if (
        italicMatch &&
        italicMatch.index !== undefined &&
        matchType !== 'bold' &&
        italicMatch.index < earliestIndex
      ) {
        earliestMatch = italicMatch;
        matchType = 'italic';
        earliestIndex = italicMatch.index;
      }

      if (!earliestMatch || matchType === null) {
        parts.push(remaining);
        break;
      }

      // マッチ前のテキスト
      if (earliestIndex > 0) {
        parts.push(remaining.slice(0, earliestIndex));
      }

      // マッチしたスタイルを適用
      if (matchType === 'code') {
        parts.push(
          <code
            key={keyIndex++}
            className="px-1 py-0.5 bg-gray-100 rounded text-xs font-mono"
          >
            {earliestMatch[1]}
          </code>
        );
      } else if (matchType === 'bold') {
        parts.push(
          <strong key={keyIndex++}>{earliestMatch[1]}</strong>
        );
      } else if (matchType === 'italic') {
        parts.push(<em key={keyIndex++}>{earliestMatch[1]}</em>);
      }

      remaining = remaining.slice(earliestIndex + earliestMatch[0].length);
    }

    return parts;
  };

  return (
    <div className="prose prose-sm max-w-none p-4 bg-white rounded-lg">
      {renderMarkdown(content)}
    </div>
  );
}
