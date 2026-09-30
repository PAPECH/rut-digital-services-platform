import { useState } from "react";
import type { MouseEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthProvider";
import { trackAnalyticsEventInBackground } from "@/features/analytics/api/analyticsApi";
import { useIsPreviewMode } from "@/features/content/model/PreviewModeContext";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { getMissingProfileFields } from "@/features/profile-requirements/model/profileRequirements";

/**
 * Resolves a `capability_key`/`view_key` pair against the platform manifest and applies the
 * gating (preview mode, uninstalled/disabled capability, incomplete profile) plus the
 * `capability_card_open` analytics event -- shared by `CapabilityActionBlockRenderer` (a
 * standalone content block) and a Task 044 capability shortcut tile in `ContentCategoryGrid`, the
 * two places that link straight into a capability view.
 *
 * `contentVersionId` is `null` for a shortcut tile (tapped from the category grid, not from
 * inside a rendered content page/version) -- the backend's `content_block_interaction` validation
 * only requires it for interaction kinds other than `capability_card_open`.
 */
export function useCapabilityLink({
  capabilityKey,
  viewKey,
  categoryId,
  contentVersionId,
  blockId,
}: {
  capabilityKey: string;
  viewKey: string;
  categoryId: number;
  contentVersionId: number | null;
  blockId: string;
}) {
  const navigate = useNavigate();
  const { profile } = useAuth();
  const { manifest } = usePlatform();
  const isPreview = useIsPreviewMode();
  const [message, setMessage] = useState<string | null>(null);
  const capability = manifest?.capabilities.find((item) => item.key === capabilityKey);
  const view = capability?.views.find((item) => item.key === viewKey);

  const handleClick = (event: MouseEvent) => {
    if (isPreview) {
      event.preventDefault();
      setMessage("Недоступно в предпросмотре");
      return;
    }
    if (!capability || !view) {
      event.preventDefault();
      setMessage("Сервис временно недоступен");
      return;
    }
    if (view.requires_complete_profile) {
      const missing = getMissingProfileFields(profile, manifest?.bot.profile_schema);
      if (missing.length) {
        event.preventDefault();
        setMessage(`Сначала заполните профиль: ${missing.join(", ")}`);
        return;
      }
    }
    trackAnalyticsEventInBackground({
      action_type: "content_block_interaction",
      interaction_kind: "capability_card_open",
      source_surface: "category",
      category_id: categoryId,
      content_version_id: contentVersionId,
      block_id: blockId,
      capability_installation_id: capability.installation_id,
      capability_key: capability.key,
      capability_view_key: view.key,
    });
  };

  return {
    capability,
    view,
    message,
    handleClick,
    navigateToProfile: () => navigate("/profile"),
  };
}
