import { UserDetailsPage } from "@pages/user-details";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Пользователь",
};

interface IUserDetailsPageRouteProps {
  params: Promise<{ userId: string }>;
}

const UserDetailsPageRoute = async ({
  params,
}: IUserDetailsPageRouteProps): Promise<ReactElement> => {
  const { userId } = await params;

  return <UserDetailsPage userId={userId} />;
};

export default UserDetailsPageRoute;
