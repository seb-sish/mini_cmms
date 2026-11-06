import Lozenge from "@shared/ui/lozenge";
import { NOTIFICATION_TYPE_APPEARANCES } from "../../model/labels";
import { NOTIFICATION_TYPE_LABELS } from "../../model/labels";
import { NotificationType } from "../../model/types";
import { ReactElement } from "react";

interface INotificationTypeLozengeProps {
  type: NotificationType;
}

const NotificationTypeLozenge = ({
  type,
}: INotificationTypeLozengeProps): ReactElement => {
  return (
    <Lozenge
      label={NOTIFICATION_TYPE_LABELS[type]}
      appearance={NOTIFICATION_TYPE_APPEARANCES[type]}
    />
  );
};

export default NotificationTypeLozenge;
