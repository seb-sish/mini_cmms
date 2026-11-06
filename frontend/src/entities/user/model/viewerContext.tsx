"use client";

import { getRolePermissions } from "./permissions";
import { IRolePermissions } from "./permissions";
import { createContext } from "react";
import { ReactElement } from "react";
import { useContext } from "react";
import { ReactNode } from "react";
import { IUser } from "./types";

const ViewerContext = createContext<IUser | null>(null);

interface IViewerProviderProps {
  viewer: IUser;
  children: ReactNode;
}

export const ViewerProvider = ({
  viewer,
  children,
}: IViewerProviderProps): ReactElement => {
  return (
    <ViewerContext.Provider value={viewer}>{children}</ViewerContext.Provider>
  );
};

export const useViewer = (): IUser => {
  const viewer = useContext(ViewerContext);

  if (!viewer) throw new Error("useViewer must be used inside ViewerProvider");

  return viewer;
};

export const useViewerPermissions = (): IRolePermissions =>
  getRolePermissions(useViewer().role);
