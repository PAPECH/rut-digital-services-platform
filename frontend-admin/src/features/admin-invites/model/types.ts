import type { StaffPermissions } from "@/features/staff-access/model/types";

export type InviteScope = "bot" | "platform";

export type InviteStatus = "active" | "expired" | "exhausted" | "revoked";

export interface AdminInvite {
  id: number;
  kind: "platform" | "bot_staff";
  full_name: string;
  role: "employee" | "admin" | null;
  permissions: StaffPermissions | null;
  max_uses: number;
  used_count: number;
  expires_at: string;
  revoked_at: string | null;
  created_at: string | null;
  status: InviteStatus;
}

export interface CreatedAdminInvite {
  invite: AdminInvite;
  start_param: string;
  link: string | null;
}

export interface AdminInviteDraft {
  full_name: string;
  ttl_hours: number;
  max_uses: number;
  role: "employee" | "admin";
  permissions: StaffPermissions;
}

export const INVITE_TTL_OPTIONS: Array<{ hours: number; label: string }> = [
  { hours: 24, label: "1 день" },
  { hours: 72, label: "3 дня" },
  { hours: 168, label: "7 дней" },
  { hours: 336, label: "14 дней" },
  { hours: 720, label: "30 дней" },
];

export const INVITE_STATUS_LABELS: Record<InviteStatus, string> = {
  active: "Активно",
  expired: "Истекло",
  exhausted: "Использовано",
  revoked: "Отозвано",
};
