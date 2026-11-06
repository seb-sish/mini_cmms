"use client";

import Icon from "@shared/ui/icon";
import { IconName } from "@shared/ui/icon";
import { IconSize } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

interface ITagProps {
  label: string;
  onRemove?: () => void;
}

const Tag = ({ label, onRemove }: ITagProps): ReactElement => {
  return (
    <span className="tag">
      <span className="tag-label">{label}</span>
      {onRemove && (
        <button
          className="tag-remove"
          type="button"
          aria-label={`Удалить ${label}`}
          onClick={onRemove}
        >
          <Icon name={IconName.CLOSE} size={IconSize.SMALL} />
        </button>
      )}
    </span>
  );
};

export default Tag;
