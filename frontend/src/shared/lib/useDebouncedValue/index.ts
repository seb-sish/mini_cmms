"use client";

import { SEARCH_DEBOUNCE_MS } from "@shared/config";
import { useEffect } from "react";
import { useState } from "react";

const useDebouncedValue = <TValue>(
  value: TValue,
  delayMs: number = SEARCH_DEBOUNCE_MS
): TValue => {
  const [debouncedValue, setDebouncedValue] = useState<TValue>(value);

  useEffect(() => {
    const timeoutId = setTimeout(() => setDebouncedValue(value), delayMs);

    return () => clearTimeout(timeoutId);
  }, [value, delayMs]);

  return debouncedValue;
};

export default useDebouncedValue;
