# Исправление результатов независимого аудита Mini-CMMS — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** устранить все 20 групп замечаний аудита, подтвердить соответствие работающего backend нормативному OpenAPI и получить воспроизводимую процедуру первого запуска.

**Architecture:** сохраняем существующие FastAPI routers → services → SQLAlchemy и текущие границы MVP. Исправляем проверки и транзакции в существующих сервисах; повторяющуюся синхронизацию индивидуальных графиков размещаем в MaintenanceService. Строгий HTTP-контракт проверяем через ASGI, конкурентные инварианты — отдельными соединениями настоящего PostgreSQL, лимит входа и ARQ — с настоящим Redis.

**Tech Stack:** Python 3.13, uv, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, PostgreSQL 16, Redis 7, ARQ, pytest, Docker Compose.

**Spec:** [OpenAPI 3.1.1](../../Mini_CMMS_OpenAPI_3.1.1.yaml), [Design Notes](../../Mini_CMMS_API_Design_Notes.md), [Acceptance](../../Mini_CMMS_API_Acceptance.md), [кейсы](../../Mini_CMMS_API_Test_Cases.csv), [flow fixtures](../../Mini_CMMS_API_Examples.yaml).

## Исходная точка и границы

- Аудит выполнен на `d951d2217ae1284f89ac9abafab07ec1096eb102`, ветка `main`. На момент составления плана SHA тот же, дерево чистое.
- Исходный отчёт: `/tmp/mini-cmms-audit-20261025-nUx9l5/REVIEW.md`. Временные репродукции полезны для переноса в тесты, но не являются зависимостью плана: обязательные сценарии перечислены ниже.
- Ранее прошли 50 тестов на SQLite/fakeredis и статическая проверка контракта: 384 кейса, 41 операция, ошибок 0. Это исходные результаты аудита, а не подтверждение исправлений или runtime PostgreSQL/Redis.
- Ruff ранее выдал 499 диагностик. Их число не равно числу runtime-дефектов; исправление линтера выделено отдельно.
- Этот документ — план. Изменения приложения, запуск инфраструктуры, миграции и развёртывание в ходе его подготовки не выполняются.

## Global Constraints

- Сохраняем согласованные Q1–Q18: состав MVP, роли, отмену CREATED/ASSIGNED, opaque bearer на 12 часов, текущие права пользователя, UTC с `Z`, правила досрочного ТО и пересчёта дат.
- Нормативный контракт — `docs/Mini_CMMS_OpenAPI_3.1.1.yaml`, версия API `1.0.0`. Не ослаблять схемы, видимость или бизнес-инварианты ради прохождения существующих тестов.
- PATCH User, Equipment, Fault, MaintenancePlan, WorkOrder требует один сильный `If-Match: "<uuid>:<version>"`. Отсутствующий заголовок — 428; некорректный — 422; корректный устаревший/чужой — 412. Checklist использует ETag родительского WorkOrder.
- Фактическое изменение увеличивает version атомарно; no-op не меняет version, даты и журнал. Автоматические изменения связанных ресурсов подчиняются тому же правилу.
- Одна транзакция охватывает бизнес-проверки, изменения связанных сущностей, версии и события. Проигравшая конкурентная операция не оставляет частичных изменений.
- Не менять `.env`, credentials или пользовательские секреты. Не печатать их в командах, логах и отчётах. Не использовать реальные данные для тестов.
- Alembic revision создавать только через `uv run alembic revision --autogenerate -m "<commit_name>"`; проверять сгенерированный diff, ограничения и сохранность данных. Не переписывать применённые 001–006.
- Новые зависимости — только необходимые для контрактных тестов: существующему validator нужны PyYAML, jsonschema с format checking, openapi-spec-validator. Сначала проверить, какие из них уже доступны/закреплены.
- Один writer в checkout. Независимые read-only ревью разрешены после реализации и проверок. Коммиты локальные, по задаче; push/merge/deploy требуют отдельного явного разрешения.

## Review Focus

1. Два запроса проходят одну предварительную проверку: после фиксации одного второй обязан перечитать состояние и получить 412/409, а не затереть данные. Задачи 3, 4, 7, 9.
2. Login проверяет старый пароль до reset/block: после фиксации изменения новая действующая сессия по прежним credentials невозможна. Задача 4.
3. Архив, категория и enabled меняются в разном порядке: пары графиков сохраняют id/даты, активность отражает все условия, отсутствующие пары создаются ровно один раз. Задачи 8, 9.
4. PATCH различает пропуск, null, пустую строку и повтор текущего значения: схема, версия, timestamp и события согласованы. Задачи 2, 3, 10.
5. Два worker tick пересекаются или процесс прерывается: уникальность не приводит к падению tick и потере остальных вставок; повтор восстанавливает положенные уведомления. Задача 11.

## Трассировка замечаний

| № аудита | Проблема | Задачи |
|---|---|---|
| 1 | Последний ADMIN; роль техника при COMPLETED | 4 |
| 2 | Login после сброса пароля | 4 |
| 3 | TECHNICIAN читает чужое оборудование | 6 |
| 4 | OPERATOR привязывает чужую неисправность | 6 |
| 5 | Неатомарный If-Match | 3 |
| 6 | Две активные заявки на один источник | 7, 9 |
| 7 | Обход лимита входа параллельными запросами | 5 |
| 8 | Публикация PostgreSQL/Redis наружу | 13 |
| 9 | Жизненный цикл и версия Fault | 7 |
| 10 | Категория не синхронизирует графики; лишний запрет при REPAIR | 8 |
| 11 | Enable/restore не создают пары; активируют архив | 8 |
| 12 | Гонка interval PATCH и PLANNED | 9 |
| 13 | Нет первого ADMIN на пустой БД | 12 |
| 14 | Строгие DTO, заголовки и HTTP расходятся со схемами | 2, 15 |
| 15 | Техник не читает собственную карточку WorkHistory | 6 |
| 16 | No-op, UPDATED, checked_at и comment=null | 10 |
| 17 | COMPLETED ошибочно остаётся просроченным | 9 |
| 18 | Конкурентный tick падает на UNIQUE | 11 |
| 19 | .dockerignore вне build context | 13 |
| 20 | Названия checklist ошибочно регистронезависимы | 8 |

## Порядок и зависимости

Основной порядок: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15.

Это рекомендуемый последовательный маршрут для одного writer. Задачу 13 можно выполнить сразу после 1, чтобы раньше закрыть публикацию хранилищ. Задачи 6 и 12 не требуют завершения логики графиков. Задача 9 обязательно использует решения 3, 7 и 8; финальная приёмка — результаты всех предыдущих задач.

Для каждого блока: регрессионный тест → зафиксированный RED по нужной причине → минимальное исправление → targeted GREEN → локальный коммит. Если тест неожиданно проходит, сначала пересмотреть репродукцию и актуальность замечания. Не писать тест, который проходит из-за невалидного тела, отсутствия авторизации или неверной фикстуры.

### Задача 1. Воспроизводимые интеграционные тесты и проверка контракта

**Files:** modify `backend/tests/conftest.py`, `backend/pyproject.toml`, `backend/uv.lock`; create `compose.test.yml`, `backend/tests/integration/conftest.py`, `backend/tests/integration/test_infrastructure.py`, `backend/tests/contract/conftest.py`, `backend/tests/contract/test_schema_validation.py`.

**Interfaces:** существующие быстрые SQLite/fakeredis fixtures сохраняются. Новые integration fixtures создают отдельные AsyncSession на каждую конкурентную операцию; никакой общей session через dependency override. Тестовые сервисы доступны только через loopback на отдельных портах, имя Compose project — `mini_cmms_test`.

- [ ] Создать отдельные PostgreSQL/Redis для тестов без `container_name` и ссылок на production volumes. Использовать только тестовые credentials и DSN; fixtures должны отклонять DSN, не принадлежащий этому тестовому окружению. Фикстуры очищают только собственные тестовые данные.
- [ ] Подключить markers `integration` и `contract`. Для отсутствующей infrastructure интеграционный запуск должен завершаться понятной ошибкой, а не незаметно превращаться в полный skip.
- [ ] Добавить `test_migrations_apply_to_empty_database` и `test_independent_sessions_observe_committed_state`: схема создаётся Alembic `upgrade head`, не `Base.metadata.create_all`. Проверить одну голову, ожидаемые таблицы, настоящий Redis PING.
- [ ] Добавить общий assertion для ответа по конкретным path/method/status исходного YAML: status, media type, обязательные заголовки и тело через JSON Schema с format checking и разрешением `$ref`. Не использовать сгенерированный FastAPI OpenAPI как oracle.
- [ ] Проверить assertion искусственным нарушением копии корректного ответа: extra property, неверный enum, timestamp без `Z`, отсутствующий required, неверный заголовок должны обнаруживаться.
- [ ] Запуск: из корня `rtk proxy docker compose -p mini_cmms_test -f compose.test.yml up -d --wait`; из backend `rtk proxy uv run --frozen pytest tests/integration/test_infrastructure.py tests/contract/test_schema_validation.py -v`. Зафиксировать команды подготовки test DSN без раскрытия секретов.
- [ ] Локальный коммит `test(backend): добавлены проверки реальных зависимостей`.

**Готово:** миграции проходят с нуля; тестовые сессии действительно независимы; ошибочный JSON отвергается oracle. Дальнейшие гонки запускаются на этой базе.

### Задача 2. Строгие DTO и HTTP-профиль

**Files:** modify `backend/app/schemas/{auth,user,equipment,fault,maintenance,work_order,common}.py`, затронутые routers в `backend/app/api/v1/`, `backend/app/api/dependencies.py`, `backend/app/errors/handlers.py`; modify существующие API/contract tests; create `backend/tests/contract/test_http_schema_conformance.py`.

**Interfaces:** нормативные request/response schemas, параметры и headers OpenAPI. Общую конфигурацию DTO применять только там, где одинаковые правила действительно заданы схемами; response projection должна соответствовать каждому конкретному DTO.

- [ ] Перенести в параметризованные тесты: login/user creation с extra property → 422; `role:null` при PATCH → 422; лишние `token` и `user.full_name` в успешном login отсутствуют. Перевести старые тесты с `json()["token"]` на нормативное поле токена из спецификации.
- [ ] Зафиксировать RED: whitespace-only result/reason и пустой элемент replaced_parts отклоняются; неизвестный status в WorkOrderCreate отклоняется, а не игнорируется. Проверить пропуск/null отдельно по каждой схеме, включая разрешённый nullable comment.
- [ ] Добавить таблицу If-Match: missing428; weak/wildcard/list/unquoted/signed/leading-zero version/malformed UUID — 422; корректный чужой UUID/устаревшая версия — 412. Сопоставить точную грамматику с исходным parameter schema перед реализацией.
- [ ] Покрыть HTTP-профиль: malformed JSON400, неверный Content-Type415, ProblemDetail по RFC9457, 401 с `WWW-Authenticate: Bearer`, успешное создание с нормативным Location, 405 с Allow. Проверить приоритет аутентификации, прав и синтаксических ошибок по Design Notes, включая смешанные ошибки.
- [ ] Проверить q/filters/sort/pagination на всех списках; отдельно воспроизвести игнорирование users.q, equipment.location, limit=0 и offset=-1. Проверить UTC `Z` и required business fields в ответах COMPLETED/CLOSED.
- [ ] Исправить DTO/routers/общую обработку, затем `rtk proxy uv run --frozen pytest tests/contract tests/test_auth_api.py tests/test_users_contract.py tests/test_protocol_and_problems.py tests/test_system_and_errors.py -v`. Не ослаблять старые assertions для сохранения неправильного ответа.
- [ ] Локальный коммит `fix(api): исправлено соответствие строгому контракту`.

**Готово:** обнаруженные входные/выходные нарушения отвергаются настоящими схемами; корректные примеры сохраняют успех. Атомарность версии закрывается следующей задачей.

### Задача 3. Атомарные версии и ETag

**Files:** modify `backend/app/services/{user,equipment,fault,maintenance,work_order}_service.py`, при необходимости `backend/app/db/base.py`; create `backend/tests/integration/test_version_conflicts.py`; extend tests User/Equipment/Fault/Maintenance.

**Interfaces:** сохранить существующие публичные методы сервисов. Выбранный механизм для изменяемых строк — `SELECT … FOR UPDATE`, затем повторная проверка expected_version и изменение в той же транзакции. Учитывать уже взятые блокировки, не делать промежуточный commit. Не включать глобально ORM versioning без отдельной проверки всех автоматических обновлений.

- [ ] До правки найти все callers и присваивания `.version`/bulk UPDATE. Составить перечень PATCH и POST, автоматически меняющих те же ресурсы; включить User, Equipment, Fault, MaintenancePlan, WorkOrder и checklist.
- [ ] RED на настоящем PostgreSQL: два PATCH одного ресурса с ETag версии1, независимые sessions, управляемая точка пересечения; ровно один 200/version2 и один 412. Повторить для четырёх ранее незащищённых ресурсов и проверить уже защищённый WorkOrder.
- [ ] Добавить проверки: rollback бизнес-ошибки не меняет version; корректный no-op не увеличивает её; ответное тело и ETag совпадают с последующим GET; автоматическая смена Fault тоже меняет его version.
- [ ] Реализовать атомарную проверку в существующих сервисах. Любую проверку, зависящую от изменяемого состояния, повторять после получения блокировки. Не сериализовать все PATCH приложения одной глобальной блокировкой.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_version_conflicts.py -v` и затронутые resource tests. Гонки должны использовать barriers/events и timeout, а не `sleep` как доказательство.
- [ ] Локальный коммит `fix(db): исправлена атомарность версий ресурсов`.

**Готово:** исходная гонка Writer A/Writer B не приводит к двум успехам. Обычные последовательные PATCH и независимые ресурсы работают.

### Задача 4. Последний ADMIN, назначения и безопасность сессий

**Files:** modify `backend/app/services/{user,auth}_service.py`, `backend/app/api/dependencies.py` при необходимости; create `backend/tests/integration/test_user_session_races.py`; extend `backend/tests/test_users_api.py`, `backend/tests/test_auth_api.py`.

**Interfaces:** login, reset password, block и role changes используют блокировку той же строки User. Операции, способные уменьшить число ACTIVE ADMIN, сначала получают общую транзакционную PostgreSQL advisory lock с постоянным документированным ключом, затем нужную строку пользователя; тот же порядок использует bootstrap из задачи12. Сессии хранятся в текущей модели UserSession.

- [ ] RED: два администратора одновременно блокируют/понижают друг друга → остаётся ≥1 ACTIVE ADMIN; один успех, второй контрактный409. Проверить также `update_status` и сочетание block с role change.
- [ ] RED: роль техника нельзя сменить при ASSIGNED, IN_PROGRESS или COMPLETED; после допустимой развязки по контракту смена возможна. Уведомления, данные и история сохраняются, права берутся из новой роли.
- [ ] RED: login со старым паролем приостановлен до записи UserSession; reset фиксируется; продолженный login не создаёт пригодную сессию. Аналогично block. Проверить оба допустимых порядка завершения транзакций.
- [ ] Реализовать общий порядок блокировок и повторную проверку credentials/status под User lock. Смена пароля, version и отзыв сессий фиксируются вместе. Приоритет ошибок и срок12 часов сохраняются.
- [ ] Проверить logout только текущей сессии; reset всех сессий; немедленное действие block/role на уже выданный токен. Убедиться, что ошибочный reset не отзывает сессии.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_user_session_races.py tests/test_auth_api.py tests/test_users_api.py tests/test_users_contract.py -v`.
- [ ] Локальный коммит `fix(auth): исправлены гонки пользователей и сессий`.

**Готово:** ноль ACTIVE ADMIN недостижимо из корректного состояния; старые credentials не переживают reset; версия и отзыв согласованы.

### Задача 5. Атомарный лимит входа по IP и login

**Files:** modify `backend/app/core/rate_limiter.py`, `backend/app/services/auth_service.py`; extend `backend/tests/test_rate_limiter.py`; create `backend/tests/integration/test_login_rate_limit.py`.

**Interfaces:** сохраняем контракт: после пяти INVALID_CREDENTIALS в скользящем окне10 минут по IP **или** lowercase(login) последующие попытки получают429. Успешные входы и остальные ошибки не становятся ошибочными credentials.

- [ ] RED на настоящем Redis: четыре прошлые ошибки, затем восемь параллельных неверных входов → только одна новая401, остальные429. Проверить общий IP с разными login и общий login с разных IP, включая регистр.
- [ ] Сериализовать полный участок «проверка обоих лимитов → проверка credentials → регистрация результата» между процессами: Redis locks для обоих нормализованных ключей в стабильном порядке. Атомарных INCR/ZADD по отдельности недостаточно. Отпускать lock только владельцем; контролировать lease/продление, cancellation и timeout.
- [ ] Реализовать атомарную очистку окна/подсчёт/Retry-After средствами Redis. Не допускать шестую проверку credentials при потере lease; отказ Redis должен давать предусмотренный контрактом ответ зависимости, а не обходить лимит.
- [ ] Проверить границы окна, истечение TTL, валидные credentials при исчерпанном лимите, округление Retry-After, одновременные успех/ошибку и прекращённый запрос. Успешный вход не обнуляет окно;400/422 не увеличивают счётчик. Проверить отсутствие дедлока при пересечении пар ключей.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/test_rate_limiter.py tests/integration/test_login_rate_limit.py -v`.
- [ ] Локальный коммит `fix(auth): исправлена атомарность лимита входа`.

**Готово:** ограничения работают между независимыми экземплярами приложения; тест одного процесса/fakeredis не заменяет этот gate.

### Задача 6. Видимость оборудования, неисправностей и истории

**Files:** modify `backend/app/services/equipment_service.py`, `backend/app/services/work_order_service.py`, при необходимости `backend/app/services/fault_service.py`; extend `backend/tests/test_faults_and_equipment_contract.py`; create `backend/tests/contract/test_access_matrix.py`.

**Interfaces:** текущая роль и связи определяют доступ до бизнес-операции. Невидимый объект возвращает404; запрет операции роли —403 согласно нормативному приоритету. Список, total и карточка используют эквивалентные ограничения.

- [ ] RED: TECHNICIAN без назначений видит total0 и получает404 на чужую карточку; после назначения видит связанное оборудование, после переназначения теряет доступ к незавершённой работе и соответствующим объектам по матрице.
- [ ] RED: OPERATOR не может создать REPAIR на чужую Fault, даже зная её UUID и equipment_id;404, ноль новых WO/events, Fault не меняется. Своя Fault остаётся доступна по бизнес-правилам.
- [ ] RED: TECHNICIAN читает собственную WorkHistory и из списка, и по id; чужая404. После смены роли применяются права новой роли; сохранность истории не равна сохранению прежних полномочий.
- [ ] Исправить ограничения выборок и разветвление WorkHistoryService.get_work_history. Не фильтровать страницы после SQL pagination; total считать с тем же predicate.
- [ ] Добавить таблицу ADMIN/ENGINEER/TECHNICIAN/OPERATOR для list/detail/mutation затронутых ресурсов, архивного оборудования и inaccessible UUID.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/contract/test_access_matrix.py tests/test_faults_and_equipment_contract.py -v`.
- [ ] Локальный коммит `fix(rbac): исправлена видимость производственных данных`.

### Задача 7. Уникальность заявок и жизненный цикл Fault

**Files:** modify `backend/app/services/work_order_service.py`, `backend/app/db/models/work_order.py`, `backend/app/services/fault_service.py`; create Alembic revision в `backend/app/db/alembic/versions/`; create `backend/tests/integration/test_work_order_creation_races.py`; extend `backend/tests/test_work_order_create.py`, `backend/tests/test_work_order_lifecycle.py`.

**Interfaces:** при создании REPAIR блокируется Fault до проверки состояния/дубликата. Для PLANNED порядок — Plan → Equipment → Schedule → WorkOrder; задача9 использует тот же порядок. Для нескольких однотипных строк — сортировка UUID. Нельзя сначала заблокировать дочерний WorkOrder, а затем ожидать родителя, если противоположный путь делает обратное: проверить start/cancel/complete/close и archive.

- [ ] RED: конкурентное создание REPAIR на одной Fault и PLANNED на одном Schedule → один201, второй409; нет дубликатов/лишних событий. Активными считаются CREATED/ASSIGNED/IN_PROGRESS/COMPLETED; CLOSED/CANCELLED не занимают слот по правилам источника.
- [ ] RED lifecycle: создание REPAIR оставляет Fault OPEN; start переводит в IN_PROGRESS; complete — в RESOLVED; соответствующие изменения увеличивают Fault.version. Создание на RESOLVED отклоняется; cancel не создаёт WorkHistory и оставляет Fault OPEN по утверждённым правилам.
- [ ] Ввести partial unique indexes на непустой fault_id и schedule_id для незакрытых состояний. Индекс Schedule запрещает две активные заявки даже при различающихся planned_due_on. UNIQUE violation преобразовывать в правильный409 после корректного rollback/savepoint, не в500.
- [ ] Перед миграцией выполнить read-only preflight дубликатов в целевой тестовой копии. При неоднозначных реальных дублях остановить применение и выдать перечень id: автоматически отменять/удалять наряды запрещено. Для initial schema проверить индексы именно после Alembic, не только metadata.
- [ ] Реализовать проверки/переходы и блокировки. Добавить гонки create с cancel/complete/archive; итог обязан соответствовать одному допустимому последовательному порядку.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_work_order_creation_races.py tests/test_work_order_create.py tests/test_work_order_lifecycle.py tests/test_work_order_complete_close.py -v`; проверить upgrade существующей корректной БД без потери записей.
- [ ] Локальный коммит `fix(work-orders): исправлены уникальность и переходы неисправностей`.

### Задача 8. Синхронизация графиков при категории, enable и restore

**Files:** modify `backend/app/services/maintenance_service.py`, `backend/app/services/equipment_service.py`; extend `backend/tests/test_schedule_recalculation.py`, `backend/tests/test_maintenance_contract.py`, `backend/tests/test_faults_and_equipment_contract.py`; create `backend/tests/integration/test_schedule_sync.py`.

**Interfaces:** переиспользовать `MaintenanceService.generate_schedules_for_new_equipment`, выделив в этом сервисе `async sync_equipment_schedules(self, equipment: Equipment) -> None` без внутреннего commit. Метод сверяет все существующие и подходящие пары данного оборудования: создаёт отсутствующие и обновляет активность существующих; callers фиксируют общую транзакцию. Изменение плана вызывает ту же операцию для объединения уже связанных и вновь подходящих equipment, отсортированных по UUID. Активность = enabled плана AND оборудование не архивировано AND попадает в scope плана.

- [ ] RED A→B→A: старый Schedule A сохраняет id/дату, на B появляется ровно одна пара, после возврата B неактивен, A возобновлён; worker использует только допустимые пары.
- [ ] RED: оборудование создано при disabled плане → enable создаёт пару; план создан во время архива → restore создаёт пару. Для первого подключения `next_due_on=max(first_due_on, company_today)`; существующие даты не сдвигаются.
- [ ] RED archive→disable→enable: график архивного оборудования остаётся неактивен. Повторный enable/restore не плодит пары и не меняет версии без фактических изменений.
- [ ] RED: REPAIR не запрещает смену категории; незакрытый PLANNED запрещает с409 `ACTIVE_MAINTENANCE_WORK`. Проверить COMPLETED до close и отсутствие частично изменённых категорий/графиков.
- [ ] RED checklist templates: `Inspect` и `inspect` принимаются как разные названия при create и replace; истинные дубликаты после нормативной нормализации пробелов отклоняются. Убрать `.lower()` только из сравнения названий checklist.
- [ ] Подключить общую синхронизацию ко всем callers: create/update Equipment, archive/restore, create/enable/update Plan, изменение scope если оно разрешено контрактом. Для конкурентных путей соблюдать порядок задачи7; проверить существующее ограничение UNIQUE пары plan/equipment, добавить через Alembic только если отсутствует.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_schedule_sync.py tests/test_schedule_recalculation.py tests/test_maintenance_contract.py tests/test_faults_and_equipment_contract.py -v`.
- [ ] Локальный коммит `fix(maintenance): исправлено подключение и возобновление графиков`.

### Задача 9. Конкурентный пересчёт дат и признак просрочки

**Files:** modify `backend/app/services/maintenance_service.py`, `backend/app/services/work_order_service.py`, затронутые пути Equipment; create `backend/tests/integration/test_schedule_work_order_races.py`; extend `backend/tests/test_schedule_recalculation.py`, `backend/tests/test_maintenance_contract.py`.

**Interfaces:** interval PATCH получает Plan lock, блокирует затронутые Equipment/Schedule в общем порядке задачи7 и только затем проверяет незакрытые PLANNED и новые даты. Создание и закрытие PLANNED используют совместимые блокировки. Проверки всех графиков и изменение всего плана атомарны.

- [ ] RED: interval PATCH приостановлен после предварительного чтения, второй запрос создаёт PLANNED. После сериализации либо PATCH первый и WO фиксирует новую дату, либо WO первый и PATCH409. Успех обоих со старым planned_due_on и новым next_due_on невозможен.
- [ ] Зафиксировать правила дат тестами: до первого ТО сохраняется индивидуальный next_due_on; после — last_completed_on+новый interval; пересчёт ≤ последнего закрытого planned_due_on даёт409 и rollback всего плана, включая уже проверенные графики.
- [ ] Проверить досрочное выполнение: `company_today + interval_days > planned_due_on`; равенство409 `TOO_EARLY_TO_COMPLETE`. Для due05.11/interval30:06.10 отказ,07.10 разрешено. Отмена не меняет даты ТО.
- [ ] RED: COMPLETED текущего срока снимает is_overdue в list и detail до close, но сохраняет has_current_work_order. Проверить CREATED/ASSIGNED/IN_PROGRESS, CLOSED/CANCELLED, вчера/сегодня/завтра и timezone предприятия.
- [ ] Реализовать общий расчёт флагов списка/карточки без расхождения predicates; проверить неактивные графики и отсутствие сдвига даты при pause/resume.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_schedule_work_order_races.py tests/test_schedule_recalculation.py tests/test_maintenance_contract.py tests/test_work_order_complete_close.py -v`.
- [ ] Локальный коммит `fix(maintenance): исправлены конкурентный пересчёт и просрочка`.

### Задача 10. PATCH заявки и checklist без ложных изменений

**Files:** modify `backend/app/services/work_order_service.py`, `backend/app/schemas/work_order.py`; extend `backend/tests/test_work_orders_contract.py`, `backend/tests/test_work_order_lifecycle.py`; create `backend/tests/test_work_order_patch_semantics.py`.

**Interfaces:** patch_work_order и check_item сохраняют ответы нормативного DTO; checklist возвращает новый ETag родителя. Для comment различать отсутствие поля и явныйnull через Pydantic fields_set/исходный набор переданных полей.

- [ ] RED: PATCH текущего title/description не меняет version/updated_at/events; реальное изменение создаёт один UPDATED с нормативными данными и увеличивает version один раз.
- [ ] RED: false→true устанавливает checked_at; повтор true сохраняет его; true→false очищает; comment-only не переписывает checked_at. `comment:null` очищает старое значение, отсутствие comment сохраняет его.
- [ ] Проверить проверку версии родителя при двух конкурентных checklist PATCH: один успех, один412, без частичного изменения пункта.
- [ ] Исправить diff-aware update в существующих методах. Не выпускать UPDATED для no-op и не терять существующие события start/assign/cancel/complete/close.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/test_work_order_patch_semantics.py tests/test_work_orders_contract.py tests/test_work_order_lifecycle.py tests/integration/test_version_conflicts.py -v`.
- [ ] Локальный коммит `fix(work-orders): исправлена семантика patch и чек-листа`.

### Задача 11. Идемпотентный конкурентный worker

**Files:** modify `backend/app/worker/tasks.py`, при необходимости модель Notification и новая Alembic revision; extend `backend/tests/test_arq_tasks.py`; create `backend/tests/integration/test_notification_worker.py`.

**Interfaces:** generate_maintenance_notifications сохраняет установленный catchup и получателей. Уникальность — schedule, planned date, notification type, recipient. PostgreSQL INSERT ON CONFLICT DO NOTHING должен ссылаться на фактическое соответствующее ограничение; предварительный SELECT не является защитой от гонки.

- [ ] RED: два tick одновременно проходят отбор одинаковых получателей; оба завершаются без IntegrityError, каждому положенному адресату ровно одна запись. В одном tick добавить ещё другую запись, чтобы проверить отсутствие rollback полезной вставки.
- [ ] Зафиксировать T−3…T−1 → только предварительное; с due до выполнения → только актуальное о сроке. Catchup после простоя не создаёт пачку устаревших уведомлений; повторный tick ничего не дублирует.
- [ ] Проверить ACTIVE ENGINEER, текущего ACTIVE исполнителя, reassign на следующем tick, COMPLETED, CANCELLED, архив, паузу, смену категории, timezone и повтор той же даты при разрешённом сценарии.
- [ ] Заменить check-then-insert на атомарную вставку. Проверить отмену/ошибку tick до commit и повторный запуск; данные после повтора полны и уникальны.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_notification_worker.py tests/test_arq_tasks.py tests/test_notifications_api.py -v`; отдельным smoke убедиться, что задача действительно выполняется процессом ARQ с Redis, а не только прямым вызовом функции.
- [ ] Локальный коммит `fix(worker): исправлена конкурентная идемпотентность уведомлений`.

### Задача 12. Первый ADMIN и инструкция первого запуска

**Files:** create `backend/app/cli.py`, `backend/tests/integration/test_bootstrap_admin.py`; modify `backend/README.md`, `backend/app/config/config.py` только при необходимости использования существующих FIRST_ADMIN settings.

**Interfaces:** явная CLI-команда `uv run python -m app.cli bootstrap-admin` после миграций. Переиспользовать текущие settings, hash_password и модель User. Секрет передаётся через предусмотренную конфигурацию/скрытый ввод, никогда аргументом командной строки или в логе. Не добавлять публичную регистрацию или seed с default password.

- [ ] RED: пустая мигрированная БД → создан один ACTIVE ADMIN и успешный login; повтор команды ничего не меняет, пароль/role существующей учётной записи не перезаписываются.
- [ ] Проверить два параллельных bootstrap: одна запись; существующий login другой роли/заблокированный пользователь вызывает явный отказ без повышения прав. При уже существующем ACTIVE ADMIN команда не создаёт второго автоматически.
- [ ] Реализовать CLI с общей admin lock задачи4 и проверкой конфигурации. Удалить встроенный fallback FIRST_ADMIN_PASSWORD: без явно переданного секрета bootstrap отказывает, обычный запуск API не требует bootstrap-конфигурации. Ошибки не раскрывают credentials; существующие FIRST_ADMIN_* использовать для этой команды, не для скрытого startup seed.
- [ ] Описать команды миграции → bootstrap → login → ready; повторный запуск и восстановление ADMIN оформлять отдельной осознанной операцией, не скрытым поведением startup.
- [ ] Запустить `rtk proxy uv run --frozen pytest tests/integration/test_bootstrap_admin.py -v`.
- [ ] Локальный коммит `feat(admin): добавлено создание первого администратора`.

### Задача 13. Compose, build context и изоляция хранилищ

**Files:** modify `compose.yml`, `backend/Dockerfile`, `backend/README.md`; create `backend/.dockerignore`; проверить существующий root `.dockerignore`, не переносить его вслепую.

**Interfaces:** backend/migrate/worker обращаются к PostgreSQL/Redis по внутренней сети Compose. Для локального доступа с хоста использовать только отдельно описанный dev/test override с127.0.0.1; основной Compose не публикует5432/6379.

- [ ] До изменения зафиксировать текущий build context и опубликованные порты, не выводя значения интерполированных secrets. Исключить `.venv`, `.env*`, caches, `.git`, тестовые артефакты из backend context; оставить необходимые runtime-файлы и migrations.
- [ ] Убрать ports хранилищ из основного Compose. Устранить предсказуемый fallback пароля PostgreSQL: при отсутствии обязательной конфигурации запуск должен явно отказывать. Не изменять существующие `.env` и не генерировать в репозитории рабочие секреты.
- [ ] Проверить `rtk proxy docker compose config --quiet`. Собрать backend с frozen lockfile; проверить uv версии образа на фактическом lockfile, не объявлять несовместимость только из-за номера версии.
- [ ] В отдельном тестовом Compose project проверить размер/состав context и содержимое image: нет host `.venv`, env-файлов или локальных caches; зависимости и entrypoint работают.
- [ ] Smoke backend+migrate+worker+PostgreSQL+Redis: миграции до старта API, bootstrap, `/health`, `/ready`, Redis job. Недоступность зависимости даёт ready503, health200 при живом HTTP-сервисе; после восстановления ready200.
- [ ] Проверить отсутствие host bindings хранилищ и доступность по внутренним DNS. Остановка/удаление — только установленных тестовых объектов; не применять `down -v` к обычному проекту.
- [ ] Локальный коммит `fix(docker): исправлены изоляция хранилищ и контекст сборки`.

### Задача 14. Линтер и инструменты разработки

**Files:** modify фактически затронутые Ruff файлы в `backend/app/`, `backend/tests/`; modify `.vscode/settings.json`; `backend/pyproject.toml` только для обоснованной конфигурации.

**Interfaces:** текущие Python3.13 и нормативный YAML в docs. Не отключать группы правил или JSON Schema validation ради зелёного статуса. ORM forward references проверить через mapper initialization.

- [ ] Получить свежую классификацию `rtk proxy uv run --frozen ruff check app tests`; отдельно разобрать F821, затем imports/unused, UP и exception rules. Из аудита499 диагностик не выводить автоматически499 runtime-проблем.
- [ ] Исправлять безопасные группы небольшими порциями; не использовать `--unsafe-fixes` вслепую. Для F821 корректно оформить typing imports/forward refs и проверить mapper configuration и startup.
- [ ] Исправить VS Code associations на существующие `docs/*.yaml`: только нормативный OpenAPI связывать с OAS3.1; flow fixtures не выдавать за OpenAPI document. Проверить пути на диске.
- [ ] Запустить Ruff и полный pytest после механических правок. Форматирование всего репозитория без необходимости не включать в поведенческие коммиты.
- [ ] Локальный коммит `chore(backend): исправлены проверки качества и настройки схем`.

### Задача 15. Полная приёмка и независимое повторное ревью

**Files:** create `docs/reviews/2026-10-25-backend-remediation-acceptance.md`, `backend/tests/contract/test_documented_flows.py`; update `docs/Mini_CMMS_API_Acceptance.md` только результатами/трассировкой, существующие E2E tests — по нормативному контракту.

**Interfaces:** исходные 384 case id и четыре flow служат матрицей покрытия, не просто счётчиком. Файл приёмки содержит SHA, версии окружения, команды, результаты и явно непроверенные области.

- [ ] Составить таблицу «№ замечания/operationId/case id → regression test → результат». Для каждого из384 кейсов указать автоматизированный тест либо конкретную ручную проверку; неподтверждённый case не считать PASS. Проверить все41 операцию, включая негативные ответы и сохранность состояния после отказа.
- [ ] Выполнить четыре документированных flow через приложение на PostgreSQL/Redis. Проверять ответы исходными схемами, ETag, версии, события, WorkHistory, конечные даты и отсутствие побочных эффектов на ошибках; часы/worker контролировать воспроизводимо.
- [ ] Из backend: `rtk proxy uv run --frozen pytest -v`; затем явно `rtk proxy uv run --frozen pytest -m integration -v` с настоящими зависимостями. Пересекающиеся targeted/full результаты не складывать как независимое число тестов.
- [ ] Из backend: `rtk proxy uv run --frozen ruff check app tests`, `rtk proxy uv lock --check --offline`, `rtk proxy uv run --frozen alembic heads`. Ожидание: ошибок Ruff нет, lock согласован, одна ожидаемая голова.
- [ ] Из корня запустить существующий checker: `rtk proxy uv run --project backend --frozen python docs/Mini_CMMS_API_Validation.py`. Он должен сохранить PASS документации; runtime-тесты — отдельный результат.
- [ ] Подтвердить миграции на пустой БД и на копии схемы001–006 с репрезентативными данными, отсутствие их потери; отдельно конфликтные данные должны блокировать опасный upgrade с понятным диагнозом. Приёмка включает image build и Compose smoke задачи13.
- [ ] После GREEN заказать два независимых read-only ревью: `gpt-6.1-sol` для транзакций/сессий/прав/контракта; `gpt-6-luna` с effort max для инфраструктуры, документации и повторных проверок. Перед делегированием получить live capabilities и передать точный SHA, полный brief, список исходных замечаний, исправлений и оставшихся возражений.
- [ ] Новые подтверждённые дефекты закрыть собственным RED/GREEN и повторным ревью затронутой области. Финальный diff не должен содержать секретов, ослабления контрактных правил или чужих изменений.
- [ ] Зафиксировать `git diff`, `git diff --check`, SHA и ограничения проверки; локальный коммит `docs(review): добавлены результаты приёмки исправлений`.

## Критерии завершения

1. Все20 групп имеют регрессионное доказательство закрытия, включая подслучаи из групп1/10/11/14/16. Нет открытых P1/P2 по согласованной области.
2. На PostgreSQL доказаны версии, последний ADMIN, login/reset, уникальность WO, синхронизация и пересчёт графиков. На Redis — межпроцессный лимит и конкурентный worker; одного SQLite/fakeredis недостаточно.
3. Запросы, ответы и headers проходят исходные JSON Schema; все41 операция и четыре flow проверены; матрица384 кейсов имеет подтверждённый результат для каждого кейса.
4. Alembic проходит с нуля и с корректной существующей БД; конфликты данных не устраняются молча. Образ собирается; Compose smoke и bootstrap воспроизводимы; хранилища не опубликованы наружу.
5. Целевые/полные тесты, Ruff, validator и независимое ревью подтверждены на финальном SHA. Пропуски или сбои записаны как ограничения, а не как успешная проверка.
6. Результат готов к отдельному решению о развёртывании. Push, merge, deploy, проверка production и эксплуатационные испытания backup/restore/нагрузки не входят в разрешение на реализацию этого плана.

## Самопроверка плана

- Трассировка20/20 приведена выше; дополнительные наблюдения по Ruff и VS Code включены в задачу14.
- Все5 классов риска из Review Focus имеют конкретные регрессионные сценарии и владельца-задачу.
- Зависимости общего порядка блокировок и синхронизации явно передаются задачам7–9; публичные интерфейсы API и согласованные бизнес-решения сохраняются.
- План не зависит от существования временных репродукций в `/tmp`. Точные результаты проверок должны быть получены заново при реализации.
