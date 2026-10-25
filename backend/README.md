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
