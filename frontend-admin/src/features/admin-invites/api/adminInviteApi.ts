import { api } from "@/api/client";
import type {
  AdminInvite,
  AdminInviteDraft,
  CreatedAdminInvite,
  InviteScope,
} from "@/features/admin-invites/model/types";

const BASE_PATH: Record<InviteScope, string> = {
  bot: "/instances/current/admin-invites",
  platform: "/platform-admins/invites",
};

function payload(scope: InviteScope, draft: AdminInviteDraft) {
  const common = {
    full_name: draft.full_name,
    ttl_hours: draft.ttl_hours,
    max_uses: draft.max_uses,
  };
  return scope === "bot"
    ? { ...common, role: draft.role, permissions: draft.permissions }
    : common;
}

export const adminInviteApi = {
  list: (scope: InviteScope) => api.get<AdminInvite[]>(BASE_PATH[scope]),
  create: (scope: InviteScope, draft: AdminInviteDraft) =>
    api.post<CreatedAdminInvite>(BASE_PATH[scope], payload(scope, draft)),
  revoke: (scope: InviteScope, inviteId: number) =>
    api.del(`${BASE_PATH[scope]}/${inviteId}`),
};
