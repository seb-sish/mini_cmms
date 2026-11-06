import EmptyState from "@shared/ui/emptyState";
import LinkButton from "@shared/ui/linkButton";
import { ButtonAppearance } from "@shared/ui/button";
import { IconName } from "@shared/ui/icon";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import "./style.css";

const NotFoundPage = (): ReactElement => {
  return (
    <div className="not-found-page">
      <EmptyState
        title="Страница не найдена"
        description="Проверьте адрес или вернитесь на главную страницу."
        icon={IconName.WARNING}
        action={
          <LinkButton
            label="На главную"
            href={ROUTES.HOME}
            appearance={ButtonAppearance.PRIMARY}
          />
        }
      />
    </div>
  );
};

export default NotFoundPage;
