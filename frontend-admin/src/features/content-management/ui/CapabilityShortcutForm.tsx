import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import type { ContentIconName } from "@/entities/content/model/contentIcons";
import type {
  AdminContentCategory,
  ContentCategoryCreate,
  ContentShortcutCardPatch,
} from "@/entities/content/model/types";
import { ContentIconPicker } from "@/entities/content/ui/ContentIconPicker";
import { FilePickerModal } from "@/features/content-files/ui/FilePickerModal";
import { availableNewCategoryParents } from "@/features/content-management/model/categoryTree";
import { useContentEditorResources } from "@/features/content-management/model/ContentEditorResourcesContext";
import { slugify } from "@/shared/lib/slugify";

// Same narrow, ad-hoc manifest shape `CapabilityActionBlockEditor` declares for itself --
// matches this codebase's existing convention (see that file) rather than a shared type.
interface PublicCapability {
  key: string;
  views: Array<{ key: string; title: string }>;
}

interface Manifest {
  capabilities: PublicCapability[];
}

type CapabilityShortcutFormProps =
  | {
      mode: "create";
      order: number;
      categories: AdminContentCategory[];
      initialParentId: number | null;
      onCreate: (payload: ContentCategoryCreate) => Promise<unknown>;
      onCancel: () => void;
    }
  | {
      mode: "edit";
      category: AdminContentCategory;
      onSave: (categoryId: number, payload: ContentShortcutCardPatch) => Promise<unknown>;
      onCancel: () => void;
    };

export function CapabilityShortcutForm(props: CapabilityShortcutFormProps) {
  const editing = props.mode === "edit" ? props.category : null;

  const [capabilities, setCapabilities] = useState<PublicCapability[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    api
      .get<Manifest>("/manifest")
      .then((result) => {
        if (active) setCapabilities(result.capabilities || []);
      })
      .catch(() => {
        if (active) setLoadError("Не удалось загрузить включённые возможности");
      });
    return () => {
      active = false;
    };
  }, []);

  const [capabilityKey, setCapabilityKey] = useState(editing?.capability_key ?? "");
  const [viewKey, setViewKey] = useState(editing?.capability_view_key ?? "");
  const [title, setTitle] = useState(editing?.title ?? "");
  const [subtitle, setSubtitle] = useState(editing?.subtitle ?? "");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [icon, setIcon] = useState<ContentIconName>(editing?.icon ?? "calendar");
  const [imageUrl, setImageUrl] = useState<string | null>(editing?.image_url ?? null);
  const [parentId, setParentId] = useState<number | null>(
    props.mode === "create" ? props.initialParentId : null,
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const { registerAttachment } = useContentEditorResources();

  const views = useMemo(
    () => capabilities.find((item) => item.key === capabilityKey)?.views || [],
    [capabilityKey, capabilities],
  );

  const selectCapability = (key: string) => {
    const firstView = capabilities.find((item) => item.key === key)?.views[0];
    setCapabilityKey(key);
    setViewKey(firstView?.key ?? "");
    if (!title) setTitle(firstView?.title ?? "");
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (props.mode === "create") {
        await props.onCreate({
          title,
          slug,
          parent_id: parentId,
          icon,
          subtitle: subtitle || null,
          language: "ru",
          order: props.order,
          capability_key: capabilityKey,
          capability_view_key: viewKey,
          image_url: imageUrl,
        });
      } else {
        await props.onSave(props.category.id, {
          icon,
          title,
          subtitle: subtitle || null,
          image_url: imageUrl,
        });
      }
      props.onCancel();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Не удалось сохранить ссылку на возможность",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="card content-create-card" onSubmit={(event) => void submit(event)}>
      <div className="card-head">
        <div>
          <h2 className="card-title">
            {props.mode === "create" ? "Ссылка на возможность" : "Ссылка на возможность · редактирование"}
          </h2>
          <p className="card-sub">
            Плитка выглядит как обычная категория, но открывает экран установленной возможности.
          </p>
        </div>
      </div>
      <div className="card-body content-create-form">
        <label>
          <span className="field-label">Возможность</span>
          <select
            className="select"
            required
            disabled={props.mode === "edit"}
            value={capabilityKey}
            onChange={(event) => selectCapability(event.target.value)}
          >
            <option value="" disabled>
              Выберите возможность
            </option>
            {!capabilities.some((item) => item.key === capabilityKey) && capabilityKey ? (
              <option value={capabilityKey}>{capabilityKey} (не установлена)</option>
            ) : null}
            {capabilities.map((capability) => (
              <option key={capability.key} value={capability.key}>
                {capability.key}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Экран</span>
          <select
            className="select"
            required
            disabled={props.mode === "edit"}
            value={viewKey}
            onChange={(event) => setViewKey(event.target.value)}
          >
            <option value="" disabled>
              Выберите экран
            </option>
            {!views.some((view) => view.key === viewKey) && viewKey ? (
              <option value={viewKey}>{viewKey}</option>
            ) : null}
            {views.map((view) => (
              <option key={view.key} value={view.key}>
                {view.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="field-label">Название плитки</span>
          <input
            required
            maxLength={300}
            className="input"
            value={title}
            onChange={(event) => {
              const value = event.target.value;
              setTitle(value);
              if (props.mode === "create" && !slugTouched) setSlug(slugify(value));
            }}
          />
        </label>
        {props.mode === "create" ? (
          <label>
            <span className="field-label">Адрес (slug)</span>
            <input
              required
              minLength={2}
              maxLength={80}
              pattern="[a-z0-9](?:[a-z0-9_]|-){1,79}"
              className="input"
              value={slug}
              onChange={(event) => {
                setSlugTouched(true);
                setSlug(event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""));
              }}
              placeholder="my-schedule"
            />
          </label>
        ) : null}
        <label>
          <span className="field-label">Иконка</span>
          <ContentIconPicker value={icon} onChange={setIcon} />
        </label>
        <label className="content-editor-wide">
          <span className="field-label">Подзаголовок</span>
          <textarea
            className="textarea"
            rows={2}
            maxLength={2000}
            value={subtitle}
            onChange={(event) => setSubtitle(event.target.value)}
          />
        </label>
        <div className="content-editor-wide">
          <span className="field-label">Изображение плитки</span>
          {imageUrl ? (
            <div className="content-file-preview">
              <img src={imageUrl} alt={title} height="76px" width="76px" className="content-file-preview-image" />
            </div>
          ) : null}
          <div className="content-file-controls">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setPickerOpen(true)}>
              {imageUrl ? "Заменить изображение" : "Выбрать изображение"}
            </button>
            {imageUrl ? (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setImageUrl(null)}>
                Убрать
              </button>
            ) : null}
          </div>
          {pickerOpen ? (
            <FilePickerModal
              title="Изображение плитки"
              imageOnly
              uploadPurpose="category_icon"
              onUploaded={registerAttachment}
              onPick={(attachment) => setImageUrl(attachment.url)}
              onClose={() => setPickerOpen(false)}
            />
          ) : null}
        </div>
        {props.mode === "create" ? (
          <label className="content-editor-wide">
            <span className="field-label">Родительская категория</span>
            <select
              className="select"
              value={parentId ?? ""}
              onChange={(event) => setParentId(event.target.value ? Number(event.target.value) : null)}
            >
              <option value="">Корневая категория</option>
              {availableNewCategoryParents(props.categories).map((category) => (
                <option value={category.id} key={category.id}>
                  {category.draft?.title ?? category.slug}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {loadError ? <p className="form-error content-editor-wide">{loadError}</p> : null}
        {error ? <p className="form-error content-editor-wide">{error}</p> : null}
        <div className="content-form-actions content-editor-wide">
          <button type="button" className="btn btn-ghost" onClick={props.onCancel}>
            Отмена
          </button>
          <button disabled={submitting || !capabilityKey || !viewKey} className="btn btn-primary" type="submit">
            {submitting ? "Сохранение…" : props.mode === "create" ? "Создать" : "Сохранить"}
          </button>
        </div>
      </div>
    </form>
  );
}
