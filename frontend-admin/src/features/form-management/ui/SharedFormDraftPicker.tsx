import { formApi } from "../api/formApi";
import {
  SharedDraftPicker,
  type SharedDraftListItem,
} from "@/features/shared-drafts/ui/SharedDraftPicker";

export function SharedFormDraftPicker({
  existingSlugs,
  onImport,
  onClose,
}: {
  existingSlugs: string[];
  onImport: (sourceFormId: number, slug: string) => Promise<unknown>;
  onClose: () => void;
}) {
  return (
    <SharedDraftPicker
      title="Общие черновики форм"
      itemLabel="формы"
      existingSlugs={existingSlugs}
      loadItems={async () =>
        (await formApi.listSharedDrafts()).map((item): SharedDraftListItem => ({
          id: item.source_form_id,
          slug: item.slug,
          title: item.name,
          description: item.description,
          sourceBotName: item.source_bot_name,
        }))
      }
      onImport={(item, slug) => onImport(item.id, slug)}
      onClose={onClose}
    />
  );
}
