"use client";

import Modal from "@shared/ui/modal";
import Button from "@shared/ui/button";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { ButtonAppearance } from "@shared/ui/button";
import { ButtonType } from "@shared/ui/button";
import { ModalWidth } from "@shared/ui/modal";
import { ReactElement } from "react";
import { FormEvent } from "react";
import { ReactNode } from "react";
import { useId } from "react";
import "./style.css";

interface IFormModalProps {
  title: string;
  submitLabel: string;
  onSubmit: () => void;
  onClose: () => void;
  children: ReactNode;
  isSubmitting?: boolean;
  isSubmitDisabled?: boolean;
  errorMessage?: string | null;
  width?: ModalWidth;
  submitAppearance?: ButtonAppearance;
}

const FormModal = ({
  title,
  submitLabel,
  onSubmit,
  onClose,
  children,
  isSubmitting = false,
  isSubmitDisabled = false,
  errorMessage,
  width = ModalWidth.MEDIUM,
  submitAppearance = ButtonAppearance.PRIMARY,
}: IFormModalProps): ReactElement => {
  const formId = useId();

  const onHandleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <Modal
      title={title}
      onClose={onClose}
      width={width}
      isDismissDisabled={isSubmitting}
      footer={
        <>
          <Button
            label="Отмена"
            appearance={ButtonAppearance.SUBTLE}
            isDisabled={isSubmitting}
            onClick={onClose}
          />
          <Button
            label={submitLabel}
            type={ButtonType.SUBMIT}
            form={formId}
            appearance={submitAppearance}
            isLoading={isSubmitting}
            isDisabled={isSubmitDisabled}
          />
        </>
      }
    >
      <form
        id={formId}
        className="form-modal-form"
        onSubmit={onHandleSubmit}
        noValidate
      >
        <p className="body-small text-subtle">
          Поля, отмеченные <span className="form-modal-required">*</span>,
          обязательны.
        </p>
        {errorMessage && (
          <SectionMessage appearance={SectionMessageAppearance.ERROR}>
            <p>{errorMessage}</p>
          </SectionMessage>
        )}
        {children}
      </form>
    </Modal>
  );
};

export default FormModal;
