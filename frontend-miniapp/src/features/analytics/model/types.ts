export type AnalyticsSourceSurface =
  | "home"
  | "category"
  | "bottom_nav"
  | "form_catalog"
  | "submission_history"
  | "direct";

export type ContentInteractionKind =
  | "link_open"
  | "accordion_item_open"
  | "contact_open"
  | "file_download"
  | "form_card_open"
  | "capability_card_open"
  | "form_catalog_open"
  | "submission_history_open"
  | "faq_list_open"
  | "test_card_open"
  | "test_catalog_open"
  | "test_attempt_history_open";

interface BaseEvent {
  source_surface?: AnalyticsSourceSurface;
}

export type AnalyticsEvent =
  | (BaseEvent & { action_type: "app_open" | "navigator_open" })
  | (BaseEvent & {
      action_type: "content_category_open";
      category_id: number;
      source_category_id?: number;
      content_version_id: number;
    })
  | (BaseEvent & {
      action_type: "content_tab_open";
      category_id: number;
      content_version_id: number;
      tabs_block_id: string;
      tab_key: string;
    })
  | (BaseEvent & {
      action_type: "content_block_interaction";
      interaction_kind: ContentInteractionKind;
      category_id: number;
      // null only for a Task 044 capability shortcut tile tapped from the category grid --
      // it has no content version (see useCapabilityLink).
      content_version_id: number | null;
      block_id: string;
      item_id?: string;
      form_template_id?: number;
      form_version_id?: number;
      faq_id?: number;
      attachment_id?: number;
      capability_installation_id?: number;
      capability_key?: string;
      capability_view_key?: string;
    })
  | (BaseEvent & {
      action_type: "form_open" | "form_start";
      form_template_id: number;
      form_version_id: number;
      category_id?: number;
      content_version_id?: number;
      block_id?: string;
    })
  | (BaseEvent & {
      action_type: "faq_open";
      faq_id: number;
      category_id?: number;
      content_version_id?: number;
      block_id?: string;
    });

export type AnalyticsEnvelope = AnalyticsEvent & {
  event_id: string;
  session_id: string;
};
