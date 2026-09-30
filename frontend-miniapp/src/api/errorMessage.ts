interface ErrorEnvelope {
  error?: unknown;
  detail?: unknown;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function cleanValidationMessage(message: string): string {
  return message.replace(/^Value error,\s*/i, "").trim();
}

function messageFromDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail.trim();

  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue) => {
        const message = asRecord(issue)?.msg;
        return typeof message === "string"
          ? cleanValidationMessage(message)
          : null;
      })
      .filter((message): message is string => Boolean(message));
    const uniqueMessages = [...new Set(messages)];
    return uniqueMessages.length ? uniqueMessages.join("; ") : null;
  }

  const detailMessage = asRecord(detail)?.message;
  return typeof detailMessage === "string" && detailMessage.trim()
    ? detailMessage.trim()
    : null;
}

export function apiErrorMessage(payload: unknown, status: number): string {
  const envelope = asRecord(payload) as ErrorEnvelope | null;
  const nestedMessage = asRecord(envelope?.error)?.message;
  if (typeof nestedMessage === "string" && nestedMessage.trim()) {
    return nestedMessage.trim();
  }

  const detailMessage = messageFromDetail(envelope?.detail);
  if (detailMessage) return detailMessage;

  if (typeof payload === "string" && payload.trim()) return payload.trim();
  return `HTTP ${status}`;
}
