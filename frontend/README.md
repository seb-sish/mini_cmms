# Mini-CMMS: фронтенд

Веб-клиент системы планирования и контроля технического обслуживания оборудования.
Реализует требования ФТ-01 - ФТ-18 из документа "Пункт 2. Требования" и контракт API 1.0.0
(`../docs/Mini_CMMS_OpenAPI_3.1.1.yaml`).

## Стек

| Технология | Версия | Назначение |
|---|---|---|
| Next.js (App Router, Turbopack) | 16.4.2 | Маршрутизация, BFF-прокси, сборка |
| React | 19.2.9 | UI |
| TypeScript | 5.9.3 | Строгая типизация (`strict: true`) |
| TanStack Query | 5.100.0 | Серверное состояние: кэш, инвалидация после команд |
| Vitest + Testing Library + jsdom | 3.2.7 | Unit-тесты |
| ESLint (`eslint-config-next`) | 9.39.5 | Линтинг и контроль границ FSD |

Redux не используется: всё состояние приложения серверное, локальное состояние форм хранится в компонентах.

## Запуск

```bash
npm ci
cp .env.example .env.local   # при необходимости поменять адрес API
npm run dev                  # http://localhost:3000
```

| Команда | Действие |
|---|---|
| `npm run dev` | Режим разработки |
| `npm run build` / `npm run preview` | Продакшн-сборка и запуск |
| `npm run typecheck` | Проверка типов |
| `npm run lint` | ESLint |
| `npm test` | Unit-тесты |

Переменные окружения:

| Переменная | Где используется | Пример |
|---|---|---|
| `CMMS_API_BASE_URL` | Только сервер Next (BFF) | `https://api.minicmms.sneakypeeky.fun` |
| `NEXT_PUBLIC_COMPANY_TIMEZONE` | Клиент, календарные расчёты | `Europe/Moscow` |

Для продакшена нужен HTTPS (НФТ-04): cookie сессии выставляется с флагом `Secure`.

### Docker

Из корня репозитория:

```bash
docker compose --env-file .env up -d --build
```

Dockerfile собирает standalone-сервер Next.js и запускает его от пользователя `node`.
Frontend доступен на `127.0.0.1:3000`, BFF использует `http://backend:8000`.
`APP_COMPANY_TIMEZONE` передаётся в сборку как `NEXT_PUBLIC_COMPANY_TIMEZONE`;
изменение часового пояса требует пересборки образа.
Healthcheck проверяет страницу `/login`.

Публичный адрес: `https://minicmms.sneakypeeky.fun`.
Настройка Traefik и автоматического TLS описана в [корневом README](../README.md).

## Архитектура

### Feature-Sliced Design

```
app/                    маршруты Next.js: тонкие файлы, передают параметры в FSD-страницы
  (main)/               защищённая зона с AppShell
  login/                вход
  api/auth/*, api/v1/*  BFF-обработчики
proxy.ts                редирект без сессии на /login
src/
  app/                  провайдеры (TanStack Query, флаги), тема и токены
  pages/                страницы: home, equipment-*, fault-*, plan-*, schedule-list, work-order-*, history-*, notification-list, user-*, login
  widgets/              app-shell, таблицы с фильтрами, карточка заявки
  features/             auth, user-management, equipment-management, fault-management,
                        maintenance-plan-management, work-order-create, work-order-actions
  entities/             user, equipment, fault, maintenance-plan, maintenance-schedule,
                        work-order, work-history, notification
  shared/               api (HTTP-клиент, ошибки, BFF), config, lib, ui (UI-кит)
pages/README.md         пустая папка, чтобы Next не принял src/pages за Pages Router
```

Правила импортов между слоями проверяет ESLint (`no-restricted-imports` в `eslint.config.mjs`).
Слайсы отдают наружу только публичный API из `index.ts`; фабрики тестовых данных лежат в `entities/*/testing.ts`.

### BFF и сессия

Браузер ходит только на свой origin:

- `POST /api/auth/login` проксирует вход, кладёт bearer-токен в cookie `cmms_session`
  (HttpOnly, SameSite=Lax, Secure в продакшене, срок = `expires_at`) и не возвращает токен в теле ответа.
- `POST /api/auth/logout` отзывает токен на бэке и очищает cookie.
- `/api/v1/*` проксирует запросы к API, подставляя `Authorization` из cookie. Наружу проходят `ETag`,
  `Location`, `Retry-After`, `Allow`. Кросс-доменные изменяющие запросы отклоняются (403),
  прямой вызов `/api/v1/auth/login` закрыт (404). Если бэк ответил 401, cookie очищается.

Такая схема решает три задачи: токен недоступен JavaScript, CORS не нужен, а заголовки `ETag` и `Retry-After`
читаемы (бэкенд не отдаёт `Access-Control-Expose-Headers`).

### Работа с API

- Все PATCH отправляют `If-Match: "<id>:<version>"` из последнего прочитанного объекта; PATCH пункта чек-листа
  использует версию заявки. При `412 VERSION_CONFLICT` данные перечитываются и пользователь получает сообщение.
- В PATCH уходят только изменённые поля, пустой PATCH не отправляется (кнопка сохранения неактивна).
- Ошибки разбираются по стабильному полю `code` (RFC 9457) и показываются на русском (`shared/api/errorMessages.ts`).
  Текст `detail` сервера пользователю не показывается.
- После любой команды над заявкой инвалидируются заявки, неисправности, графики, история и уведомления.
- Календарные даты считаются в часовом поясе предприятия (`shared/lib/date`).

### Права доступа

Видимость разделов и кнопок повторяет матрицу `x-allowed-roles` контракта (`entities/user/model/permissions.ts`,
`features/work-order-actions/model/workOrderActions.ts`). Это только удобство интерфейса, окончательную проверку
выполняет сервер. Прямой переход в недоступный раздел показывает сообщение `RoleGate`.

## Дизайн-система

Токены Atlassian Design System (Jira), перенесённые в CSS-переменные `--ds-*` (`src/app/styles/theme.css`).
Акцентная палитра переопределена под промышленную тематику:

- primary: petrol `#0A7275` (hover `#075A5C`, pressed `#054446`, selected `#E3F2F2`);
- secondary: графит `#1F2A33` для верхней навигации и брендинга;
- семантические цвета (danger, warning, success, information) и нейтральные цвета взяты из ADS без изменений.

Компоненты `shared/ui` повторяют паттерны ADS: Button, Lozenge, SectionMessage, Modal, Flag, DynamicTable,
Tabs, ProgressTracker, формы с подписью над полем и ошибкой под ним.

## Стиль кода

Стиль взят из проекта `company-landing-frontend`:

- компонент: папка `componentName/index.tsx` + `style.css`, стрелочная функция с типом `ReactElement`, `export default`;
- интерфейсы пропсов с префиксом `I`, варианты через `const enum`, константы `UPPER_SNAKE_CASE`;
- plain CSS с классами в kebab-case и токенами из CSS-переменных;
- каждый импорт на отдельной строке: default-импорты по возрастанию длины, named-импорты по убыванию, CSS последним;
- Prettier-формат: 80 символов, двойные кавычки, `trailingComma: es5`. Комментариев в коде нет.

## Тесты

Только unit-тесты (`*.test.ts(x)` рядом с кодом), интеграционные и e2e пишет тестировщик:

- доменная логика: переходы статусов заявки, правило раннего планового ТО, сроки графика, матрица ролей;
- формы: валидация и сборка payload для POST и PATCH;
- инфраструктура: HTTP-клиент, разбор ошибок, хелперы BFF, защита от open redirect, политика повторов;
- UI: Button, Pagination, DataTable, Modal, LoginForm, навигация по ролям.

## Известные ограничения бэкенда

1. `GET /users` разрешён только ADMIN. Главный инженер не может получить список техников, поэтому
   в окне назначения включается запасной ввод UUID техника, а авторы и исполнители показываются как
   "Пользователь <id>". Когда бэкенд откроет инженеру справочник активных техников
   (`GET /users?role=TECHNICIAN&status=ACTIVE`), выбор из списка и фильтр по исполнителю заработают без
   изменений во фронтенде.
2. CORS бэкенда задаётся через `APP_CORS_ORIGINS`. Фронтенд обращается к API через BFF своего origin, поэтому не зависит от CORS и `Expose-Headers` backend.
3. Поле `details` в событиях заявки содержит технический текст на английском, поэтому в журнале оно не выводится.
