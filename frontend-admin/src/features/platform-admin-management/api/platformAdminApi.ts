import { api } from "@/api/client";
import type {
  EnsurePlatformAdminDraft,
  EnsurePlatformAdminResult,
  PlatformAdminAccount,
} from "@/features/platform-admin-management/model/types";

export const platformAdminApi = {
  list: () => api.get<PlatformAdminAccount[]>("/platform-admins"),
  ensure: (draft: EnsurePlatformAdminDraft) =>
    api.post<EnsurePlatformAdminResult>("/platform-admins", draft),
};
