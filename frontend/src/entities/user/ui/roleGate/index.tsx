"use client";

import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { useViewer } from "../../model/viewerContext";
import { UserRole } from "../../model/types";
import { ReactElement } from "react";
import { ReactNode } from "react";

interface IRoleGateProps {
  allowedRoles: readonly UserRole[];
  children: ReactNode;
}

const RoleGate = ({ allowedRoles, children }: IRoleGateProps): ReactElement => {
  const viewer = useViewer();

  if (!allowedRoles.includes(viewer.role)) {
    return (
      <SectionMessage
        appearance={SectionMessageAppearance.WARNING}
        title="Раздел недоступен"
      >
        <p>Этот раздел не предусмотрен для вашей роли.</p>
      </SectionMessage>
    );
  }

  return <>{children}</>;
};

export default RoleGate;
