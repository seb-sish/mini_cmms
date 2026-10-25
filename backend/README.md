# Mini-CMMS Backend
FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL + Redis + ARQ

## Первый запуск и инициализация (First Run)

### 1. Применение миграций базы данных
```bash
uv run alembic upgrade head
```

### 2. Создание первой учётной записи администратора (Bootstrap Admin)
Создание первого администратора выполняется осознанной отдельной CLI-командой. Пароль не передаётся аргументом командной строки и не логируется.

Вариант с переменной окружения:
```bash
SECURITY_FIRST_ADMIN_PASSWORD="StrongAdminPassword123!" uv run python -m app.cli bootstrap-admin --login admin
```

Вариант с передачей через stdin:
```bash
echo "StrongAdminPassword123!" | uv run python -m app.cli bootstrap-admin --login admin --password-stdin
```

Вариант с интерактивным скрытым вводом:
```bash
uv run python -m app.cli bootstrap-admin --login admin
```

- Команда защищена advisory lock в PostgreSQL от конкурентных запусков.
- Если в системе уже существует активный администратор, повторный запуск является no-op и не перезаписывает пароль или права.
- Попытка выполнить bootstrap с логином пользователя другой роли или заблокированного пользователя отклоняется с ошибкой.

### 3. Запуск сервисов
Запуск API:
```bash
uv run uvicorn app.__main__:app --host 0.0.0.0 --port 8000
```

Запуск фонового воркера ARQ:
```bash
uv run arq app.worker.main.WorkerSettings
```

### 4. Вход и проверка готовности
Вход администратора:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "StrongAdminPassword123!"}'
```

Проверка работоспособности:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Запуск через Docker Compose

Для запуска производственного/демо стека:
```bash
cp .env.example .env   # заполнить секреты и при необходимости изменить настройки
docker compose --env-file .env up -d
```
Файл `.env` из корня репозитория — источник конфигурации развёртывания: compose
подставляет из него значения в контейнеры API, миграций и воркера
(`APP_COMPANY_TIMEZONE`, `APP_CORS_ORIGINS`, `SECURITY_*`, реквизиты PostgreSQL).
`.env.example` используется как запасной набор значений по умолчанию.

Хранилища PostgreSQL и Redis изолированы внутри внутренней сети Docker Compose и не публикуют порты наружу. Для локального запуска тестов с хоста используется изолированный тестовый стек `compose.test.yml` (порты 5433 и 6380).
