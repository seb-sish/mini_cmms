"use client";

import Button from "@shared/ui/button";
import Checkbox from "@shared/ui/checkbox";
import TextField from "@shared/ui/textField";
import { useWorkOrderMutation } from "../../model/useWorkOrderMutation";
import { IChecklistItemUpdatePayload } from "@entities/work-order";
import { getMissingRequiredItems } from "@entities/work-order";
import { updateChecklistItem } from "@entities/work-order";
import { IWorkChecklistItem } from "@entities/work-order";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { ButtonAppearance } from "@shared/ui/button";
import { sortChecklist } from "@entities/work-order";
import { ButtonSpacing } from "@shared/ui/button";
import { formatDateTime } from "@shared/lib/date";
import { IWorkOrder } from "@entities/work-order";
import { normalizeText } from "@shared/lib/form";
import { ReactElement } from "react";
import { useState } from "react";
import "./style.css";

interface IWorkOrderChecklistProps {
  workOrder: IWorkOrder;
  isEditable: boolean;
  isRefreshing: boolean;
}

interface IChecklistMutationVariables {
  itemId: string;
  payload: IChecklistItemUpdatePayload;
}

const WorkOrderChecklist = ({
  workOrder,
  isEditable,
  isRefreshing,
}: IWorkOrderChecklistProps): ReactElement => {
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState<string>("");
  const items = sortChecklist(workOrder.checklist);
  const missingCount: number = getMissingRequiredItems(
    workOrder.checklist
  ).length;
  const checkedCount: number = items.filter((item) => item.checked).length;

  const checklistMutation = useWorkOrderMutation({
    workOrderId: workOrder.id,
    mutationFn: ({ itemId, payload }: IChecklistMutationVariables) =>
      updateChecklistItem(workOrder, itemId, payload),
    shouldFlagErrors: true,
    onSuccess: () => setEditingItemId(null),
  });

  const isBusy: boolean = checklistMutation.isPending || isRefreshing;

  const startCommentEditing = (item: IWorkChecklistItem) => {
    setEditingItemId(item.id);
    setCommentDraft(item.comment ?? "");
  };

  const cancelCommentEditing = () => {
    setEditingItemId(null);
  };

  return (
    <div className="work-order-checklist">
      <p className="body-small text-subtle">
        Выполнено {checkedCount} из {items.length}
        {missingCount > 0 && `, обязательных не отмечено: ${missingCount}`}
      </p>
      <ul className="work-order-checklist-list">
        {items.map((item) => {
          const isEditingComment: boolean = editingItemId === item.id;

          const handleToggle = (isChecked: boolean) => {
            checklistMutation.mutate({
              itemId: item.id,
              payload: { checked: isChecked },
            });
          };

          const handleStartEditing = () => {
            startCommentEditing(item);
          };

          const handleSaveComment = () => {
            const comment = normalizeText(commentDraft);

            checklistMutation.mutate({
              itemId: item.id,
              payload: { checked: item.checked, comment: comment || null },
            });
          };

          return (
            <li key={item.id} className="work-order-checklist-item">
              <Checkbox
                label={item.title}
                isChecked={item.checked}
                isRequired={item.required}
                isDisabled={!isEditable || isBusy}
                onChange={handleToggle}
                description={
                  item.checked_at
                    ? `Отмечено ${formatDateTime(item.checked_at)}`
                    : undefined
                }
              />
              {item.comment && !isEditingComment && (
                <p className="work-order-checklist-comment body-small">
                  {item.comment}
                </p>
              )}
              {isEditable && !isEditingComment && (
                <Button
                  label={
                    item.comment
                      ? "Изменить комментарий"
                      : "Добавить комментарий"
                  }
                  appearance={ButtonAppearance.LINK}
                  spacing={ButtonSpacing.COMPACT}
                  isDisabled={isBusy}
                  onClick={handleStartEditing}
                />
              )}
              {isEditingComment && (
                <div className="work-order-checklist-comment-editor">
                  <TextField
                    label="Комментарий к пункту"
                    value={commentDraft}
                    onChange={setCommentDraft}
                    maxLength={WORK_ORDER_LIMITS.CHECKLIST_COMMENT_MAX}
                    autoFocus
                  />
                  <div className="work-order-checklist-comment-actions">
                    <Button
                      label="Сохранить"
                      appearance={ButtonAppearance.PRIMARY}
                      spacing={ButtonSpacing.COMPACT}
                      isLoading={checklistMutation.isPending}
                      onClick={handleSaveComment}
                    />
                    <Button
                      label="Отмена"
                      appearance={ButtonAppearance.SUBTLE}
                      spacing={ButtonSpacing.COMPACT}
                      onClick={cancelCommentEditing}
                    />
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default WorkOrderChecklist;
