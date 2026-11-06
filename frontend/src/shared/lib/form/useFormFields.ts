"use client";

import { FormErrors } from "./validators";
import { useState } from "react";

export const useFormFields = <TValues extends object>(
  initialValues: TValues
) => {
  const [values, setValues] = useState<TValues>(initialValues);
  const [errors, setErrors] = useState<FormErrors<TValues>>({});

  const setFieldValue = <TKey extends keyof TValues>(
    fieldName: TKey,
    value: TValues[TKey]
  ) => {
    setValues((prev) => ({ ...prev, [fieldName]: value }));
    setErrors((prev) => ({ ...prev, [fieldName]: undefined }));
  };

  const resetForm = (nextValues: TValues = initialValues) => {
    setValues(nextValues);
    setErrors({});
  };

  return { values, errors, setErrors, setFieldValue, resetForm };
};
