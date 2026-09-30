import { useState } from "react";

import { useBotSelection } from "@/features/bot-selection/model/BotSelectionContext";
import { CampaignLinkForm } from "@/features/campaign-links/ui/CampaignLinkForm";
import { CampaignLinkPrintView } from "@/features/campaign-links/ui/CampaignLinkPrintView";
import { CampaignLinksTable } from "@/features/campaign-links/ui/CampaignLinksTable";
import { UnmatchedCampaignLinksPanel } from "@/features/campaign-links/ui/UnmatchedCampaignLinksPanel";
import { useCampaignLinks } from "@/features/campaign-links/model/useCampaignLinks";
import { useUnmatchedCampaignLinks } from "@/features/campaign-links/model/useUnmatchedCampaignLinks";
import type { CampaignLink } from "@/entities/campaign-links/model/types";

export function CampaignLinksPage() {
  const { items, loading, error, creating, deletingId, create, remove } = useCampaignLinks();
  const unmatched = useUnmatchedCampaignLinks();
  const { bots, selectedSlug } = useBotSelection();
  const [printLink, setPrintLink] = useState<CampaignLink | null>(null);

  const selectedBot = bots.find((bot) => bot.slug === selectedSlug);
  const brandColor =
    typeof selectedBot?.branding?.primary_color === "string"
      ? selectedBot.branding.primary_color
      : null;

  const handleDelete = async (link: CampaignLink) => {
    if (!window.confirm(`Удалить ссылку «${link.campaign} / ${link.source} / ${link.placement}»?`))
      return;
    await remove(link.id);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Кампании</h1>
          <p className="page-sub">
            Ссылки и QR-коды для отслеживания переходов из рекламных кампаний
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <CampaignLinkForm creating={creating} onCreate={create} />
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="card">
        <div className="card-body">
          <CampaignLinksTable
            items={items}
            loading={loading}
            deletingId={deletingId}
            onDelete={handleDelete}
            onPrint={setPrintLink}
          />
        </div>
      </div>

      <UnmatchedCampaignLinksPanel
        items={unmatched.items}
        loading={unmatched.loading}
        error={unmatched.error}
      />

      {printLink ? (
        <CampaignLinkPrintView
          link={printLink}
          botName={selectedBot?.name ?? ""}
          brandColor={brandColor}
          onClose={() => setPrintLink(null)}
        />
      ) : null}
    </div>
  );
}
