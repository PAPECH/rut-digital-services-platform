import { useCallback, useEffect, useState } from "react";

import type { CapabilityInstallation } from "@/api/types";
import { capabilityApi } from "@/features/capability-management/api/capabilityApi";

export function useCapabilities() {
  const [installations, setInstallations] = useState<CapabilityInstallation[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setInstallations(await capabilityApi.list());
    } catch (reason) {
      setError((reason as Error).message || "Не удалось загрузить возможности");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void load(), [load]);

  const replace = (fresh: CapabilityInstallation) =>
    setInstallations((current) =>
      current.map((item) =>
        item.capability_key === fresh.capability_key ? fresh : item,
      ),
    );

  const act = async (
    key: string,
    action: string,
    request: () => Promise<CapabilityInstallation>,
    success: string,
  ) => {
    setBusy(`${key}:${action}`);
    setError(null);
    setNotice(null);
    try {
      replace(await request());
      setNotice(success);
    } catch (reason) {
      setError((reason as Error).message || "Операция не выполнена");
      throw reason;
    } finally {
      setBusy(null);
    }
  };

  return {
    installations,
    loading,
    busy,
    error,
    notice,
    reload: load,
    save: (item: CapabilityInstallation, config: Record<string, unknown>) =>
      act(
        item.capability_key,
        "save",
        () =>
          capabilityApi.save(item.capability_key, item.config_revision, config),
        "Настройки сохранены",
      ),
    enable: (item: CapabilityInstallation) =>
      act(
        item.capability_key,
        "enable",
        () => capabilityApi.enable(item.capability_key),
        "Возможность включена",
      ),
    disable: (item: CapabilityInstallation) =>
      act(
        item.capability_key,
        "disable",
        () => capabilityApi.disable(item.capability_key),
        "Возможность отключена",
      ),
    test: (item: CapabilityInstallation) =>
      act(
        item.capability_key,
        "test",
        () => capabilityApi.test(item.capability_key),
        "Подключение работает",
      ),
    move: async (capabilityKey: string, direction: -1 | 1) => {
      const index = installations.findIndex(
        (item) => item.capability_key === capabilityKey,
      );
      const target = index + direction;
      if (index < 0 || target < 0 || target >= installations.length) return;
      const keys = installations.map((item) => item.capability_key);
      [keys[index], keys[target]] = [keys[target], keys[index]];
      setBusy(`${capabilityKey}:reorder`);
      setError(null);
      try {
        setInstallations(await capabilityApi.reorder(keys));
      } catch (reason) {
        setError((reason as Error).message || "Не удалось изменить порядок");
      } finally {
        setBusy(null);
      }
    },
  };
}
