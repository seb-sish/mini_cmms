import { AppShell } from "@widgets/app-shell";
import { ReactElement } from "react";
import { ReactNode } from "react";

const MainLayout = ({
  children,
}: Readonly<{
  children: ReactNode;
}>): ReactElement => {
  return <AppShell>{children}</AppShell>;
};

export default MainLayout;
