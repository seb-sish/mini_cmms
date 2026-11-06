import Link from "next/link";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

export interface IBreadcrumb {
  label: string;
  href: string;
}

interface IPageHeaderProps {
  title: ReactNode;
  breadcrumbs?: IBreadcrumb[];
  actions?: ReactNode;
  bottomBar?: ReactNode;
}

const PageHeader = ({
  title,
  breadcrumbs,
  actions,
  bottomBar,
}: IPageHeaderProps): ReactElement => {
  return (
    <header className="page-header">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav
          className="page-header-breadcrumbs"
          aria-label="Навигационная цепочка"
        >
          <ol>
            {breadcrumbs.map((breadcrumb) => (
              <li key={breadcrumb.href} className="body-small">
                <Link href={breadcrumb.href}>{breadcrumb.label}</Link>
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="page-header-main">
        <h1 className="page-header-title heading-xlarge">{title}</h1>
        {actions && <div className="page-header-actions">{actions}</div>}
      </div>
      {bottomBar && <div className="page-header-bottom-bar">{bottomBar}</div>}
    </header>
  );
};

export default PageHeader;
