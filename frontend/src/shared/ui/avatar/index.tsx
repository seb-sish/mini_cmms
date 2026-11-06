import { ReactElement } from "react";
import "./style.css";

export const enum AvatarSize {
  SMALL = "small",
  MEDIUM = "medium",
}

interface IAvatarProps {
  name: string;
  size?: AvatarSize;
}

const AVATAR_COLORS: string[] = [
  "#0A7275",
  "#1F2A33",
  "#6E5DC6",
  "#0C66E4",
  "#1F845A",
  "#A54800",
];

export const getAvatarInitials = (name: string): string =>
  name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "?";

export const getAvatarColor = (name: string): string => {
  const hash = Array.from(name).reduce(
    (sum, char) => sum + char.charCodeAt(0),
    0
  );

  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
};

const Avatar = ({
  name,
  size = AvatarSize.SMALL,
}: IAvatarProps): ReactElement => {
  return (
    <span
      className={`avatar ${size}`}
      style={{ backgroundColor: getAvatarColor(name) }}
      aria-hidden="true"
    >
      {getAvatarInitials(name)}
    </span>
  );
};

export default Avatar;
