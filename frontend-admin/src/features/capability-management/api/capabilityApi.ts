import type { CapabilityInstallation } from "@/api/types";
import { api } from "@/api/client";
import type {
  RutScheduleGroupWithLastSync,
  RutScheduleInstitute,
  RutScheduleManualSyncRequest,
  RutScheduleRefreshGroupsResult,
} from "@/entities/capability/model/types";

export const capabilityApi = {
  list: () => api.get<CapabilityInstallation[]>("/capabilities/admin"),
  save: (
    capabilityKey: string,
    expectedRevision: number,
    config: Record<string, unknown>,
  ) =>
    api.put<CapabilityInstallation>(
      `/capabilities/admin/${capabilityKey}/config`,
      { expected_revision: expectedRevision, config },
    ),
  enable: (capabilityKey: string) =>
    api.post<CapabilityInstallation>(
      `/capabilities/admin/${capabilityKey}/enable`,
      {},
    ),
  disable: (capabilityKey: string) =>
    api.post<CapabilityInstallation>(
      `/capabilities/admin/${capabilityKey}/disable`,
      {},
    ),
  test: (capabilityKey: string) =>
    api.post<CapabilityInstallation>(
      `/capabilities/admin/${capabilityKey}/test`,
      {},
    ),
  reorder: (capabilityKeys: string[]) =>
    api.post<CapabilityInstallation[]>("/capabilities/admin/reorder", {
      capability_keys: capabilityKeys,
    }),
  // Platform-admin-only rut_schedule manual sync controls (Task 045 + institute-scope follow-up).
  rutSchedule: {
    triggerSyncForGroup: (groupExternalId: string) =>
      api.post<RutScheduleManualSyncRequest>("/capabilities/rut-schedule/admin/sync", {
        scope: "group",
        group_external_id: groupExternalId,
        institute_external_id: null,
      }),
    triggerSyncForInstitute: (instituteExternalId: string) =>
      api.post<RutScheduleManualSyncRequest>("/capabilities/rut-schedule/admin/sync", {
        scope: "institute",
        group_external_id: null,
        institute_external_id: instituteExternalId,
      }),
    triggerSyncForAll: () =>
      api.post<RutScheduleManualSyncRequest>("/capabilities/rut-schedule/admin/sync", {
        scope: "all",
        group_external_id: null,
        institute_external_id: null,
      }),
    institutes: () =>
      api.get<RutScheduleInstitute[]>("/capabilities/rut-schedule/admin/institutes"),
    syncRequests: (limit = 50) =>
      api.get<RutScheduleManualSyncRequest[]>(
        `/capabilities/rut-schedule/admin/sync-requests?limit=${limit}`,
      ),
    groups: (limit = 1000) =>
      api.get<RutScheduleGroupWithLastSync[]>(
        `/capabilities/rut-schedule/admin/groups?limit=${limit}`,
      ),
    refreshGroups: () =>
      api.post<RutScheduleRefreshGroupsResult>(
        "/capabilities/rut-schedule/admin/refresh-groups",
        {},
      ),
  },
};
