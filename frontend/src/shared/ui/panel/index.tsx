import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IPanelProps {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  isFlush?: boolean;
}

const Panel = ({
  title,
  actions,
  children,
  isFlush = false,
}: IPanelProps): ReactElement => {
  const flushClassname: string = isFlush ? "flush" : "";

  return (
    <section className={`panel ${flushClassname}`}>
      {(title || actions) && (
        <header className="panel-header">
          {title && <h2 className="heading-medium">{title}</h2>}
          {actions && <div className="panel-actions">{actions}</div>}
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
};

export default Panel;
