import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { BotRuntime } from "@/api/types";

export interface RuntimeCredentialPayload {
  source: "environment" | "managed";
  credential_env_key: string | null;
  bot_token: string | null;
  mode: BotRuntime["mode"];
}

export function useBotRuntime(botId: number) {
  const [runtime, setRuntime] = useState<BotRuntime | null>(null);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    api.get<BotRuntime>(`/instances/${botId}/runtime`)
      .then((value) => {
        if (active) setRuntime(value);
      })
      .catch((reason) => {
        if (active) setError((reason as Error).message);
      });
    return () => { active = false; };
  }, [botId]);

  const configure = async (payload: RuntimeCredentialPayload) => {
    setBusy(true);
    setError(null);
    setIssuedToken(null);
    try {
      const value = await api.put<BotRuntime>(
        `/instances/${botId}/runtime/credential`,
        payload,
      );
      setRuntime(value);
      return value;
    } catch (reason) {
      setError((reason as Error).message);
      throw reason;
    } finally {
      setBusy(false);
    }
  };

  const rotateRuntimeToken = async () => {
    setBusy(true);
    setError(null);
    try {
      const value = await api.post<{ runtime_token: string }>(
        `/instances/${botId}/runtime/rotate-token`,
      );
      setIssuedToken(value.runtime_token);
      setRuntime((current) => current ? {
        ...current,
        token_configured: true,
        status: "not_connected",
      } : current);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return { runtime, issuedToken, busy, error, configure, rotateRuntimeToken };
}
