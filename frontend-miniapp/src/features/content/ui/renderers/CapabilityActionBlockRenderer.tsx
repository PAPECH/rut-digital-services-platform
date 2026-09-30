import { Link } from "react-router-dom";

import { ContentIcon } from "@/entities/content/ui/ContentIcon";
import type {
  BlockRendererProps,
  CapabilityActionBlock,
} from "@/entities/content/model/types";
import { useCapabilityLink } from "@/features/capabilities/model/useCapabilityLink";

export function CapabilityActionBlockRenderer({
  block,
  content,
}: BlockRendererProps<CapabilityActionBlock>) {
  const { capability, view, message, handleClick, navigateToProfile } = useCapabilityLink({
    capabilityKey: block.capability_key,
    viewKey: block.view_key,
    categoryId: content.id,
    contentVersionId: content.version_id,
    blockId: block.id,
  });
  return (
    <>
      <Link
        className="cms-category-card"
        to={view?.path ?? "#"}
        aria-disabled={!capability || !view}
        onClick={handleClick}
      >
        <span className="cms-category-text">
          <strong>{block.title}</strong>
          {block.description ? <small>{block.description}</small> : null}
        </span>
        <span className="cms-category-card__icon" aria-hidden="true">
          <ContentIcon name={view?.icon ?? "folder"} />
        </span>
      </Link>
      {message ? (
        <div className="cms-form-action__warning">
          {message}
          {view?.requires_complete_profile ? (
            <button type="button" onClick={navigateToProfile}>
              Перейти в профиль
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
