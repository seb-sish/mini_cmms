"use client";

import Icon from "@shared/ui/icon";
import Avatar from "@shared/ui/avatar";
import { useTechniciansQuery } from "../../api/userQueries";
import { useViewer } from "../../model/viewerContext";
import { shortenId } from "@shared/lib/options";
import { UserRole } from "../../model/types";
import { IconName } from "@shared/ui/icon";
import { IconSize } from "@shared/ui/icon";
import { ReactElement } from "react";
import "./style.css";

interface IUserNameProps {
  userId: string | null;
  emptyLabel?: string;
}

const DEFAULT_EMPTY_LABEL: string = "Не назначен";

const UserName = ({
  userId,
  emptyLabel = DEFAULT_EMPTY_LABEL,
}: IUserNameProps): ReactElement => {
  const viewer = useViewer();
  const { data: technicians } = useTechniciansQuery(
    viewer.role === UserRole.ENGINEER
  );

  if (!userId) return <span className="text-subtlest">{emptyLabel}</span>;

  const knownLogin: string | undefined =
    userId === viewer.id
      ? viewer.login
      : technicians?.items.find((technician) => technician.id === userId)
          ?.login;

  const displayName: string = knownLogin ?? `Пользователь ${shortenId(userId)}`;

  return (
    <span className="user-name" title={userId}>
      {knownLogin ? (
        <Avatar name={knownLogin} />
      ) : (
        <span className="user-name-unknown" aria-hidden="true">
          <Icon name={IconName.USER} size={IconSize.SMALL} />
        </span>
      )}
      <span>{displayName}</span>
      {userId === viewer.id && <span className="text-subtlest">(вы)</span>}
    </span>
  );
};

export default UserName;
