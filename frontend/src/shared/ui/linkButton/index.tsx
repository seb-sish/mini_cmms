import Link from "next/link";
import Icon from "@shared/ui/icon";
import { ButtonAppearance } from "@shared/ui/button";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import "@shared/ui/button/style.css";

interface ILinkButtonProps {
  label: string;
  href: string;
  appearance?: ButtonAppearance;
  iconBefore?: IconName;
}

const LinkButton = ({
  label,
  href,
  appearance = ButtonAppearance.DEFAULT,
  iconBefore,
}: ILinkButtonProps): ReactElement => {
  return (
    <Link className={`button ${appearance} spacing-default`} href={href}>
      {iconBefore && <Icon name={iconBefore} />}
      <span className="button-label">{label}</span>
    </Link>
  );
};

export default LinkButton;
