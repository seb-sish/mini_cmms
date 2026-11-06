# Mini-CMMS

Система учёта оборудования, неисправностей и технического обслуживания.
Backend: FastAPI / PostgreSQL / Redis / ARQ. Frontend: Next.js / React / TypeScript.

## Запуск через Docker Compose

Из корня репозитория подготовьте `.env` по `.env.example`, задайте пароль PostgreSQL
и допустимые CORS origins, затем выполните:

```bash
docker compose --env-file .env up -d --build
docker compose --env-file .env ps
```

Миграции применяет сервис `migrate` перед запуском API и worker.
Первый администратор создаётся отдельной командой — см. [backend/README.md](backend/README.md).
Секреты и `.env` не коммитятся.

Frontend опубликован только на `127.0.0.1:3000`; backend — на порту `APP_PORT`
(по умолчанию 8000). PostgreSQL и Redis не публикуют порты на хосте.
Внутри Compose BFF обращается к `http://backend:8000`, браузер — к `/api/*` своего origin.
Для production нужен HTTPS: сессионная cookie имеет флаг `Secure`.

`APP_COMPANY_TIMEZONE` используется API и передаётся в сборку frontend.
При его изменении frontend нужно пересобрать: `NEXT_PUBLIC_*` встраивается в JavaScript.

## Traefik и TLS

Конфигурация [deploy/traefik/mini-cmms.yml](deploy/traefik/mini-cmms.yml) предназначена
для существующего Traefik на том же хосте с `network_mode: host`:

- `minicmms.sneakypeeky.fun` → `http://127.0.0.1:3000`;
- `api.minicmms.sneakypeeky.fun` → `http://127.0.0.1:8000`.

Файл устанавливается в каталог file provider:

```bash
cp deploy/traefik/mini-cmms.yml /root/docker-services/traefik/dynamic/mini-cmms.yml
```

На этом сервере включены наблюдение за каталогом и перенаправление HTTP → HTTPS.
Для внешнего редиректа TCP-порты 80 и 443 должны доходить до Traefik;
при наличии NAT необходимо настроить их проброс на сервер.
Resolver `letsencrypt` получает и продлевает сертификаты через Cloudflare DNS challenge.
DNS доменов должен указывать на сервер; токен Cloudflare и ACME-хранилище остаются
в инфраструктуре Traefik и не входят в репозиторий.
В статической конфигурации `certificatesResolvers.letsencrypt.acme.dnsChallenge`
заданы `resolvers: ["1.1.1.1:53", "8.8.8.8:53"]`: это обходит NXDOMAIN от
локального DNS при проверке новой ACME-записи. Изменение статической конфигурации
требует перезапуска Traefik.
Если меняются `FRONTEND_PORT` или `APP_PORT`, обновите соответствующий адрес в маршруте.

## Проверки и разработка

Frontend:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

Подробнее: [frontend/README.md](frontend/README.md),
[backend/README.md](backend/README.md),
[контракт API](docs/Mini_CMMS_OpenAPI_3.1.1.yaml).
Healthcheck frontend проверяет `/login`; готовность PostgreSQL и Redis проверяет
`/ready` backend. Эти проверки не заменяют сквозные бизнес-сценарии.
