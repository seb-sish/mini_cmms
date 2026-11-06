"use client";

import { ReactElement } from "react";
import "./style.css";

export interface ITab {
  id: string;
  label: string;
}

interface ITabsProps {
  label: string;
  tabs: ITab[];
  selectedId: string;
  onChange: (tabId: string) => void;
}

export const buildTabPanelId = (tabId: string): string => `tab-panel-${tabId}`;

const Tabs = ({
  label,
  tabs,
  selectedId,
  onChange,
}: ITabsProps): ReactElement => {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => {
        const isSelected: boolean = tab.id === selectedId;

        const handleClick = () => {
          onChange(tab.id);
        };

        return (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            className={`tabs-tab ${isSelected ? "selected" : ""}`}
            type="button"
            role="tab"
            aria-selected={isSelected}
            aria-controls={buildTabPanelId(tab.id)}
            tabIndex={isSelected ? 0 : -1}
            onClick={handleClick}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;
