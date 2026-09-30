import type { AdminRole } from "@/api/types";

export interface StaffPermissions {
  can_process_submissions: boolean;
  can_manage_content: boolean;
  can_manage_forms: boolean;
  can_manage_staff: boolean;
  can_manage_maintenance: boolean;
  can_manage_capabilities: boolean;
  can_manage_campaigns: boolean;
}

export interface StaffAccess {
  id: number;
  admin_id: number;
  bot_instance_id: number;
  max_user_id: string;
  full_name: string;
  role: AdminRole;
  is_active: boolean;
  permissions: StaffPermissions;
}

export interface GrantStaffAccessDraft {
  max_user_id: string;
  full_name: string;
  role: "employee" | "admin";
  permissions: StaffPermissions;
}

export const DEFAULT_STAFF_PERMISSIONS: StaffPermissions = {
  can_process_submissions: true,
  can_manage_content: false,
  can_manage_forms: false,
  can_manage_staff: false,
  can_manage_maintenance: false,
  can_manage_capabilities: false,
  can_manage_campaigns: false,
};

export const PERMISSION_LABELS: Array<{
  key: keyof StaffPermissions;
  label: string;
}> = [
  { key: "can_process_submissions", label: "Обработка заявок" },
  { key: "can_manage_content", label: "Управление контентом" },
  { key: "can_manage_forms", label: "Управление формами" },
  { key: "can_manage_staff", label: "Управление сотрудниками" },
  { key: "can_manage_maintenance", label: "Технический режим" },
  { key: "can_manage_capabilities", label: "Спец. возможности" },
  { key: "can_manage_campaigns", label: "Кампании" },
];

