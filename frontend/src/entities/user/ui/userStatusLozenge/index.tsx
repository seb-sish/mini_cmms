import Lozenge from "@shared/ui/lozenge";
import { USER_STATUS_APPEARANCES } from "../../model/labels";
import { USER_STATUS_LABELS } from "../../model/labels";
import { UserStatus } from "../../model/types";
import { ReactElement } from "react";

interface IUserStatusLozengeProps {
  status: UserStatus;
}

const UserStatusLozenge = ({
  status,
}: IUserStatusLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={USER_STATUS_LABELS[status]}
      appearance={USER_STATUS_APPEARANCES[status]}
    />
  );
};

export default UserStatusLozenge;
