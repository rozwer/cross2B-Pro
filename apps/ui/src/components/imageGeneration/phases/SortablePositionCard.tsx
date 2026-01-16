"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  GripVertical,
  Trash2,
  Edit2,
  Check,
  MapPin,
} from "lucide-react";
import type { ImagePosition, Section } from "@/lib/types";

interface SortablePositionCardProps {
  id: string;
  position: ImagePosition;
  index: number;
  sections: Section[];
  isEditing: boolean;
  disabled?: boolean;
  onEdit: (index: number, field: keyof ImagePosition, value: string | number) => void;
  onDelete: (index: number) => void;
  onStartEdit: (index: number) => void;
  onEndEdit: () => void;
}

export function SortablePositionCard({
  id,
  position: pos,
  index,
  sections,
  isEditing,
  disabled = false,
  onEdit,
  onDelete,
  onStartEdit,
  onEndEdit,
}: SortablePositionCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled: disabled || isEditing });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg ${
        isDragging ? "shadow-lg ring-2 ring-primary-400" : ""
      }`}
    >
      {isEditing ? (
        // 編集モード
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400">
                セクション
              </label>
              <select
                value={pos.section_title}
                onChange={(e) => {
                  const section = sections.find(
                    (s) => s.title === e.target.value
                  );
                  if (section) {
                    const sectionIndex = section.section_index ?? sections.indexOf(section);
                    onEdit(index, "section_title", section.title);
                    onEdit(index, "section_index", sectionIndex);
                    if (section.article_number !== undefined) {
                      onEdit(index, "article_number", section.article_number);
                    }
                  }
                }}
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              >
                {sections.map((section, i) => (
                  <option key={section.section_key ?? i} value={section.title}>
                    {section.article_number ? `記事${section.article_number}: ` : ""}{section.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400">
                位置
              </label>
              <select
                value={pos.position}
                onChange={(e) => onEdit(index, "position", e.target.value)}
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              >
                <option value="before">見出しの前</option>
                <option value="after">見出しの後</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400">
              説明
            </label>
            <input
              type="text"
              value={pos.description}
              onChange={(e) => onEdit(index, "description", e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={onEndEdit}
              className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
            >
              <Check className="h-4 w-4" />
            </button>
          </div>
        </div>
      ) : (
        // 表示モード
        <div className="flex items-start gap-2">
          {/* ドラッグハンドル */}
          <button
            {...attributes}
            {...listeners}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-grab active:cursor-grabbing touch-none"
            aria-label="ドラッグして並び替え"
          >
            <GripVertical className="h-4 w-4" />
          </button>

          {/* コンテンツ */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <MapPin className="h-4 w-4 text-primary-500 flex-shrink-0" />
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {pos.section_title}
              </span>
              {pos.article_number && (
                <span className="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-200 rounded">
                  記事{pos.article_number}
                </span>
              )}
              <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                {pos.position === "before" ? "前" : "後"}
              </span>
            </div>
            {pos.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 ml-6">
                {pos.description}
              </p>
            )}
          </div>

          {/* アクションボタン */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={() => onStartEdit(index)}
              disabled={disabled}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded disabled:opacity-50"
            >
              <Edit2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => onDelete(index)}
              disabled={disabled}
              className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
