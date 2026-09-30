import { api } from "@/api/client";
import type {
  CampaignLink,
  CampaignLinkCreateInput,
  UnmatchedCampaignLink,
} from "@/entities/campaign-links/model/types";

export const campaignLinksApi = {
  list: () => api.get<CampaignLink[]>("/campaign-links"),
  create: (input: CampaignLinkCreateInput) =>
    api.post<CampaignLink>("/campaign-links", input),
  remove: (id: number) => api.del<void>(`/campaign-links/${id}`),
  unmatched: () => api.get<UnmatchedCampaignLink[]>("/campaign-links/unmatched"),
};
