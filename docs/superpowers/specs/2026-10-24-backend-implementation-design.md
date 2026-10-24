# Дизайн реализации бэкенда Mini-CMMS

**Дата:** 2026-10-24  
**Статус:** Согласован к планированию  
**Контракт:** [OpenAPI 3.1.1](../../Mini_CMMS_OpenAPI_3.1.1.yaml), [Реестр решений и инвариантов](../../Mini_CMMS_API_Design_Notes.md), [Инструкция приёмки](../../Mini_CMMS_API_Acceptance.md)

---

## 1. Контекст и цели (Intent and Why)
Проект **Mini-CMMS** представляет собой минималистичную систему управления техническим обслуживанием и ремонтами оборудования (CMMS / ТОиР) на промышленном предприятии. 
Цель настоящей разработки — создать надежный, производительный и строго соответствующий нормативному контракту OpenAPI 3.1.1 серверный бэкенд на Python. 

Система обслуживает 4 категории пользователей:
- **Администратор (ADMIN):** управление пользователями, ролями и учетными записями.
- **Инженер (ENGINEER):** управление парком оборудования, регламентами ТО, распределение и закрытие нарядов/заявок.
- **Техник (TECHNICIAN):** исполнение нарядов на ТО и ремонт, прохождение чек-листов, фиксация результатов работ.
- **Оператор (OPERATOR):** фиксация неисправностей (инцидентов) на оборудовании и создание заявок на ремонт.

---

## 2. Цели, не-цели и анти-цели (Goals, Non-Goals, Anti-Goals)

### Цели (Goals):
1. **100% соответствие согласованному контракту API 1.0.0**: реализация всех 31 эндпоинтов (41 HTTP-операции) в префиксе `/api/v1` и системных `/health`, `/ready`.
2. **Точная валидация и форматы ошибок**: реализация RFC 9457 `ProblemDetail` (`application/problem+json`) с точными статус-кодами и машиночитаемыми кодами `code` (например, `VALIDATION_ERROR`, `VERSION_CONFLICT`, `PRECONDITION_REQUIRED`, `TOO_EARLY_TO_COMPLETE` и т.д.).
3. **Безопасность и сессии**: непрозрачные (opaque) bearer-токены со сроком жизни 12 часов, сохраняемые в виде безопасных хешей в БД, хеширование паролей алгоритмом Argon2, скользящий Rate Limiter на попытки входа (5 неудачных за 10 минут на IP или lowercase(login) $\to$ HTTP 429 с `Retry-After`).
4. **Конкурентная целостность (Optimistic Concurrency Control)**: ETag и заголовок `If-Match` формата `"<uuid>:<version>"` для всех сущностей с версией (`version >= 1`), атомарное инкрементирование версий и защита от состояния гонки.
5. **Фоновая обработка регламентов**: периодический воркер на базе Redis + ARQ, формирующий внутрисистемные уведомления о плановом ТО (окна T−3..T−1 и T) с гарантией идемпотентности.
6. **Полная контейнеризация**: запуск всех сервисов (FastAPI приложение, PostgreSQL, Redis, ARQ worker, автоматические миграции Alembic) через единый `docker-compose.yml` в корне репозитория.

### Не-цели (Non-Goals):
1. Разработка пользовательского интерфейса (фронтенд разрабатывается отдельным специалистом).
2. Реализация функционала за пределами MVP: публичная регистрация, SSO, OAuth2/OIDC, refresh-токены, экспорт/импорт в Excel/PDF, отправка email/Telegram, файловое хранилище S3, QR-коды.

### Анти-цели (Anti-Goals):
1. Использование слабо типизированных JSON или вольностей в DTO (любое отклонение от OpenAPI 3.1.1 считается дефектом).
2. Применение JWT вместо opaque bearer токенов (нарушает требование мгновенного отзыва сессий при логауте и блокировке).
3. "Last write wins" при конкурентном редактировании: запрещено обновлять сущность без валидации версии через `If-Match`.

---

## 3. Ограничения (Constraints)
1. **Платформа и стек**: Python 3.13, менеджер пакетов `uv`, фреймворк FastAPI, база данных PostgreSQL 16+, ORM SQLAlchemy 2.0 (асинхронный драйвер `asyncpg`), миграции Alembic, Redis 7+ и планировщик ARQ.
2. **Стандарты дат и времени**:
   - Формат дат: строго `YYYY-MM-DD`.
   - Временные метки в API: строго UTC RFC3339 с суффиксом `Z` (`YYYY-MM-DDTHH:MM:SSZ` или с микросекундами).
   - Локальные календарные вычисления (например, определение `local_today` для проверок сроков ТО и создания нарядов): берутся с учетом системной таймзоны предприятия (`company_timezone`, по умолчанию `Europe/Moscow`).
3. **Обработка строк**:
   - Деловые строки триммируются от внешних пробелов перед сохранением и проверкой уникальности.
   - Поле login валидируется регистронезависимо (`lower(login)` уникален).
   - В обязательном порядке запрещены строки, состоящие только из пробелов (возврат 422).
4. **Структура репозитория**:
   - `compose.yml` и корневой `.env.example` находятся в корне `/root/projects/mini_cmms/`.
   - Исходный код бэкенда, его `pyproject.toml`, Dockerfile и тесты изолированы в `/root/projects/mini_cmms/backend/`.

---

## 4. Варианты подходов (Approaches)

### Рассмотренные варианты:
1. **Подход 1: Вертикальные доменные срезы (Выбранный)**
   Реализация шаг за шагом изолированных вертикальных доменов (Core/Infra $\to$ Auth & Users $\to$ Equipment & Faults $\to$ Plans & Schedules $\to$ Work Orders $\to$ ARQ & Notifications $\to$ E2E Validation).  
   *Почему выбран:* Обеспечивает непрерывную проверяемость, раннее обнаружение несоответствий контракту, строгий TDD-цикл, чистоту миграций БД и изоляцию бизнес-логики.
2. **Подход 2: Горизонтальные слои («Все таблицы $\to$ Все CRUD $\to$ Все роуты»)**  
   *Почему отклонен:* Создает гигантские диффы, откладывает первую сквозную проверку на самый конец, затрудняет локализацию регрессий.
3. **Подход 3: Автоматическая кодогенерация DTO из OpenAPI**  
   *Почему отклонен:* Генераторы кода некорректно обрабатывают расширенные конструкции JSON Schema Draft 2020-12 (такие как `const`, условные схемы `if/then/else`, `type: 'null'`) и требуют большого объема ручных правок, ломая идиоматичную структуру.

---

## 5. Архитектура и структура проекта

### 5.1. Референс и структура директорий
В качестве архитектурного стандарта используется паттерн проекта `/root/projects/main-fastapi`:

```
mini_cmms/
├── compose.yml                # Сервисы: postgres, redis, backend, arq-worker, migrate
├── .env.example
├── .gitignore
├── docs/                      # Нормативные спецификации и тесты
└── backend/
    ├── pyproject.toml         # Зависимости uv (Python >= 3.13)
    ├── uv.lock
    ├── Dockerfile
    ├── README.md
    ├── app/
    │   ├── __init__.py
    │   ├── __main__.py        # Запуск uvicorn, фабрика FastAPI, CORS, middleware
    │   ├── config/
    │   │   ├── __init__.py
    │   │   └── config.py      # Pydantic Settings (App, DB, Redis, Security, Logging)
    │   ├── logger/
    │   │   ├── __init__.py
    │   │   └── middleware.py  # Structured Request/Response logging
    │   ├── errors/
    │   │   ├── __init__.py
    │   │   ├── exceptions.py  # Доменные исключения (AppException)
    │   │   └── handlers.py    # Преобразование в RFC 9457 ProblemDetail
    │   ├── db/
    │   │   ├── __init__.py
    │   │   ├── session.py     # SQLAlchemy 2.0 asyncpg engine & sessionmaker
    │   │   ├── base.py        # DeclarativeBase, TimestampMixin, VersionMixin
    │   │   ├── models/        # SQLAlchemy модели
    │   │   │   ├── user.py
    │   │   │   ├── session.py
    │   │   │   ├── equipment.py
    │   │   │   ├── fault.py
    │   │   │   ├── maintenance_plan.py
    │   │   │   ├── maintenance_schedule.py
    │   │   │   ├── work_order.py
    │   │   │   ├── work_order_event.py
    │   │   │   ├── work_history.py
    │   │   │   └── notification.py
    │   │   └── alembic/
    │   │       ├── alembic.ini
    │   │       ├── env.py
    │   │       └── versions/
    │   ├── schemas/           # Pydantic v2 DTO
    │   │   ├── common.py      # Pagination, ProblemDetail, Enums
    │   │   ├── auth.py
    │   │   ├── user.py
    │   │   ├── equipment.py
    │   │   ├── fault.py
    │   │   ├── maintenance.py
    │   │   ├── work_order.py
    │   │   └── notification.py
    │   ├── core/              # Бизнес-сервисы и безопасность
    │   │   ├── security.py    # Argon2, Opaque Token generation & hashing
    │   │   ├── rate_limiter.py# Redis sliding window rate limiting
    │   │   └── permissions.py # FastAPI Depends: роли и видимость объектов
    │   ├── services/          # Сервисный слой доменной логики
    │   │   ├── auth_service.py
    │   │   ├── user_service.py
    │   │   ├── equipment_service.py
    │   │   ├── fault_service.py
    │   │   ├── maintenance_service.py
    │   │   ├── work_order_service.py
    │   │   └── notification_service.py
    │   ├── worker/            # ARQ background worker
    │   │   ├── __init__.py
    │   │   ├── main.py        # ARQ WorkerSettings, cron jobs, lifespan
    │   │   └── tasks.py       # Периодический чек регламентов и генерация нотификаций
    │   └── api/
    │       ├── __init__.py
    │       ├── dependencies.py# DB session, Current User, RateLimit dependencies
    │       └── v1/
    │           ├── __init__.py
    │           ├── router.py  # Агрегатор роутов v1
    │           ├── auth.py
    │           ├── users.py
    │           ├── equipment.py
    │           ├── faults.py
    │           ├── maintenance_plans.py
    │           ├── maintenance_schedules.py
    │           ├── work_orders.py
    │           ├── work_history.py
    │           ├── notifications.py
    │           └── system.py  # /health, /ready
    └── tests/
        ├── conftest.py
        ├── test_health.py
        ├── test_auth.py
        ├── test_users.py
        ├── test_equipment.py
        ├── test_faults.py
        ├── test_maintenance.py
        ├── test_work_orders.py
        ├── test_notifications.py
        └── test_concurrency.py

```

---

## 6. Ключевые архитектурные и доменные решения

### 6.1. Аутентификация и Rate Limiting
- **Хранение паролей:** библиотека `argon2-cffi`. Пароли не логируются.
- **Токены:** криптографически стойкие случайные строки (`secrets.token_urlsafe(32)`), в базе хранится только `sha256(token)`. Срок действия — строго 12 часов.
- **Отзыв токенов:**
  - `POST /api/v1/auth/logout` аннулирует текущий токен (удаление или `revoked_at`).
  - Блокировка пользователя (`status=BLOCKED`) или смена пароля аннулирует все активные сессии пользователя. Разблокировка старые сессии не восстанавливает.
- **Ограничение частоты запросов (Rate Limiting):**
  - Подсчет в Redis (структура `Sorted Set` / скользящее окно 10 минут).
  - Учитываются только неудачные попытки входа (`401 INVALID_CREDENTIALS`).
  - Ключ лимитера: IP-клиента и `lower(login)`.
  - Превышение порога (более 5 ошибок за 10 мин): ответ `429 TOO_MANY_REQUESTS` с заголовком `Retry-After: <seconds>`.

### 6.2. Версионирование и оптимистичные блокировки
- Сущности `User`, `Equipment`, `Fault`, `MaintenancePlan`, `WorkOrder` содержат целочисленное поле `version >= 1`.
- При `GET` отдается заголовок `ETag: "<uuid>:<version>"`.
- При `PATCH` обязателен заголовок `If-Match`:
  - Отсутствует $\to$ `428 PRECONDITION_REQUIRED`.
  - Не совпадает с текущей версией в БД $\to$ `412 VERSION_CONFLICT`.
  - Неверный формат $\to$ `422 VALIDATION_ERROR`.
- Обновление версий выполняется атомарно внутри транзакции через `UPDATE ... WHERE id = :id AND version = :expected_version RETURNING ...`.

### 6.3. Ролевая модель и матрица доступа
- Реализуется в виде FastAPI Dependencies (`require_role(...)`, `check_object_visibility(...)`).
- При попытке доступа без токена: `401` с заголовком `WWW-Authenticate: Bearer`.
- При несовпадении роли: `403 FORBIDDEN`.
- Если объект скрыт от роли согласно матрице видимости: `404 NOT_FOUND` (для предотвращения утечки информации о существовании чужих записей).
- Защита последнего активного администратора: невозможно удалить, заблокировать или сменить роль у единственного пользователя со статусом `ADMIN + ACTIVE`.

### 6.4. Жизненный цикл заявок (Work Orders FSM)
- Типы заявок: `REPAIR` (по неисправности или без) и `PLANNED` (строго по регламентному графику ТО).
- Переходы статусов:
  - `CREATED` $\to$ `ASSIGNED` (команда `assign`, роль ENGINEER)
  - `ASSIGNED` / `IN_PROGRESS` $\to$ `ASSIGNED` / `IN_PROGRESS` (команда `reassign`, смена техника, статус сохраняется)
  - `ASSIGNED` $\to$ `IN_PROGRESS` (команда `start`, назначенный техник)
  - `IN_PROGRESS` $\to$ `COMPLETED` (команда `complete`, результат работы, проверка обязательных пунктов чек-листа, проверка допустимого срока `completed_at + interval_days > planned_due_on`)
  - `COMPLETED` $\to$ `CLOSED` (команда `close`, инженер; атомарно создает запись `WorkHistory`, обновляет `Fault` в `RESOLVED` или пересчитывает даты в `MaintenanceSchedule`)
  - `CREATED` / `ASSIGNED` $\to$ `CANCELLED` (команда `cancel`, инженер, указание причины отмены).

### 6.5. Фоновый воркер ARQ и уведомления
- Периодическая задача `check_maintenance_notifications` запускается каждый час (или по cron расписанию).
- Определяет текущую дату `local_today` в `company_timezone`.
- Для всех активных графиков (`active=True`):
  - При `next_due_on - local_today` от 1 до 3 дней: тип `THREE_DAYS_BEFORE`.
  - При `next_due_on <= local_today`: тип `ON_DUE_DATE`.
- Гарантия идемпотентности: уникальный индекс в БД `UNIQUE(schedule_id, planned_due_on, notification_type, recipient_id)` предотвращает повторные отправки.

### 6.6. Обработка ошибок по стандарту RFC 9457
Все ошибки формируются глобальным обработчиком исключений:
```json
{
  "type": "https://mini-cmms.example/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Field 'inventory_number' cannot be blank.",
  "instance": "/api/v1/equipment",
  "code": "VALIDATION_ERROR",
  "invalid_params": [...]
}
```

---

## 7. Этапы пошаговой реализации (Vertical Slices Roadmap)

1. **Фаза 1: Каркас инфраструктуры и базы данных**
   - Настройка `backend/pyproject.toml` (uv), `compose.yml` в корне, Dockerfile, конфигураций, сессии asyncpg.
   - Базовая модель SQLAlchemy, скрипты Alembic.
   - RFC 9457 exception handlers, `/health` и `/ready`.
2. **Фаза 2: Домен Auth & Users**
   - Модели `User` и `UserSession`.
   - Сервис паролей Argon2, генерация и проверка bearer-токенов.
   - Redis Rate Limiter на логин.
   - Роуты `/api/v1/auth/login`, `/logout`, `/me`, `/users` (CRUD, смена пароля, блокировка).
3. **Фаза 3: Домен Equipment & Faults**
   - Модели `Equipment` и `Fault`.
   - ETag/If-Match middleware/утилиты.
   - CRUD оборудования, архивация/восстановление, поиск `q`.
   - Регистрация и ведение неисправностей.
4. **Фаза 4: Домен Maintenance (Планы и графики ТО)**
   - Модели `MaintenancePlan` и `MaintenanceSchedule`.
   - Логика автоматического подключения оборудования к регламентам.
   - Расчет `next_due_on`, пересчет интервалов, деактивация графиков.
5. **Фаза 5: Домен Work Orders (Заявки и исполнение ТО)**
   - Модели `WorkOrder`, `WorkChecklistItem`, `WorkOrderEvent`, `WorkHistory`.
   - FSM переходов, наряды, чек-листы со snapshot-ами.
   - Команды `assign`, `reassign`, `start`, `complete`, `close`, `cancel`.
6. **Фаза 6: Redis + ARQ Worker и Уведомления**
   - Модель `Notification`.
   - ARQ worker задачи, генерация уведомлений по временным окнам ТО.
   - Эндпоинты `/api/v1/notifications`.
7. **Фаза 7: Интеграционное тестирование и приемка**
   - Запуск сквозных сценариев из `docs/Mini_CMMS_API_Test_Cases.csv`.
   - Проверка мутационным валидатором `docs/Mini_CMMS_API_Validation.py`.
   - Сверка покрытия OpenAPI 3.1.1.

---

## 8. Что оставляется на усмотрение разработчика (Left to Builder)
- Внутреннее разбиение вспомогательных функций в `app/utils/`.
- Точные наименования вторичных индексов в миграциях БД (при условии соблюдения уникальных составных ограничений).
- Оптимизация SQL-запросов (например, использование `selectinload` для связей).
