"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface JsonViewerProps {
  content: string;
}

export function JsonViewer({ content }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);

  let parsed: unknown;
  let parseError: string | null = null;

  try {
    parsed = JSON.parse(content);
  } catch (e) {
    parseError = e instanceof Error ? e.message : "Invalid JSON";
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (parseError) {
    return (
      <div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
          <p className="text-sm text-red-700">JSON Parse Error: {parseError}</p>
        </div>
        <pre className="p-4 bg-gray-50 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap">
          {content}
        </pre>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-end mb-2">
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-500" />
              コピーしました
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              コピー
            </>
          )}
        </button>
      </div>
      <div className="p-4 bg-gray-50 rounded-lg overflow-auto max-h-96">
        <JsonNode value={parsed} name={null} isLast />
      </div>
    </div>
  );
}

interface JsonNodeProps {
  value: unknown;
  name: string | null;
  isLast: boolean;
  depth?: number;
}

function JsonNode({ value, name, isLast, depth = 0 }: JsonNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);

  const isObject = value !== null && typeof value === "object";
  const isArray = Array.isArray(value);
  const entries = isObject
    ? isArray
      ? value.map((v, i) => [i.toString(), v] as [string, unknown])
      : Object.entries(value as Record<string, unknown>)
    : [];

  const renderValue = () => {
    if (value === null) {
      return <span className="text-gray-500">null</span>;
    }
    if (typeof value === "boolean") {
      return <span className="text-purple-600">{value.toString()}</span>;
    }
    if (typeof value === "number") {
      return <span className="text-blue-600">{value}</span>;
    }
    if (typeof value === "string") {
      return <span className="text-green-600">&quot;{value}&quot;</span>;
    }
    return null;
  };

  if (!isObject) {
    return (
      <div className="text-xs font-mono" style={{ paddingLeft: depth * 16 }}>
        {name !== null && (
          <>
            <span className="text-gray-700">&quot;{name}&quot;</span>
            <span className="text-gray-500">: </span>
          </>
        )}
        {renderValue()}
        {!isLast && <span className="text-gray-500">,</span>}
      </div>
    );
  }

  const bracketOpen = isArray ? "[" : "{";
  const bracketClose = isArray ? "]" : "}";

  if (entries.length === 0) {
    return (
      <div className="text-xs font-mono" style={{ paddingLeft: depth * 16 }}>
        {name !== null && (
          <>
            <span className="text-gray-700">&quot;{name}&quot;</span>
            <span className="text-gray-500">: </span>
          </>
        )}
        <span className="text-gray-500">
          {bracketOpen}
          {bracketClose}
        </span>
        {!isLast && <span className="text-gray-500">,</span>}
      </div>
    );
  }

  return (
    <div>
      <div
        className="text-xs font-mono flex items-center cursor-pointer hover:bg-gray-100 rounded"
        style={{ paddingLeft: depth * 16 }}
        onClick={() => setExpanded(!expanded)}
      >
        <span className="w-4 flex-shrink-0">
          {expanded ? (
            <ChevronDown className="h-3 w-3 text-gray-400" />
          ) : (
            <ChevronRight className="h-3 w-3 text-gray-400" />
          )}
        </span>
        {name !== null && (
          <>
            <span className="text-gray-700">&quot;{name}&quot;</span>
            <span className="text-gray-500">: </span>
          </>
        )}
        <span className="text-gray-500">{bracketOpen}</span>
        {!expanded && (
          <span className="text-gray-400 ml-1">
            {entries.length} {isArray ? "items" : "keys"}...
          </span>
        )}
        {!expanded && (
          <>
            <span className="text-gray-500">{bracketClose}</span>
            {!isLast && <span className="text-gray-500">,</span>}
          </>
        )}
      </div>
      {expanded && (
        <>
          {entries.map(([key, val], index) => (
            <JsonNode
              key={key}
              name={isArray ? null : key}
              value={val}
              isLast={index === entries.length - 1}
              depth={depth + 1}
            />
          ))}
          <div className="text-xs font-mono" style={{ paddingLeft: depth * 16 }}>
            <span className="text-gray-500">{bracketClose}</span>
            {!isLast && <span className="text-gray-500">,</span>}
          </div>
        </>
      )}
    </div>
  );
}
