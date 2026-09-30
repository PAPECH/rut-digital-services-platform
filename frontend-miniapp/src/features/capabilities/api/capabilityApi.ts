import { api } from "@/api/client";
import type {
  AdmissionRatingLookup,
  AdmissionRatingSubscription,
  RequestStatusLookup,
  RequestStatusSubscription,
  RutGroupSchedule,
  RutScheduleNavigationTree,
} from "@/entities/capability/model/types";

export const capabilityApi = {
  viewOpened: (
    capabilityKey: string,
    installationId: number,
    viewKey: string,
  ) =>
    api.post(`/capabilities/${capabilityKey}/events/view-open`, {
      installation_id: installationId,
      view_key: viewKey,
    }),
  requestStatus: {
    lookup: (requestNumber: string) =>
      api.get<RequestStatusLookup>(
        `/capabilities/request-status/lookup?request_number=${encodeURIComponent(requestNumber)}`,
      ),
    subscription: () =>
      api.get<RequestStatusSubscription>(
        "/capabilities/request-status/subscription",
      ),
    subscribe: (requestNumber: string) =>
      api.post<RequestStatusSubscription>(
        "/capabilities/request-status/subscribe",
        { request_number: requestNumber },
      ),
    unsubscribe: (requestNumber: string) =>
      api.post<RequestStatusSubscription>(
        "/capabilities/request-status/unsubscribe",
        { request_number: requestNumber },
      ),
  },
  rutSchedule: {
    navigationTree: () =>
      api.get<RutScheduleNavigationTree>("/capabilities/rut-schedule/navigation-tree"),
    schedule: (groupExternalId: string) =>
      api.get<RutGroupSchedule>(
        `/capabilities/rut-schedule/groups/${encodeURIComponent(groupExternalId)}/schedule`,
      ),
  },
  admissionRating: {
    lookup: (applicantCode: string) =>
      api.get<AdmissionRatingLookup>(
        `/capabilities/admission-rating/lookup?applicant_code=${encodeURIComponent(applicantCode)}`,
      ),
    subscription: () =>
      api.get<AdmissionRatingSubscription>(
        "/capabilities/admission-rating/subscription",
      ),
    subscribe: (applicantCode: string) =>
      api.post<AdmissionRatingSubscription>(
        "/capabilities/admission-rating/subscribe",
        { applicant_code: applicantCode },
      ),
    unsubscribe: (applicantCode: string) =>
      api.post<AdmissionRatingSubscription>(
        "/capabilities/admission-rating/unsubscribe",
        { applicant_code: applicantCode },
      ),
  },
};
