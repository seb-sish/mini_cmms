"use client";

import Button from "@shared/ui/button";
import { KeyboardEvent as ReactKeyboardEvent } from "react";
import { ButtonAppearance } from "@shared/ui/button";
import { IconName } from "@shared/ui/icon";
import { createPortal } from "react-dom";
import { ReactElement } from "react";
import { MouseEvent } from "react";
import { useEffect } from "react";
import { ReactNode } from "react";
import { useRef } from "react";
import { useId } from "react";
import "./style.css";

export const enum ModalWidth {
  SMALL = "small",
  MEDIUM = "medium",
  LARGE = "large",
}

interface IModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: ModalWidth;
  isDismissDisabled?: boolean;
}

const FOCUSABLE_SELECTOR: string =
  'input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

const Modal = ({
  title,
  onClose,
  children,
  footer,
  width = ModalWidth.MEDIUM,
  isDismissDisabled = false,
}: IModalProps): ReactElement => {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const firstField = dialogRef.current
      ?.querySelector(".modal-body")
      ?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
    const previousOverflow = document.body.style.overflow;

    (firstField ?? dialogRef.current)?.focus();
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus();
    };
  }, []);

  const handleClose = () => {
    if (!isDismissDisabled) onClose();
  };

  const onHandleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      handleClose();
      return;
    }

    if (event.key !== "Tab" || !dialogRef.current) return;

    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    );

    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const onHandleBlanketClick = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) handleClose();
  };

  return createPortal(
    <div className="modal-blanket" onMouseDown={onHandleBlanketClick}>
      <div
        ref={dialogRef}
        className={`modal-dialog ${width}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={onHandleKeyDown}
      >
        <header className="modal-header">
          <h1 className="heading-large" id={titleId}>
            {title}
          </h1>
          <Button
            label="Закрыть"
            appearance={ButtonAppearance.SUBTLE}
            iconBefore={IconName.CLOSE}
            isIconOnly
            isDisabled={isDismissDisabled}
            onClick={handleClose}
          />
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-footer">{footer}</footer>}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
