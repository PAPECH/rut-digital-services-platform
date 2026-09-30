import type {
  BottomNavigationItem,
  BotSettings,
  ProfileFieldDefinition,
} from "@/api/types";
import { isShortcutCategory, type AdminContentCategory } from "@/entities/content/model/types";
import { ContentIconPicker } from "@/entities/content/ui/ContentIconPicker";

const EMPTY_ITEM: BottomNavigationItem = {
  target: "category",
  category_slug: null,
  label: "",
  icon: "folder",
};

const SYSTEM_TARGETS = [
  {
    value: "system:submission_history",
    target: "submission_history" as const,
    label: "История заявок",
    icon: "document" as const,
  },
  {
    value: "system:form_catalog",
    target: "form_catalog" as const,
    label: "Доступные формы",
    icon: "folder" as const,
  },
];

function selectedTarget(item: BottomNavigationItem): string {
  const target = item.target ?? "category";
  return target === "category"
    ? item.category_slug
      ? `category:${item.category_slug}`
      : ""
    : `system:${target}`;
}

export function BottomNavigationEditor({
  settings,
  categories,
  profileSchema,
  onChange,
}: {
  settings: BotSettings;
  categories: AdminContentCategory[];
  profileSchema: ProfileFieldDefinition[];
  onChange: (settings: BotSettings) => void;
}) {
  // A capability shortcut has no content page of its own (see docs/tasks/044) -- navigating
  // straight to its slug is a defined failure state, not a usable bottom-nav destination, so it
  // never appears as an option here.
  const navigableCategories = categories.filter((category) => !isShortcutCategory(category));
  const items = settings.bottom_navigation.custom_items;
  const setItems = (custom_items: BottomNavigationItem[]) =>
    onChange({ ...settings, bottom_navigation: { custom_items } });
  const setItem = (index: number, patch: Partial<BottomNavigationItem>) =>
    setItems(items.map((item, current) => current === index ? { ...item, ...patch } : item));

  const profileEnabled = settings.profile.enabled;
  // Client-side mirror of the backend's bidirectional check (Task 054) — required fields
  // are known here without a new fetch, so the toggle can explain itself before a submit
  // round-trip; a capability blocking the same toggle is only caught server-side (no
  // capability in this deployment currently sets requires_complete_profile, and fetching
  // installations here would be a bigger change than this editor needs today).
  const requiredFieldKeys = profileSchema.filter((field) => field.required).map((field) => field.key);
  const toggleLocked = profileEnabled && requiredFieldKeys.length > 0;
  const setProfileEnabled = (enabled: boolean) => onChange({ ...settings, profile: { enabled } });

  return (
    <section className="bottom-navigation-editor">
      <div className="profile-schema-editor__head">
        <div>
          <span className="field-label">Нижнее меню мини-приложения</span>
          <p className="profile-schema-editor__hint">
            «Главная» закреплена. Между ней и «Профилем» можно добавить до двух опубликованных экранов.
          </p>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          type="button"
          disabled={items.length >= 2}
          onClick={() => setItems([...items, { ...EMPTY_ITEM }])}
        >
          Добавить экран
        </button>
      </div>
      <div className="bottom-navigation-fixed-preview" aria-label="Постоянные пункты меню">
        <span>Главная</span>
        <span>Настраиваемые экраны</span>
        <label
          style={{ display: "flex", alignItems: "center", gap: 6 }}
          title={
            toggleLocked
              ? `Нельзя отключить: обязательные поля анкеты — ${requiredFieldKeys.join(", ")}`
              : undefined
          }
        >
          <input
            type="checkbox"
            checked={profileEnabled}
            disabled={toggleLocked}
            onChange={(event) => setProfileEnabled(event.target.checked)}
          />
          Профиль
        </label>
      </div>
      {toggleLocked && (
        <p className="profile-schema-editor__hint" style={{ color: "var(--st-rej-fg)" }}>
          Чтобы отключить вкладку «Профиль», сначала снимите отметку «обязательное» со всех
          полей анкеты: {requiredFieldKeys.join(", ")}.
        </p>
      )}
      {items.map((item, index) => (
        <div className="bottom-navigation-row" key={index}>
          <select
            className="select"
            value={selectedTarget(item)}
            required
            onChange={(event) => {
              const systemTarget = SYSTEM_TARGETS.find(
                (candidate) => candidate.value === event.target.value,
              );
              if (systemTarget) {
                setItem(index, {
                  target: systemTarget.target,
                  category_slug: null,
                  label: systemTarget.label,
                  icon: systemTarget.icon,
                });
                return;
              }
              const slug = event.target.value.replace(/^category:/, "");
              const category = navigableCategories.find((candidate) => candidate.slug === slug);
              setItem(index, {
                target: "category",
                category_slug: slug || null,
                label: category?.draft?.title.slice(0, 24) ?? "",
                icon: category?.icon ?? "folder",
              });
            }}
          >
            <option value="">Выберите экран</option>
            <optgroup label="Системные экраны">
              {SYSTEM_TARGETS.map((target) => (
                <option value={target.value} key={target.value}>{target.label}</option>
              ))}
            </optgroup>
            <optgroup label="Контентные категории">
            {navigableCategories.map((category) => (
              <option value={`category:${category.slug}`} key={category.id}>{category.draft?.title ?? category.slug}</option>
            ))}
            </optgroup>
          </select>
          <input
            className="input"
            value={item.label}
            maxLength={24}
            placeholder="Подпись в меню"
            onChange={(event) => setItem(index, { label: event.target.value })}
          />
          <ContentIconPicker
            value={item.icon}
            onChange={(icon) => setItem(index, { icon })}
          />
          <div className="content-inline-actions">
            <button className="btn btn-ghost btn-sm" type="button" disabled={index === 0} onClick={() => {
              const next = [...items];
              [next[index - 1], next[index]] = [next[index], next[index - 1]];
              setItems(next);
            }}>↑</button>
            <button className="btn btn-ghost btn-sm" type="button" disabled={index === items.length - 1} onClick={() => {
              const next = [...items];
              [next[index], next[index + 1]] = [next[index + 1], next[index]];
              setItems(next);
            }}>↓</button>
            <button className="btn btn-danger btn-sm" type="button" onClick={() => setItems(items.filter((_, current) => current !== index))}>
              Удалить
            </button>
          </div>
        </div>
      ))}
      {!navigableCategories.length ? <p className="muted">Контентных экранов пока нет, но системные экраны уже доступны.</p> : null}
    </section>
  );
}
