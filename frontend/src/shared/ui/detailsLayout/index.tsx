import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IDetailsLayoutProps {
  main: ReactNode;
  side: ReactNode;
}

const DetailsLayout = ({ main, side }: IDetailsLayoutProps): ReactElement => {
  return (
    <div className="details-layout">
      <div className="details-layout-main">{main}</div>
      <aside className="details-layout-side">{side}</aside>
    </div>
  );
};

export default DetailsLayout;
