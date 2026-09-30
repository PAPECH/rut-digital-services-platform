export interface PlatformAdminAccount {
  id: number;
  max_user_id: string;
  full_name: string;
  is_active: boolean;
}

export interface EnsurePlatformAdminDraft {
  max_user_id: string;
  full_name: string;
}

export interface EnsurePlatformAdminResult {
  account: PlatformAdminAccount;
  created: boolean;
  promoted: boolean;
  reactivated: boolean;
}
