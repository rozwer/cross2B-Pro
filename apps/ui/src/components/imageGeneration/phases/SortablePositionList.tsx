"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { Plus } from "lucide-react";
import type { ImagePosition, Section } from "@/lib/types";
import { SortablePositionCard } from "./SortablePositionCard";

interface SortablePositionListProps {
  positions: ImagePosition[];
  sections: Section[];
  disabled?: boolean;
  onPositionsChange: (positions: ImagePosition[]) => void;
  onShowAddForm: () => void;
}

export function SortablePositionList({
  positions,
  sections,
  disabled = false,
  onPositionsChange,
  onShowAddForm,
}: SortablePositionListProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px 移動後にドラッグ開始（クリックとの区別）
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;

      if (over && active.id !== over.id) {
        const oldIndex = positions.findIndex(
          (_, i) => `position-${i}` === active.id
        );
        const newIndex = positions.findIndex(
          (_, i) => `position-${i}` === over.id
        );

        if (oldIndex !== -1 && newIndex !== -1) {
          const newPositions = arrayMove(positions, oldIndex, newIndex);
          onPositionsChange(newPositions);
        }
      }
    },
    [positions, onPositionsChange]
  );

  const handleEdit = useCallback(
    (index: number, field: keyof ImagePosition, value: string | number) => {
      const newPositions = positions.map((pos, i) =>
        i === index ? { ...pos, [field]: value } : pos
      );
      onPositionsChange(newPositions);
    },
    [positions, onPositionsChange]
  );

  const handleDelete = useCallback(
    (index: number) => {
      const newPositions = positions.filter((_, i) => i !== index);
      onPositionsChange(newPositions);
      if (editingIndex === index) {
        setEditingIndex(null);
      }
    },
    [positions, onPositionsChange, editingIndex]
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          挿入位置 ({positions.length}件)
        </h4>
        <button
          onClick={onShowAddForm}
          disabled={disabled}
          className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg disabled:opacity-50"
        >
          <Plus className="h-3 w-3" />
          追加
        </button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={positions.map((_, i) => `position-${i}`)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {positions.map((pos, index) => (
              <SortablePositionCard
                key={`position-${index}`}
                id={`position-${index}`}
                position={pos}
                index={index}
                sections={sections}
                isEditing={editingIndex === index}
                disabled={disabled}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onStartEdit={setEditingIndex}
                onEndEdit={() => setEditingIndex(null)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {positions.length === 0 && (
        <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          挿入位置がありません。
          <br />
          左の記事プレビューから選択するか、「追加」ボタンで手動追加してください。
        </div>
      )}
    </div>
  );
}
