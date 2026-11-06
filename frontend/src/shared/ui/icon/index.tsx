import { ReactElement } from "react";
import "./style.css";

export const enum IconName {
  ADD = "add",
  ARCHIVE = "archive",
  ARROW_LEFT = "arrow-left",
  BELL = "bell",
  CALENDAR = "calendar",
  CHECK = "check",
  CHECKLIST = "checklist",
  CHEVRON_DOWN = "chevron-down",
  CHEVRON_LEFT = "chevron-left",
  CHEVRON_RIGHT = "chevron-right",
  CLOSE = "close",
  DASHBOARD = "dashboard",
  EDIT = "edit",
  ERROR = "error",
  EQUIPMENT = "equipment",
  FAULT = "fault",
  HISTORY = "history",
  INFO = "info",
  LOCK = "lock",
  LOGOUT = "logout",
  PLAN = "plan",
  PRIORITY_CRITICAL = "priority-critical",
  PRIORITY_HIGH = "priority-high",
  PRIORITY_LOW = "priority-low",
  PRIORITY_NORMAL = "priority-normal",
  REFRESH = "refresh",
  RESTORE = "restore",
  SEARCH = "search",
  SUCCESS = "success",
  UNLOCK = "unlock",
  USER = "user",
  USERS = "users",
  WARNING = "warning",
  WORK_ORDER = "work-order",
  WRENCH = "wrench",
}

export const enum IconSize {
  SMALL = 12,
  MEDIUM = 16,
  LARGE = 24,
}

interface IIconProps {
  name: IconName;
  size?: IconSize;
  label?: string;
  className?: string;
}

const ICON_PATHS: Record<IconName, string[]> = {
  [IconName.ADD]: ["M12 5v14", "M5 12h14"],
  [IconName.ARCHIVE]: ["M3 4h18v4H3z", "M5 8v12h14V8", "M10 12h4"],
  [IconName.ARROW_LEFT]: ["M19 12H5", "M12 19l-7-7 7-7"],
  [IconName.BELL]: [
    "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9",
    "M10.3 21a1.94 1.94 0 0 0 3.4 0",
  ],
  [IconName.CALENDAR]: ["M3 5h18v16H3z", "M16 3v4", "M8 3v4", "M3 10h18"],
  [IconName.CHECK]: ["M20 6L9 17l-5-5"],
  [IconName.CHECKLIST]: [
    "M10 6h11",
    "M10 12h11",
    "M10 18h11",
    "M3 6l1.5 1.5L7 5",
    "M3 12l1.5 1.5L7 11",
    "M3 18l1.5 1.5L7 17",
  ],
  [IconName.CHEVRON_DOWN]: ["M6 9l6 6 6-6"],
  [IconName.CHEVRON_LEFT]: ["M15 18l-6-6 6-6"],
  [IconName.CHEVRON_RIGHT]: ["M9 18l6-6-6-6"],
  [IconName.CLOSE]: ["M18 6L6 18", "M6 6l12 12"],
  [IconName.DASHBOARD]: [
    "M3 3h8v8H3z",
    "M13 3h8v5h-8z",
    "M13 10h8v11h-8z",
    "M3 13h8v8H3z",
  ],
  [IconName.EDIT]: ["M12 20h9", "M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"],
  [IconName.ERROR]: [
    "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20",
    "M15 9l-6 6",
    "M9 9l6 6",
  ],
  [IconName.EQUIPMENT]: [
    "M12 15a3 3 0 1 0 0-6a3 3 0 0 0 0 6",
    "M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
  ],
  [IconName.FAULT]: [
    "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    "M12 9v4",
    "M12 17h.01",
  ],
  [IconName.HISTORY]: ["M3 12a9 9 0 1 0 3-6.7L3 8", "M3 3v5h5", "M12 7v5l4 2"],
  [IconName.INFO]: [
    "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20",
    "M12 16v-4",
    "M12 8h.01",
  ],
  [IconName.LOCK]: ["M5 11h14v10H5z", "M7 11V7a5 5 0 0 1 10 0v4"],
  [IconName.LOGOUT]: [
    "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4",
    "M16 17l5-5-5-5",
    "M21 12H9",
  ],
  [IconName.PLAN]: ["M9 3h6v4H9z", "M16 5h3v16H5V5h3", "M9 12h6", "M9 16h6"],
  [IconName.PRIORITY_CRITICAL]: ["M6 13l6-6 6 6", "M6 19l6-6 6 6"],
  [IconName.PRIORITY_HIGH]: ["M6 15l6-6 6 6"],
  [IconName.PRIORITY_LOW]: ["M6 9l6 6 6-6"],
  [IconName.PRIORITY_NORMAL]: ["M5 9h14", "M5 15h14"],
  [IconName.REFRESH]: ["M21 12a9 9 0 1 1-2.64-6.36L21 8", "M21 3v5h-5"],
  [IconName.RESTORE]: [
    "M3 12a9 9 0 1 0 2.64-6.36L3 8",
    "M3 3v5h5",
    "M12 8v8",
    "M8 12h8",
  ],
  [IconName.SEARCH]: [
    "M11 18a7 7 0 1 0 0-14a7 7 0 0 0 0 14",
    "M21 21l-4.35-4.35",
  ],
  [IconName.SUCCESS]: [
    "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20",
    "M8 12l3 3 5-6",
  ],
  [IconName.UNLOCK]: ["M5 11h14v10H5z", "M7 11V7a5 5 0 0 1 9.9-1"],
  [IconName.USER]: [
    "M20 21a8 8 0 0 0-16 0",
    "M12 13a5 5 0 1 0 0-10a5 5 0 0 0 0 10",
  ],
  [IconName.USERS]: [
    "M17 21a6 6 0 0 0-12 0",
    "M11 11a4 4 0 1 0 0-8a4 4 0 0 0 0 8",
    "M23 21a6 6 0 0 0-4-5.65",
    "M16 3.13a4 4 0 0 1 0 7.75",
  ],
  [IconName.WARNING]: [
    "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    "M12 9v4",
    "M12 17h.01",
  ],
  [IconName.WORK_ORDER]: ["M9 3h6v4H9z", "M16 5h3v16H5V5h3", "M9 14l2 2 4-4"],
  [IconName.WRENCH]: [
    "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
  ],
};

const DEFAULT_ICON_SIZE: IconSize = IconSize.MEDIUM;

const Icon = ({
  name,
  size = DEFAULT_ICON_SIZE,
  label,
  className,
}: IIconProps): ReactElement => {
  const isDecorative: boolean = !label;

  return (
    <svg
      className={`icon ${className ?? ""}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={isDecorative ? undefined : "img"}
      aria-hidden={isDecorative}
      aria-label={label}
      focusable="false"
    >
      {ICON_PATHS[name].map((path) => (
        <path key={path} d={path} />
      ))}
    </svg>
  );
};

export default Icon;
