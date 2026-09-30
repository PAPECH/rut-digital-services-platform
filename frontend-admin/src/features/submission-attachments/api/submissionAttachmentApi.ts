import { api } from "@/api/client";
import type { SubmissionAttachment } from "@/api/types";

export function listSubmissionAttachments(
  submissionId: number,
): Promise<SubmissionAttachment[]> {
  return api.get(`/submissions/${submissionId}/attachments`);
}

export async function fetchSubmissionAttachment(
  path: string,
): Promise<Blob> {
  return api.getBlob(path);
}
