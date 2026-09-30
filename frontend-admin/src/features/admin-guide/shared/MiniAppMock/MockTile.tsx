import { MockPhoto } from "./MockPhoto";
import * as mock from "./MiniAppMock.css";

/**
 * A mini-app category card (`.cms-category-card`): title and subtitle on the left, the icon — or
 * the category image, which replaces it — on the right. Also the look of «Подключаемая
 * возможность». Pass `onClick` to make it tappable.
 */
export function MockTile({
  title,
  subtitle,
  icon = "▦",
  image = false,
  filled = false,
  onClick,
  className,
}: {
  title: string;
  subtitle?: string;
  icon?: string;
  image?: boolean;
  filled?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  const classes = [
    mock.tile,
    filled ? mock.tileFilled : "",
    onClick ? mock.tileClickable : "",
    className ?? "",
  ].join(" ");
  const content = (
    <>
      <span className={mock.tileText}>
        <span className={mock.tileTitle}>{title}</span>
        {subtitle ? <span className={mock.tileSubtitle}>{subtitle}</span> : null}
      </span>
      <span className={mock.tileIcon} aria-hidden>
        {image ? <MockPhoto /> : icon}
      </span>
    </>
  );
  return onClick ? (
    <button type="button" className={classes} onClick={onClick}>
      {content}
    </button>
  ) : (
    <div className={classes}>{content}</div>
  );
}
