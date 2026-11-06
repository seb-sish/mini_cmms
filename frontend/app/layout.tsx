import AppProviders from "@app/providers/appProviders";
import { APP_DESCRIPTION } from "@shared/config";
import { APP_NAME } from "@shared/config";
import { ReactElement } from "react";
import { ReactNode } from "react";
import { Metadata } from "next";
import "@app/styles/theme.css";

export const metadata: Metadata = {
  title: {
    default: APP_NAME,
    template: `%s | ${APP_NAME}`,
  },
  description: APP_DESCRIPTION,
};

const RootLayout = ({
  children,
}: Readonly<{
  children: ReactNode;
}>): ReactElement => {
  return (
    <html lang="ru">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
};

export default RootLayout;
