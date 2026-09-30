interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

export function apiErrorMessage(data: unknown, status: number): string {
  if (!data || typeof data !== "object") {
    return typeof data === "string" && data ? data : `HTTP ${status}`;
  }
  const payload = data as {
    error?: { message?: string };
    detail?: unknown;
  };
  if (payload.error?.message) return payload.error.message;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    const messages = (payload.detail as ValidationIssue[])
      .map((issue) => {
        if (!issue?.msg) return null;
        const field = issue.loc?.at(-1);
        return field ? `${String(field)}: ${issue.msg}` : issue.msg;
      })
      .filter((message): message is string => Boolean(message));
    if (messages.length) return messages.join("; ");
  }
  if (payload.detail && typeof payload.detail === "object") {
    const detail = payload.detail as { message?: string };
    if (detail.message) return detail.message;
  }
  return `HTTP ${status}`;
}
