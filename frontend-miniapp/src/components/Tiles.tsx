import { Link } from "react-router-dom";

const iconStyle: React.CSSProperties = {
  width: 20,
  height: 20,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

export function Tile({
  to,
  icon,
  title,
  sub,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  sub: string;
}) {
  return (
    <Link to={to} className="tile">
      <div className="tile-icon">
        <span className="ico" style={iconStyle}>
          {icon}
        </span>
      </div>
      <b>{title}</b>
      <small>{sub}</small>
    </Link>
  );
}

export function LargeTile({
  to,
  icon,
  title,
  sub,
  color = "dark",
  onClick,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  sub: string;
  color?: "dark" | "light";
  onClick?: () => Promise<void>;
}) {
  return (
    <Link
      onClick={onClick}
      to={to}
      className={`tile tile-large ${color === "light" ? "tile-large--light" : ""}`}
    >
      <div style={{ height: "100%", alignContent: "center" }}>
        <div className="tile-icon">
          <span className="ico" style={iconStyle}>
            {icon}
          </span>
        </div>
      </div>

      <div className="tile-content">
        <b>{title}</b>
        <small>{sub}</small>
      </div>
    </Link>
  );
}
