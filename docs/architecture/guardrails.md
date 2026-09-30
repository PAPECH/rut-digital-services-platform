# Architecture guardrails

## Platform shape

Use a modular monolith with one backend, admin application, mini-application, PostgreSQL database, Redis, file-storage port, and multiple MAX adapter processes built from one image. Treat each bot as a `BotInstance` tenant.

## Backend boundaries

Organize business modules under `backend/app/modules/<module>`:

```text
domain/          entities, value objects, policies, repository protocols
application/     commands, queries, DTOs, ports, use cases
infrastructure/  SQLAlchemy repositories, external providers, workers
presentation/    FastAPI routers and request/response schemas
```

Allowed dependency direction:

```text
presentation -> application -> domain
infrastructure -> application/domain
domain -> Python standard library only
```

Shared technical code belongs under `backend/app/shared`; shared business behavior does not.

## Tenant model

- A global identity is `(provider, external_user_id)`; for MAX the external ID comes only from validated init data.
- `BotMembership` links the global identity to one bot and owns bot-local bans, preferences, and custom fields.
- Tenant-owned entities include `bot_instance_id` or are reachable only through a tenant-owned aggregate with enforced repository scoping.
- A request header may select a bot before login, but the issued principal must bind the resolved bot ID. Never authorize from the header alone.
- Platform administrators may cross tenants explicitly; all other roles require current access from storage.

## Shared profile

Access shared profile information through an application port. Keep common attributes, organization attributes, provenance, verification, and bot-local fields distinct. Store a profile snapshot with a submitted form. The future RUT directory adapter remains backlog.

## Content and forms

Use typed block definitions and a registry. Keep draft and immutable published versions separate. A submission references a published form version, not a mutable template.

## Capabilities

Install capability code through deployment. Platform admins enable it per bot; bot admins configure allowed settings and place its registered view. Never execute uploaded JavaScript.

## Maintenance

Support informational, read-only, and full-stop modes globally and per bot. Enforce blocked operations server-side. Keep health, manifest, admin authentication/refresh, logout, and maintenance controls available.

## Analytics

Collect stable, idempotent events asynchronously. Include tenant, internal user ID, session, entity/version IDs, and safe metadata. Exclude names, MAX IDs, contact data, search input, profile attributes, and form values. Cross-bot usage is aggregate-only.

## Authentication

Use short-lived admin access tokens and rotating refresh sessions. Keep refresh tokens in Secure HttpOnly cookies and store only their hashes. Detect reuse, revoke token families, and re-check current permissions for sensitive actions.

## Module and file isolation

Split by logical concern, not by convenience: one component or module per file, and each keeps its own files together in one place (markup, state, types, styles) rather than scattering them into shared dumps. Never grow a "god file" that mixes multiple unrelated responsibilities — extract a new file instead. Apply this at every layer — backend modules (within the `domain/application/infrastructure/presentation` split above), frontend components, and any other feature work.

## Frontend boundaries

Use `app/pages/widgets/features/entities/shared`. Pages compose; features act; entities model; shared contains framework-agnostic UI and utilities. Each block/capability has separate view and editor components. Author styles in `.ts` files colocated with their component, not in a global stylesheet or scattered inline `style` objects. Keep a component's types with the component or its owning feature/entity, not in a shared cross-domain types dump.

## Responsive admin

At mobile widths, preserve dashboard, bot switching, submissions, users, maintenance controls, notifications, and safe quick actions. Convert wide tables to cards or horizontally constrained views. Complex content/form builders are desktop-first but must provide readable preview, limited field edits, and a clear message for unavailable drag-and-drop operations.

## Admin guide

When admin functionality described in «Инструкции» (`/guide`) changes, update the matching guide
tab in the same change and set its «Актуально на» date. A new admin section that gets a guide tab
follows the same rule.

## Minimize manual entry

Never make an admin type a value that already exists as data elsewhere in the system — derive it, suggest it, or offer it as a pick/insert action instead of free text. Applied examples: a slug auto-fills from its name field and stays editable (`shared/lib/slugify.ts`) rather than being typed from scratch; an editor for text that references other entities' keys (result scales, questions, capabilities, placeholders) offers click-to-insert options for those keys instead of requiring the admin to recall and hand-type their syntax. Free-text entry is for genuinely new content the system has no prior knowledge of, never for values that already exist as data.
