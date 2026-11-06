"use client";

import Button from "@shared/ui/button";
import Checkbox from "@shared/ui/checkbox";
import TextField from "@shared/ui/textField";
import { createChecklistDraftItem } from "../../model/planForm";
import { IChecklistDraftItem } from "../../model/planForm";
import { PLAN_LIMITS } from "@entities/maintenance-plan";
import { ButtonAppearance } from "@shared/ui/button";
import { ButtonSpacing } from "@shared/ui/button";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

interface IChecklistEditorProps {
  items: IChecklistDraftItem[];
  onChange: (items: IChecklistDraftItem[]) => void;
  errorMessage?: string;
  itemErrors?: Record<string, string>;
}

const ChecklistEditor = ({
  items,
  onChange,
  errorMessage,
  itemErrors = {},
}: IChecklistEditorProps): ReactElement => {
  const updateItem = (key: string, patch: Partial<IChecklistDraftItem>) => {
    onChange(
      items.map((item) => (item.key === key ? { ...item, ...patch } : item))
    );
  };

  const moveItem = (index: number, direction: number) => {
    const nextItems = [...items];
    const [movedItem] = nextItems.splice(index, 1);

    nextItems.splice(index + direction, 0, movedItem);
    onChange(nextItems);
  };

  const handleAdd = () => {
    onChange([...items, createChecklistDraftItem()]);
  };

  return (
    <fieldset className="checklist-editor">
      <legend className="checklist-editor-legend">
        Чек-лист операций <span className="checklist-editor-required">*</span>
      </legend>
      {errorMessage && (
        <p className="checklist-editor-error body-small">{errorMessage}</p>
      )}
      <ol className="checklist-editor-list">
        {items.map((item, index) => {
          const handleTitleChange = (title: string) => {
            updateItem(item.key, { title });
          };

          const handleRequiredChange = (required: boolean) => {
            updateItem(item.key, { required });
          };

          const handleMoveUp = () => {
            moveItem(index, -1);
          };

          const handleMoveDown = () => {
            moveItem(index, 1);
          };

          const handleRemove = () => {
            onChange(items.filter((candidate) => candidate.key !== item.key));
          };

          return (
            <li key={item.key} className="checklist-editor-item">
              <span className="checklist-editor-index body-small">
                {index + 1}.
              </span>
              <div className="checklist-editor-fields">
                <TextField
                  label={`Операция ${index + 1}`}
                  value={item.title}
                  onChange={handleTitleChange}
                  errorMessage={itemErrors[item.key]}
                  maxLength={PLAN_LIMITS.CHECKLIST_TITLE_MAX}
                  isRequired
                />
                <Checkbox
                  label="Обязательная операция"
                  isChecked={item.required}
                  onChange={handleRequiredChange}
                />
              </div>
              <div className="checklist-editor-actions">
                <Button
                  label="Переместить выше"
                  appearance={ButtonAppearance.SUBTLE}
                  spacing={ButtonSpacing.COMPACT}
                  iconBefore={IconName.PRIORITY_HIGH}
                  isIconOnly
                  isDisabled={index === 0}
                  onClick={handleMoveUp}
                />
                <Button
                  label="Переместить ниже"
                  appearance={ButtonAppearance.SUBTLE}
                  spacing={ButtonSpacing.COMPACT}
                  iconBefore={IconName.PRIORITY_LOW}
                  isIconOnly
                  isDisabled={index === items.length - 1}
                  onClick={handleMoveDown}
                />
                <Button
                  label="Удалить операцию"
                  appearance={ButtonAppearance.SUBTLE}
                  spacing={ButtonSpacing.COMPACT}
                  iconBefore={IconName.CLOSE}
                  isIconOnly
                  onClick={handleRemove}
                />
              </div>
            </li>
          );
        })}
      </ol>
      <div>
        <Button
          label="Добавить операцию"
          appearance={ButtonAppearance.SUBTLE}
          iconBefore={IconName.ADD}
          isDisabled={items.length >= PLAN_LIMITS.CHECKLIST_MAX_ITEMS}
          onClick={handleAdd}
        />
      </div>
    </fieldset>
  );
};

export default ChecklistEditor;
