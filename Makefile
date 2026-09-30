DC := docker compose
DEV_DC := docker compose -f docker-compose.dev.yml

.DEFAULT_GOAL := help

help: ## Показать список целей
	@awk 'BEGIN{FS=":.*##"; printf "\nЦели:\n"} /^[a-zA-Z_-]+:.*?##/{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.env: .env.example ## Создать .env из .env.example, если его ещё нет
	@if [ ! -f .env ]; then cp .env.example .env; echo "→ создан .env из .env.example (подправьте секреты при необходимости)"; fi

init: .env ## Подготовить локальное окружение (.env)

build: .env ## Сборка всех docker-образов
	$(DC) build

up: .env ## Запуск всего стека в фоне
	$(DC) up -d

up-fg: .env ## Запуск всего стека в foreground (логи в консоль)
	$(DC) up

dev-up: .env ## Запуск локального dev-стека
	$(DEV_DC) up -d --build

dev-logs: ## Логи локального dev-стека
	$(DEV_DC) logs -f --tail=200

dev-down: ## Остановка локального dev-стека
	$(DEV_DC) down

down: ## Остановка стека
	$(DC) down

restart: ## Перезапуск (down + up -d)
	$(DC) down
	$(DC) up -d

logs: ## Логи всех сервисов
	$(DC) logs -f --tail=200

logs-backend: ## Логи только backend
	$(DC) logs -f --tail=200 backend

logs-worker: ## Логи только worker
	$(DC) logs -f --tail=200 worker

logs-bot: ## Логи только bot
	$(DC) logs -f --tail=200 bot

ps: ## Статус контейнеров
	$(DC) ps

migrate: ## Применить миграции БД (Alembic)
	$(DC) exec backend alembic upgrade head

makemigration: ## Сгенерировать новую миграцию (m="название")
	$(DC) exec backend alembic revision --autogenerate -m "$(m)"

downgrade: ## Откатить одну миграцию
	$(DC) exec backend alembic downgrade -1

seed: ## Демо-боты, формы, FAQ, тест и синтетическая активность
	$(DC) exec backend python -m app.cli.demo_seed

platform-admin: ## Создать/повысить platform admin: make platform-admin MAX_ID=... FULL_NAME="..."
	@test -n "$(MAX_ID)" || (echo "MAX_ID обязателен" && exit 1)
	@test -n "$(FULL_NAME)" || (echo "FULL_NAME обязателен" && exit 1)
	$(DC) exec backend python -m app.cli.platform_admin --max-user-id "$(MAX_ID)" --full-name "$(FULL_NAME)"

dev-platform-admin: ## То же для docker-compose.dev.yml
	@test -n "$(MAX_ID)" || (echo "MAX_ID обязателен" && exit 1)
	@test -n "$(FULL_NAME)" || (echo "FULL_NAME обязателен" && exit 1)
	$(DEV_DC) exec backend python -m app.cli.platform_admin --max-user-id "$(MAX_ID)" --full-name "$(FULL_NAME)"

bot: ## Перезапустить только бот
	$(DC) up -d --build bot

dev-bot: ## Перезапустить supervisor ботов в локальном dev-стеке
	$(DEV_DC) up -d --build bot

test: ## Запуск тестов бэкенда
	$(DC) exec backend pytest -q

lint: ## Линт (ruff)
	$(DC) exec backend ruff check .

fmt: ## Форматирование (ruff format)
	$(DC) exec backend ruff format .

shell: ## Shell в контейнере backend
	$(DC) exec backend bash

psql: ## psql в контейнере db
	$(DC) exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

redis-cli: ## redis-cli в контейнере redis
	$(DC) exec redis redis-cli

clean: ## Удалить контейнеры И ТОМА (БД, файлы) — нужно подтверждение
	@read -p "Это удалит все данные (БД, файлы, redis). Продолжить? [y/N] " ans && [ "$$ans" = "y" ] || (echo "отмена" && exit 1)
	$(DC) down -v

.PHONY: help init build up up-fg dev-up dev-logs dev-down down restart logs logs-backend logs-worker logs-bot ps \
        migrate makemigration downgrade seed platform-admin dev-platform-admin bot dev-bot test lint fmt shell psql redis-cli clean
