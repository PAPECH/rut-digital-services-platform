# Шпаргалка: добавление capability и воркеров/cron

Основано на реальной структуре `rut_schedule` (самая полная capability на
сегодня: своя БД-модель, внешний provider, admin-editor, bot-view, ночной
cron-синк). Читай вместе с `docs/architecture/guardrails.md` — здесь только
механика "куда класть файлы", инварианты остаются там.

## Что такое capability

Изолированный, тенант-включаемый модуль под
`backend/app/modules/capabilities/<capability_key>/`, со своими
`domain/application/infrastructure/presentation` (та же Clean Architecture,
что и у обычного модуля) плюс `descriptor.py`, который регистрирует её в общем
каталоге. Платформенный админ включает capability на бот, бот-админ
настраивает `config` и решает, где показать `view`.

## 1. Анатомия модуля (шаблон дерева)

```text
backend/app/modules/capabilities/<key>/
├── descriptor.py                 # регистрация: key, views, validate_config, public_config
├── domain/
│   ├── entities.py                # доменные сущности capability
│   └── config.py                  # parse_<key>_config / validate_<key>_config
├── application/
│   ├── ports.py                   # протоколы для внешних систем (напр. ScheduleHierarchyProvider)
│   └── use_cases.py                # use case'ы, независимые от FastAPI/SQLAlchemy
├── infrastructure/
│   ├── models.py                   # SQLAlchemy-модели (+ alembic-миграция)
│   ├── repositories.py             # реализация репозиториев из domain
│   ├── provider.py                 # адаптер к внешней системе (если есть)
│   ├── provider_factory.py         # опционально: выбор provider по settings-флагу
│   └── sync_worker.py              # опционально: cron/фоновая синхронизация
└── presentation/
    ├── schemas.py                  # pydantic-схемы запрос/ответ
    ├── router.py                   # bot-facing эндпоинты (view)
    └── admin_router.py             # опционально: admin-only действия (напр. manual sync)
```

## 2. Добавление новой capability — бэкенд

1. **`descriptor.py`** — минимальный контракт:

   ```python
   from ..domain.entities import CapabilityDescriptor, CapabilityView
   from .domain.config import project_<key>_public_config, validate_<key>_config

   <KEY>_DESCRIPTOR = CapabilityDescriptor(
       key="<key>",
       version="1.0.0",
       name="...",
       description="...",
       admin_editor_key="<key>",       # должен совпасть с ключом в CapabilityEditorRegistry (фронт)
       views=(CapabilityView(key="browse", title="...", subtitle="...", icon="..."),),
       validate_config=validate_<key>_config,
       public_config=project_<key>_public_config,
   )
   ```

2. **Зарегистрировать** в `capabilities/infrastructure/catalog.py`:
   добавить импорт дескриптора и включить его в `CapabilityRegistry((...))`.

3. **`infrastructure/models.py`** — если нужна своя таблица, плюс
   `alembic revision --autogenerate`. Проверить сгенерированный файл руками —
   в проекте уже случались пустые/дублирующиеся миграции от неаккуратного
   `--autogenerate` (см. `20260727_19xx_add_staff_favorites_table*`).

4. **`presentation/router.py`** (bot-facing) и, если нужны admin-only действия
   (ручной sync, тест конфигурации) — **`presentation/admin_router.py`**.
   Подключить оба в `app/api/router.py`:

   ```python
   from ..modules.capabilities.<key>.presentation.router import router as <key>_router
   ...
   api_router.include_router(<key>_router, prefix="/capabilities/<key>", tags=["<key>"])
   ```

   ⚠️ **Ловушка**: универсальный `capabilities/presentation/router.py`
   (install/enable/configure/test-config) на сегодня явно импортирует
   provider каждой capability для эндпоинта "проверить конфигурацию"
   (`admission_rating`, `request_status`, `rut_schedule` — все три прямо
   там). Это не полностью generic слой — если новой capability нужна кнопка
   "проверить подключение" в админке, придётся руками добавить ветку в этом
   общем файле, а не только в своём модуле.

5. Если capability ходит во внешнюю систему и есть/будет несколько
   провайдеров (веб-скрейпер → официальный API, тест vs прод) — заведи
   `provider_factory.py` по образцу `rut_schedule`:

   ```python
   def get_<key>_provider():
       if settings.<KEY>_PROVIDER == "oracle":
           return OracleProvider()
       return DefaultProvider()
   ```

   Один флаг в `settings`, один switch-point — все потребители (в том числе
   cron-воркер) идут через фабрику, а не создают провайдер напрямую.

## 3. Добавление новой capability — admin-фронт

1. Создать редактор конфигурации:
   `frontend-admin/src/features/capability-management/ui/editors/<Key>CapabilityEditor.tsx`.
2. Зарегистрировать в
   `frontend-admin/src/features/capability-management/ui/editors/CapabilityEditorRegistry.tsx`:

   ```tsx
   import { <Key>CapabilityEditor } from "./<Key>CapabilityEditor";
   const capabilityEditorRegistry = {
     ...,
     <key>: <Key>CapabilityEditor,
   };
   ```

   Ключ в реестре обязан совпасть с `admin_editor_key` из дескриптора.

## 4. Добавление новой capability — mini-app (bot-facing) фронт

1. Создать вью: `frontend-miniapp/src/features/capabilities/ui/<Key>CapabilityView.tsx`.
2. Зарегистрировать в
   `frontend-miniapp/src/features/capabilities/ui/CapabilityViewRegistry.tsx`
   под ключом `"<capability_key>:<view_key>"` (например `"rut_schedule:browse"`)
   — составной ключ, не просто `capability_key`.

## 5. Добавление воркера / cron-задачи

Паттерн живёт в `infrastructure/sync_worker.py` внутри самой capability (не
в `app/workers/` напрямую) — держит фоновую логику рядом с доменом, которым
она владеет.

1. **Реализовать 3 функции** (см. `rut_schedule/infrastructure/sync_worker.py`
   как эталон):

   ```python
   async def tick() -> None:
       """Проходит по всем enabled installations этой capability."""
       for installation_id in enabled_installation_ids():
           await sync_installation(installation_id)

   def tick_sync() -> None:
       """APScheduler (BlockingScheduler) зовёт только синхронные джобы."""
       asyncio.run(tick())

   def schedule_jobs(scheduler) -> None:
       scheduler.add_job(
           tick_sync,
           "cron",              # или "interval", если не нужна фиксированная точка времени
           hour=HOUR_UTC, minute=MINUTE_UTC,
           id="<key>_capability_tick",
           max_instances=1,     # не даёт наложиться, если предыдущий прогон завис
           coalesce=True,       # пропущенные тики схлопываются в один, не накапливаются
           # next_run_time НЕ трогать — иначе рестарт контейнера триггерит
           # внеплановый прогон немедленно вместо ожидания следующего окна
       )
   ```

2. **Добавить compatibility-shim** в `app/workers/<key>_monitoring.py`
   (тонкий ре-экспорт, чтобы `run.py` не знал о внутренней структуре модуля):

   ```python
   """Compatibility export for the <key> capability's worker."""
   from ..modules.capabilities.<key>.infrastructure.sync_worker import (
       schedule_jobs, sync_installation, tick, tick_sync,
   )
   __all__ = ["schedule_jobs", "sync_installation", "tick", "tick_sync"]
   ```

3. **Подключить в `app/workers/run.py`**:

   ```python
   from .<key>_monitoring import schedule_jobs as schedule_<key>
   ...
   def main() -> None:
       ...
       schedule_<key>(scheduler)
   ```

   Ничего в `docker-compose*.yml` менять не нужно — один `worker`-контейнер
   крутит все зарегистрированные джобы через один `BlockingScheduler`.

### Гигиена cron-задач (из инцидентов в этом проекте)

- **Если данные общие для всех тенантов** (как календарь `rut_schedule`, не
  привязанный к `bot_instance_id`) — бери Redis-лок
  (`redis_client.set(key, "1", nx=True, ex=TTL)`) перед реальной работой,
  чтобы N тиков от N enabled-инсталляций не долбили внешний источник N раз
  параллельно.
- Пиши `last_health_status` / `last_health_at` / `last_health_error_code` на
  `CapabilityInstallationRecord` при успехе и при ошибке — это то, что видит
  админ в панели, без этого сбой невидим снаружи логов.
- Если источник данных сам по себе ограничен по времени доступа (как
  `miit.ru`, доступен только ночью) — фиксированный `cron` час/минута, не
  `interval`; иначе рестарт контейнера посреди дня уйдёт во внешний источник
  в неподходящее время.
- Инвалидируй кэш (`RedisScheduleTreeCache().invalidate()` — тот же паттерн
  для любого читающего кэша) **после** commit, не до — иначе конкурентный
  читатель успеет пересобрать кэш из ещё не закоммиченных старых данных.

## TL;DR-чеклист для новой capability

- [ ] `domain/` + `application/` + `infrastructure/` + `presentation/` по шаблону
- [ ] `descriptor.py` → зарегистрирован в `infrastructure/catalog.py`
- [ ] Роутер(ы) подключены в `app/api/router.py`
- [ ] Миграция для новых таблиц (проверена руками, не просто `--autogenerate`)
- [ ] Editor зарегистрирован в admin `CapabilityEditorRegistry.tsx` под `admin_editor_key`
- [ ] View зарегистрирован в miniapp `CapabilityViewRegistry.tsx` под `"<key>:<view_key>"`
- [ ] Если нужна проверка конфигурации из админки — добавлена ветка в общем `capabilities/presentation/router.py`
- [ ] Если нужен провайдер с внешним переключением (тест/прод, старый/новый источник) — `provider_factory.py` + флаг в `settings`
- [ ] Если нужен фон/cron — `infrastructure/sync_worker.py` + shim в `app/workers/` + вызов в `app/workers/run.py::main()`
- [ ] Тесты на cross-tenant denial, если capability трогает тенант-данные (см. `AGENTS.md`)
