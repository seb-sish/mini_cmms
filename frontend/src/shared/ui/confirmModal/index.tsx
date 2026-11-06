"use client";

import Modal from "@shared/ui/modal";
import Button from "@shared/ui/button";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { ButtonAppearance } from "@shared/ui/button";
import { ModalWidth } from "@shared/ui/modal";
import { ReactElement } from "react";
import { ReactNode } from "react";

interface IConfirmModalProps {
  title: string;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
  children: ReactNode;
  isPending?: boolean;
  errorMessage?: string | null;
  confirmAppearance?: ButtonAppearance;
}

const ConfirmModal = ({
  title,
  confirmLabel,
  onConfirm,
  onClose,
  children,
  isPending = false,
  errorMessage,
  confirmAppearance = ButtonAppearance.PRIMARY,
}: IConfirmModalProps): ReactElement => {
  return (
    <Modal
      title={title}
      onClose={onClose}
      width={ModalWidth.SMALL}
      isDismissDisabled={isPending}
      footer={
        <>
          <Button
            label="Отмена"
            appearance={ButtonAppearance.SUBTLE}
            isDisabled={isPending}
            onClick={onClose}
          />
          <Button
            label={confirmLabel}
            appearance={confirmAppearance}
            isLoading={isPending}
            onClick={onConfirm}
          />
        </>
      }
    >
      {errorMessage && (
        <SectionMessage appearance={SectionMessageAppearance.ERROR}>
          <p>{errorMessage}</p>
        </SectionMessage>
      )}
      {children}
    </Modal>
  );
};

export default ConfirmModal;
