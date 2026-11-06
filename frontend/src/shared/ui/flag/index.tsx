"use client";

import Icon from "@shared/ui/icon";
import Button from "@shared/ui/button";
import { ButtonAppearance } from "@shared/ui/button";
import { ButtonSpacing } from "@shared/ui/button";
import { IconName } from "@shared/ui/icon";
import { createContext } from "react";
import { ReactElement } from "react";
import { useContext } from "react";
import { ReactNode } from "react";
import { useState } from "react";
import { useRef } from "react";
import "./style.css";

export const enum FlagAppearance {
  SUCCESS = "success",
  ERROR = "error",
  WARNING = "warning",
  INFO = "info",
}

export interface IFlagInput {
  appearance: FlagAppearance;
  title: string;
  description?: string;
}

interface IFlag extends IFlagInput {
  id: number;
}

interface IFlagsContext {
  showFlag: (flag: IFlagInput) => void;
}

const FLAG_LIFETIME_MS = 6000;

const FLAG_ICONS: Record<FlagAppearance, IconName> = {
  [FlagAppearance.SUCCESS]: IconName.SUCCESS,
  [FlagAppearance.ERROR]: IconName.ERROR,
  [FlagAppearance.WARNING]: IconName.WARNING,
  [FlagAppearance.INFO]: IconName.INFO,
};

const FlagsContext = createContext<IFlagsContext | null>(null);

export const FlagsProvider = ({
  children,
}: {
  children: ReactNode;
}): ReactElement => {
  const [flags, setFlags] = useState<IFlag[]>([]);
  const nextIdRef = useRef<number>(1);

  const dismissFlag = (id: number) => {
    setFlags((prev) => prev.filter((flag) => flag.id !== id));
  };

  const [contextValue] = useState<IFlagsContext>(() => ({
    showFlag: (flag: IFlagInput) => {
      const id = nextIdRef.current;

      nextIdRef.current += 1;
      setFlags((prev) => [...prev, { ...flag, id }]);
      setTimeout(() => {
        setFlags((prev) => prev.filter((item) => item.id !== id));
      }, FLAG_LIFETIME_MS);
    },
  }));

  return (
    <FlagsContext.Provider value={contextValue}>
      {children}
      <div className="flag-group" aria-live="polite">
        {flags.map((flag) => {
          const handleDismiss = () => {
            dismissFlag(flag.id);
          };

          return (
            <div
              key={flag.id}
              className={`flag ${flag.appearance}`}
              role={
                flag.appearance === FlagAppearance.ERROR ? "alert" : "status"
              }
            >
              <span className="flag-icon">
                <Icon name={FLAG_ICONS[flag.appearance]} />
              </span>
              <div className="flag-content">
                <p className="heading-small">{flag.title}</p>
                {flag.description && (
                  <p className="flag-description">{flag.description}</p>
                )}
              </div>
              <Button
                label="Скрыть уведомление"
                appearance={ButtonAppearance.SUBTLE}
                spacing={ButtonSpacing.COMPACT}
                iconBefore={IconName.CLOSE}
                isIconOnly
                onClick={handleDismiss}
              />
            </div>
          );
        })}
      </div>
    </FlagsContext.Provider>
  );
};

export const useFlags = (): IFlagsContext => {
  const context = useContext(FlagsContext);

  if (!context) throw new Error("useFlags must be used inside FlagsProvider");

  return context;
};
