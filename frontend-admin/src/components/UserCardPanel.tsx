import { useCallback, useEffect, useRef, useState } from "react";
import { api, getToken } from "@/api/client";
import {
  createAdminWebSocketUrl,
  resolveAdminAssetUrl,
} from "@/api/config";
import { getSelectedBotSlug } from "@/shared/tenant/selectedBotStorage";
import type { MessageItem, Submission, UserSummary } from "@/api/types";
import { Avatar } from "@/components/Avatar";
import { Icon } from "@/components/Icon";
import { StatusTag } from "@/components/StatusTag";
import { formatDateTime } from "@/lib/status";
import {
  type UploadedFile,
  formatBytes,
  isImageMime,
  uploadFile,
} from "@/api/files";

interface UserCard {
  user: UserSummary;
  profile_fields: Array<{ key: string; label: string; value: unknown }>;
  messages: MessageItem[];
  submissions: Submission[];
}

interface Props {
  userId: number;
  currentAdminId: number | null;
  onClose: () => void;
  onOpenTickets?: (userId: number) => void;
}

function fullName(u: UserSummary): string {
  const parts = [u.last_name, u.first_name, u.patronymic].filter(
    Boolean,
  ) as string[];
  if (parts.length) return parts.join(" ");
  return u.username || u.user_id;
}

function formatDate(d: string | null): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("ru-RU");
  } catch {
    return d;
  }
}

export function UserCardPanel({
  userId,
  currentAdminId,
  onClose,
  onOpenTickets,
}: Props) {
  const [data, setData] = useState<UserCard | null>(null);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [banDraft, setBanDraft] = useState<{
    ban_chat: boolean;
    ban_chat_reason: string;
    ban_forms: boolean;
    ban_forms_reason: string;
    ban_app: boolean;
    ban_app_reason: string;
  } | null>(null);
  const [banBusy, setBanBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  const reload = useCallback(async () => {
    const r = await api.get<UserCard>(`/users/${userId}`);
    setData(r);
    setBanDraft({
      ban_chat: r.user.ban_chat,
      ban_chat_reason: r.user.ban_chat_reason ?? "",
      ban_forms: r.user.ban_forms,
      ban_forms_reason: r.user.ban_forms_reason ?? "",
      ban_app: r.user.ban_app,
      ban_app_reason: r.user.ban_app_reason ?? "",
    });
  }, [userId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!data) return;
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [data?.messages.length]);

  // ───────── Realtime: WS на user-комнату (§ задача 4) ─────────
  // Без этого новые сообщения от пользователя из MAX появятся в карточке только
  // при перезагрузке. В TicketsPage это уже работает — переиспользуем тот же поток.
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const url = createAdminWebSocketUrl("/ws/chat");
    url.searchParams.set("token", token);
    url.searchParams.set("bot_slug", getSelectedBotSlug());
    url.searchParams.set("user_pk", String(userId));
    const ws = new WebSocket(url.toString());
    ws.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data);
        if (ev.type !== "message") return;
        const msg = ev.data as MessageItem;
        if (msg.user_id !== userId) return;
        // Не дублировать собственные исходящие — они уже добавлены локально после POST.
        const isMyOutgoing =
          msg.direction === "out" &&
          currentAdminId !== null &&
          msg.replied_by_admin_id === currentAdminId;
        if (isMyOutgoing) return;
        setData((prev) => {
          if (!prev) return prev;
          if (prev.messages.some((m) => m.id === msg.id)) return prev;
          return { ...prev, messages: [...prev.messages, msg] };
        });
      } catch {}
    };
    return () => ws.close();
  }, [userId, currentAdminId]);

  const onPickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setUploading(true);
    try {
      const uploaded = await uploadFile(f);
      setPending((prev) => [...prev, uploaded]);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const send = async () => {
    if (!data) return;
    const trimmed = draft.trim();
    if (!trimmed && pending.length === 0) return;
    setSending(true);
    try {
      const msg = await api.post<MessageItem>(
        `/messages/to-user/${data.user.id}`,
        {
          text: trimmed || null,
          attachment_ids: pending.map((p) => p.id),
        },
      );
      setData({ ...data, messages: [...data.messages, msg] });
      setDraft("");
      setPending([]);
    } finally {
      setSending(false);
    }
  };

  const saveBan = async () => {
    if (!data || !banDraft) return;
    setBanBusy(true);
    try {
      const updated = await api.patch<UserSummary>(
        `/users/${data.user.id}/ban`,
        {
          ban_chat: banDraft.ban_chat,
          ban_chat_reason: banDraft.ban_chat_reason.trim() || null,
          ban_forms: banDraft.ban_forms,
          ban_forms_reason: banDraft.ban_forms_reason.trim() || null,
          ban_app: banDraft.ban_app,
          ban_app_reason: banDraft.ban_app_reason.trim() || null,
        },
      );
      setData({ ...data, user: updated });
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBanBusy(false);
    }
  };

  if (!data) {
    return (
      <Drawer onClose={onClose}>
        <div
          style={{ padding: 40, textAlign: "center", color: "var(--ink-400)" }}
        >
          Загрузка…
        </div>
      </Drawer>
    );
  }

  const u = data.user;
  const name = fullName(u);

  return (
    <Drawer onClose={onClose}>
      <div
        style={{
          padding: '18px 22px',
          borderBottom: '1px solid var(--line)',
          display: 'flex',
          gap: 12,
          alignItems: 'center',
        }}>
        <Avatar size='lg' user={{ photo_url: u?.photo_url, fullName: name }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 18,
              fontWeight: 700,
            }}>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
            {u.phone_verified && (
              <span title='Телефон подтверждён' style={{ color: 'var(--brand)', display: 'inline-flex' }}>
                <Icon.Check />
              </span>
            )}
          </div>
          {u.username && <div style={{ fontSize: 12.5, color: 'var(--ink-400)' }}>@{u.username}</div>}
        </div>
        <button className='btn btn-ghost btn-icon' onClick={onClose}>
          ×
        </button>
      </div>

      <div style={{ padding: '16px 22px', overflow: 'auto', flex: 1 }}>
        <Section title='Профиль'>
          <KeyVal label='Фамилия' value={u.last_name ?? '—'} />
          <KeyVal label='Имя' value={u.first_name ?? '—'} />
          <KeyVal label='Отчество' value={u.patronymic ?? '—'} />
          <KeyVal label='Дата рождения' value={formatDate(u.birth_date)} />
          {data.profile_fields.map((field) => (
            <KeyVal key={field.key} label={field.label} value={formatProfileValue(field.value)} />
          ))}
        </Section>

        <Section title='Контакты'>
          <KeyVal label='MAX ID' value={u.user_id} mono />
          <KeyVal label='Источник' value={u.system} />
          <KeyVal
            label='Телефон'
            value={u.phone ? `${u.phone}${u.phone_verified ? '  ✓' : '  (не подтверждён)'}` : '—'}
          />
          <KeyVal label='Почта' value={u.email ?? '—'} />
        </Section>

        {u.campaign_source && (
          <Section title='Откуда пришёл'>
            <KeyVal label='Кампания' value={u.campaign_source.campaign} />
            <KeyVal label='Источник' value={u.campaign_source.source} />
            <KeyVal label='Размещение' value={u.campaign_source.placement} />
          </Section>
        )}

        <Section title='Согласие на обработку персональных данных'>
          {u.consent_revoked_at ? (
            <>
              <KeyVal label='Согласие' value='Отозвано' />
              <KeyVal label='Отозвано' value={formatDateTime(u.consent_revoked_at)} />
              <KeyVal
                label='Данные будут удалены'
                value={u.consent_deletion_due_at ? formatDateTime(u.consent_deletion_due_at) : '—'}
              />
            </>
          ) : (
            <>
              <KeyVal label='Согласие' value='Получено' />
              <KeyVal
                label='Дата'
                value={u.consent_given_at ? formatDateTime(u.consent_given_at) : '—'}
              />
            </>
          )}
        </Section>

        {banDraft && (
          <Section title='Блокировки'>
            <BanRow
              label='Чат'
              banned={banDraft.ban_chat}
              reason={banDraft.ban_chat_reason}
              onToggle={(v) => setBanDraft({ ...banDraft, ban_chat: v })}
              onReason={(v) => setBanDraft({ ...banDraft, ban_chat_reason: v })}
            />
            <BanRow
              label='Подача форм'
              banned={banDraft.ban_forms}
              reason={banDraft.ban_forms_reason}
              onToggle={(v) => setBanDraft({ ...banDraft, ban_forms: v })}
              onReason={(v) => setBanDraft({ ...banDraft, ban_forms_reason: v })}
            />
            <BanRow
              label='Открытие приложения'
              banned={banDraft.ban_app}
              reason={banDraft.ban_app_reason}
              onToggle={(v) => setBanDraft({ ...banDraft, ban_app: v })}
              onReason={(v) => setBanDraft({ ...banDraft, ban_app_reason: v })}
            />
            <button
              className='btn btn-secondary btn-sm'
              style={{ marginTop: 8 }}
              disabled={banBusy}
              onClick={() => void saveBan()}>
              {banBusy ? 'Сохраняем…' : 'Сохранить блокировки'}
            </button>
          </Section>
        )}

        <Section title={`Заявки (${data.submissions.length})`}>
          {data.submissions.length === 0 ? (
            <div className='muted' style={{ fontSize: 13 }}>
              Нет заявок
            </div>
          ) : (
            data.submissions.map((s) => (
              <div
                key={s.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '10px 0',
                  borderBottom: '1px solid var(--line)',
                }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>Заявка #{s.id}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--ink-400)' }}>
                    {formatDateTime(s.created_at)}
                  </div>
                </div>
                <StatusTag status={s.status} />
              </div>
            ))
          )}
        </Section>

        <Section
          title={`История переписки (${data.messages.length})`}
          action={
            onOpenTickets ? (
              <button className='btn btn-secondary btn-sm' onClick={() => onOpenTickets(u.id)}>
                Открыть в тикетах
              </button>
            ) : null
          }>
          <div
            ref={messagesRef}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              maxHeight: 360,
              overflow: 'auto',
              paddingRight: 4,
            }}>
            {data.messages.length === 0 && (
              <div className='muted' style={{ fontSize: 13 }}>
                Сообщений нет
              </div>
            )}
            {data.messages.map((m) => (
              <MessageBubble key={m.id} msg={m} currentAdminId={currentAdminId} />
            ))}
          </div>
        </Section>
      </div>

      <div
        style={{
          padding: 12,
          borderTop: '1px solid var(--line)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}>
        {pending.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {pending.map((p) => (
              <span key={p.id} className='tag outline' style={{ paddingRight: 4 }}>
                {p.name} · {formatBytes(p.size_bytes)}
                <button
                  onClick={() => setPending((prev) => prev.filter((x) => x.id !== p.id))}
                  style={{
                    background: 'transparent',
                    border: 0,
                    cursor: 'pointer',
                    marginLeft: 4,
                    color: 'var(--ink-400)',
                  }}>
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <input ref={fileInputRef} type='file' hidden onChange={(e) => void onPickFile(e)} />
          <button
            className='btn btn-secondary btn-icon'
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            title='Прикрепить файл'>
            <span className='ico'>
              <Icon.Paperclip />
            </span>
          </button>
          <textarea
            className='textarea'
            rows={1}
            style={{ resize: 'none', flex: 1 }}
            placeholder='Написать сообщение…'
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void send()
              }
            }}
          />
          <button
            className='btn btn-primary'
            disabled={sending || (!draft.trim() && pending.length === 0)}
            onClick={() => void send()}>
            Отправить
          </button>
        </div>
      </div>
    </Drawer>
  )
}

function Drawer({
  children,
  onClose,
}: {
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        justifyContent: "flex-end",
      }}
    >
      <div
        onClick={onClose}
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(11,23,41,.32)",
        }}
      />
      <div
        style={{
          position: "relative",
          width: 600,
          maxWidth: "100vw",
          height: "100%",
          background: "#fff",
          borderLeft: "1px solid var(--line)",
          boxShadow: "var(--shadow-lg)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div className="user-card-section-head">
        <h4
          style={{
            fontSize: 12,
            color: "var(--ink-500)",
            textTransform: "uppercase",
            letterSpacing: ".06em",
            margin: "0 0 10px",
          }}
        >
          {title}
        </h4>
        {action}
      </div>
      {children}
    </div>
  );
}

function formatProfileValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function KeyVal({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "6px 0",
        fontSize: 13,
      }}
    >
      <span style={{ color: "var(--ink-500)" }}>{label}</span>
      <span
        style={{
          fontWeight: 600,
          fontFamily: mono ? "var(--mono)" : undefined,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function BanRow({
  label,
  banned,
  reason,
  onToggle,
  onReason,
}: {
  label: string;
  banned: boolean;
  reason: string;
  onToggle: (v: boolean) => void;
  onReason: (v: string) => void;
}) {
  return (
    <div
      style={{
        padding: "8px 0",
        borderBottom: "1px solid var(--line)",
      }}
    >
      <label
        style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}
      >
        <input
          type="checkbox"
          checked={banned}
          onChange={(e) => onToggle(e.target.checked)}
        />
        <span style={{ fontWeight: 600 }}>{label}</span>
      </label>
      {banned && (
        <input
          className="input"
          style={{ marginTop: 6 }}
          placeholder="Причина (видна пользователю)"
          value={reason}
          onChange={(e) => onReason(e.target.value)}
        />
      )}
    </div>
  );
}

function MessageBubble({
  msg,
  currentAdminId,
}: {
  msg: MessageItem;
  currentAdminId: number | null;
}) {
  const isOut = msg.direction === "out";
  const attachments = msg.attachments ?? [];
  const authorLabel =
    isOut && msg.replied_by_admin_name
      ? msg.replied_by_admin_id === currentAdminId
        ? `${msg.replied_by_admin_name} (вы)`
        : msg.replied_by_admin_name
      : null;
  return (
    <div
      style={{
        alignSelf: isOut ? "flex-end" : "flex-start",
        maxWidth: "85%",
        background: isOut ? "var(--brand)" : "var(--ink-50)",
        color: isOut ? "#fff" : "var(--ink-900)",
        padding: "8px 12px",
        borderRadius: 10,
        fontSize: 13,
      }}
    >
      {authorLabel && (
        <div
          style={{
            fontSize: 11.5,
            fontWeight: 700,
            marginBottom: 2,
            opacity: 0.85,
          }}
        >
          {authorLabel}
        </div>
      )}
      {msg.text && <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>}
      {attachments.length > 0 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            marginTop: msg.text ? 6 : 0,
          }}
        >
          {attachments.map((a, i) =>
            isImageMime(a.mime) ? (
              <a
                key={i}
                href={resolveAdminAssetUrl(a.url)}
                target="_blank"
                rel="noopener noreferrer"
              >
                <img
                  src={resolveAdminAssetUrl(a.url)}
                  alt={a.name ?? ""}
                  style={{
                    maxWidth: 220,
                    maxHeight: 220,
                    borderRadius: 8,
                    display: "block",
                  }}
                />
              </a>
            ) : (
              <a
                key={i}
                href={resolveAdminAssetUrl(a.url)}
                download={a.name ?? "file"}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 8px",
                  borderRadius: 6,
                  background: isOut ? "rgba(255,255,255,.18)" : "#fff",
                  color: isOut ? "#fff" : "var(--ink-900)",
                  textDecoration: "none",
                  fontSize: 12,
                }}
              >
                <span className="ico" style={{ width: 14, height: 14 }}>
                  <Icon.Download />
                </span>
                <span>{a.name ?? "файл"}</span>
                {a.size ? (
                  <span style={{ opacity: 0.6 }}> · {formatBytes(a.size)}</span>
                ) : null}
              </a>
            ),
          )}
        </div>
      )}
      <div style={{ fontSize: 10.5, opacity: 0.65, marginTop: 4 }}>
        {formatDateTime(msg.created_at)}
      </div>
    </div>
  );
}
