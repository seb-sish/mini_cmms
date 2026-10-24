# Mini-CMMS Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready, fully containerized asynchronous backend for the Mini-CMMS industrial maintenance management platform adhering strictly to OpenAPI 3.1.1 specification and RFC 9457.

**Architecture:** Vertical domain-driven slicing based on the `main-fastapi` template. Asynchronous FastAPI services with SQLAlchemy 2.0 (asyncpg), Alembic migrations, Redis sliding-window rate limiting, ARQ cron worker, and RFC 9457 error normalization.

**Tech Stack:** Python 3.13, uv, FastAPI, Pydantic v2, Pydantic-Settings, SQLAlchemy 2.0, asyncpg, Alembic, Redis, ARQ, Argon2-cffi, Docker Compose.

**Spec:** [docs/superpowers/specs/2026-10-24-backend-implementation-design.md](file:///root/projects/mini_cmms/docs/superpowers/specs/2026-10-24-backend-implementation-design.md), [docs/Mini_CMMS_OpenAPI_3.1.1.yaml](file:///root/projects/mini_cmms/docs/Mini_CMMS_OpenAPI_3.1.1.yaml), [docs/Mini_CMMS_API_Design_Notes.md](file:///root/projects/mini_cmms/docs/Mini_CMMS_API_Design_Notes.md).

## Global Constraints

- Python version: `>= 3.13` managed with `uv`.
- OpenAPI base path: `/api/v1` for business endpoints; root `/health` and `/ready` for orchestrator probes.
- Timestamps in JSON responses: strictly UTC ISO 8601 with `Z` suffix (`YYYY-MM-DDTHH:MM:SSZ` or microseconds).
- Dates: strictly `YYYY-MM-DD`.
- Local enterprise date (`local_today`): computed using `company_timezone` (`Europe/Moscow`).
- Concurrency control: strong `ETag: "<uuid>:<version>"` header on single-resource GETs; required `If-Match` header on all PATCH requests (`version >= 1`).
- Error envelope: RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, `code`, and optional `invalid_params`.
- Sessions: Opaque bearer tokens (12-hour expiry, stored as SHA-256 hashes in DB); passwords hashed with Argon2.
- Rate Limiting: 5 failed logins within 10 minutes sliding window per IP or `lower(login)` returns 429 with `Retry-After`.
- Deployment: Docker Compose orchestrates `postgres`, `redis`, `backend`, `arq-worker`, `migrate`.

## Review Focus

1. **Optimistic locking race:** two concurrent PATCH requests with identical `If-Match` must result in one succeeding (200) and one failing with 412 `VERSION_CONFLICT`.
2. **Too early work order completion:** completing a planned work order when `local_date(completed_at) + interval_days <= planned_due_on` must fail with 409 `TOO_EARLY_TO_COMPLETE`.
3. **Sole active admin protection:** blocking, deleting, or demoting the last active administrator must fail with 409 `LAST_ACTIVE_ADMIN`.
4. **Maintenance schedule non-advancing check:** updating plan interval such that `last_completed_on + interval_days <= latest_closed_planned_due_on` must fail with 409 `NON_ADVANCING_DUE_DATE` and rollback.
5. **Notification delivery idempotency:** concurrent or duplicate ARQ scheduler ticks must never create duplicate notification rows for the same `(schedule_id, planned_due_on, notification_type, recipient_id)`.

---

### Task 1: Scaffolding, uv environment, config, Dockerfile and Compose

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `backend/app/config/__init__.py`
- Create: `backend/app/config/config.py`
- Create: `backend/app/__init__.py`
- Create: `compose.yml`
- Create: `.env.example`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `app.config.settings` object exposing `app`, `db`, `redis`, `security` settings.

- [ ] **Step 1: Write failing test for config and environment variables**

```python
# backend/tests/test_config.py
def test_settings_load_defaults():
    from app.config.config import Settings
    settings = Settings()
    assert settings.app.SERVICE_NAME == "Mini-CMMS"
    assert settings.app.COMPANY_TIMEZONE == "Europe/Moscow"
    assert "postgresql+asyncpg://" in str(settings.db.DSN)
    assert settings.security.TOKEN_EXPIRE_HOURS == 12
    assert settings.security.RATE_LIMIT_MAX_ATTEMPTS == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config.py`
Expected: FAIL with ModuleNotFoundError: No module named 'app'

- [ ] **Step 3: Implement `backend/pyproject.toml`, `config.py`, `compose.yml` and `Dockerfile`**

Create `backend/pyproject.toml` with dependencies (`fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `redis`, `arq`, `argon2-cffi`, `structlog`). Create `app/config/config.py` defining Pydantic Settings classes. Create root `compose.yml` configuring `postgres`, `redis`, `backend`, `arq-worker`, `migrate`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add compose.yml .env.example backend/
git commit -m "feat(infra): add project scaffolding, settings, dockerfile and compose"
```

---

### Task 2: Database engine, async session manager and Base model

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/alembic/alembic.ini`
- Create: `backend/app/db/alembic/env.py`
- Create: `backend/app/db/alembic/script.py.mako`
- Test: `backend/tests/test_db_session.py`

**Interfaces:**
- Consumes: `app.config.settings`
- Produces: `app.db.base.Base`, `app.db.base.TimestampMixin`, `app.db.base.VersionMixin`, `app.db.session.get_session()`

- [ ] **Step 1: Write failing test for async DB session and base mixins**

```python
# backend/tests/test_db_session.py
import pytest
from sqlalchemy import Column, Integer, String
from app.db.base import Base, TimestampMixin, VersionMixin

class DummyModel(Base, TimestampMixin, VersionMixin):
    __tablename__ = "dummy_model"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)

def test_model_mixins():
    instance = DummyModel(id=1, name="test")
    assert instance.version == 1
    assert hasattr(instance, "created_at")
    assert hasattr(instance, "updated_at")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_db_session.py`
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 3: Implement `app/db/base.py`, `app/db/session.py` and initialize Alembic**

Implement declarative base with UTC datetime columns and version default = 1. Implement async session maker pool with connection arguments (`statement_cache_size=0`, `timezone="UTC"`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_db_session.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/ backend/tests/test_db_session.py
git commit -m "feat(db): implement async session manager, base models and alembic setup"
```

---

### Task 3: RFC 9457 ProblemDetail error handling and System Endpoints

**Files:**
- Create: `backend/app/errors/__init__.py`
- Create: `backend/app/errors/exceptions.py`
- Create: `backend/app/errors/handlers.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/api/v1/system.py`
- Create: `backend/app/__main__.py`
- Test: `backend/tests/test_system_and_errors.py`

**Interfaces:**
- Produces: `app.__main__.app`, `app.errors.exceptions.AppException`, `GET /health`, `GET /ready`.

- [ ] **Step 1: Write failing test for RFC 9457 error format, /health and /ready**

```python
# backend/tests/test_system_and_errors.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.__main__:app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_rfc_9457_error_handler():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/nonexistent")
        assert res.status_code == 404
        assert res.headers["content-type"] == "application/problem+json"
        data = res.json()
        assert data["status"] == 404
        assert "type" in data
        assert "code" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_system_and_errors.py`
Expected: FAIL

- [ ] **Step 3: Implement exceptions, error handlers, system endpoints and FastAPI app factory**

In `app/errors/handlers.py`, register handlers for `RequestValidationError`, `HTTPException`, `AppException`, returning `application/problem+json` matching RFC 9457. In `app/api/v1/system.py`, implement `GET /health` (always 200 if server responds) and `GET /ready` (200 if PG & Redis alive, otherwise 503).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_system_and_errors.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/errors/ backend/app/schemas/common.py backend/app/api/v1/system.py backend/app/__main__.py backend/tests/test_system_and_errors.py
git commit -m "feat(api): implement RFC 9457 error handlers and /health, /ready endpoints"
```

---

### Task 4: User & Session models, Alembic migration, Argon2 password hasher and Opaque token generator

**Files:**
- Create: `backend/app/db/models/user.py`
- Create: `backend/app/db/models/session.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/db/alembic/versions/001_initial_users_and_sessions.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `app.core.security.hash_password(raw: str) -> str`, `verify_password(raw: str, hash: str) -> bool`, `create_opaque_token() -> tuple[str, str]` (raw_token, sha256_hash).

- [ ] **Step 1: Write failing test for password hashing and opaque token generator**

```python
# backend/tests/test_security.py
from app.core.security import hash_password, verify_password, create_opaque_token

def test_argon2_hashing():
    pwd = "SecretPass123!"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPass", h) is False

def test_opaque_token_generation():
    token, token_hash = create_opaque_token()
    assert len(token) >= 32
    assert len(token_hash) == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_security.py`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `app/core/security.py`, `User`, `UserSession` models and initial Alembic migration**

Use `argon2.PasswordHasher` in `app/core/security.py`. In `User` model, enforce `UNIQUE(lower(login))`, `role in (ADMIN, ENGINEER, TECHNICIAN, OPERATOR)`, `status in (ACTIVE, BLOCKED)`. In `UserSession`, store `token_hash`, `expires_at`, `revoked_at`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_security.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/app/db/models/ backend/app/db/alembic/versions/ backend/tests/test_security.py
git commit -m "feat(auth): implement user models, argon2 hashing and token generation"
```

---

### Task 5: Redis sliding-window Rate Limiter

**Files:**
- Create: `backend/app/core/rate_limiter.py`
- Test: `backend/tests/test_rate_limiter.py`

**Interfaces:**
- Produces: `app.core.rate_limiter.record_failed_attempt(redis, key: str) -> None`, `check_rate_limit(redis, key: str) -> int | None` (returns retry_after in seconds if limited).

- [ ] **Step 1: Write failing test for sliding window rate limiter**

```python
# backend/tests/test_rate_limiter.py
import pytest
import fakeredis.aioredis
from app.core.rate_limiter import record_failed_attempt, check_rate_limit

@pytest.mark.asyncio
async def test_rate_limiter_blocks_on_sixth_attempt():
    r = fakeredis.aioredis.FakeRedis()
    key = "test_ip:127.0.0.1"
    for _ in range(5):
        assert await check_rate_limit(r, key) is None
        await record_failed_attempt(r, key)
    retry_after = await check_rate_limit(r, key)
    assert retry_after is not None
    assert 0 < retry_after <= 600
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_rate_limiter.py`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement sliding window rate limiter in `app/core/rate_limiter.py`**

Use Redis `zadd`, `zremrangebyscore`, `zcard` to track timestamp of failed login attempts over 600 seconds. If attempts >= 5, compute `Retry-After = 600 - (now - oldest_attempt_in_window)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_rate_limiter.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rate_limiter.py backend/tests/test_rate_limiter.py
git commit -m "feat(security): implement Redis sliding window rate limiter"
```

---

### Task 6: Auth endpoints (`/login`, `/logout`, `/me`) and Current User dependency

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/dependencies.py`
- Create: `backend/app/api/v1/auth.py`
- Modify: `backend/app/__main__.py:40-60`
- Test: `backend/tests/test_auth_api.py`

**Interfaces:**
- Consumes: `app.core.security`, `app.core.rate_limiter`, `app.db.session`
- Produces: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, `app.api.dependencies.get_current_user`.

- [ ] **Step 1: Write failing test for login, logout, me and rate limit**

```python
# backend/tests/test_auth_api.py
import pytest

@pytest.mark.asyncio
async def test_login_success_and_logout(async_client, db_session, test_user):
    # Login
    res = await async_client.post("/api/v1/auth/login", json={"login": "admin", "password": "Password123!"})
    assert res.status_code == 200
    token = res.json()["token"]
    
    # Get Me
    me_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["login"] == "admin"
    
    # Logout
    logout_res = await async_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 204
    
    # Check revoked
    revoked_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_res.status_code == 401
    assert "Bearer" in revoked_res.headers.get("WWW-Authenticate", "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_auth_api.py`
Expected: FAIL

- [ ] **Step 3: Implement Auth schemas, service, dependencies, and API endpoints**

Implement `POST /api/v1/auth/login` (checks credentials, checks rate limit, updates rate limiter on 401, issues 12h opaque token). Implement `POST /api/v1/auth/logout` (revokes token, returns 204). Implement `GET /api/v1/auth/me` (returns CurrentUser).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_auth_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/services/auth_service.py backend/app/api/dependencies.py backend/app/api/v1/auth.py backend/tests/test_auth_api.py
git commit -m "feat(auth): implement /login, /logout, /me endpoints and auth dependencies"
```

---

### Task 7: Users Management API and Last Active Admin Protection

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/services/user_service.py`
- Create: `backend/app/api/v1/users.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_users_api.py`

**Interfaces:**
- Consumes: `app.api.dependencies.require_role("ADMIN")`, `app.db.models.user.User`
- Produces: `GET /api/v1/users`, `POST /api/v1/users`, `GET /api/v1/users/{id}`, `PATCH /api/v1/users/{id}`, `POST /api/v1/users/{id}/password`, `POST /api/v1/users/{id}/status`.

- [ ] **Step 1: Write failing test for user creation, ETag check, and last admin protection**

```python
# backend/tests/test_users_api.py
import pytest

@pytest.mark.asyncio
async def test_cannot_demote_or_block_last_admin(admin_client, db_session, admin_user):
    res = await admin_client.post(f"/api/v1/users/{admin_user.id}/status", json={"status": "BLOCKED"})
    assert res.status_code == 409
    assert res.json()["code"] == "LAST_ACTIVE_ADMIN"

@pytest.mark.asyncio
async def test_user_patch_requires_if_match(admin_client, db_session, test_technician):
    res = await admin_client.patch(f"/api/v1/users/{test_technician.id}", json={"full_name": "New Name"})
    assert res.status_code == 428
    assert res.json()["code"] == "PRECONDITION_REQUIRED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_users_api.py`
Expected: FAIL

- [ ] **Step 3: Implement Users schemas, service and router**

Implement `GET`, `POST`, `PATCH`, `/password`, `/status`. Check `If-Match` with `ETag: "<uuid>:<version>"`. When changing role or blocking, check that count of active admins remains >= 1 with `SELECT COUNT(*) FROM users WHERE role='ADMIN' AND status='ACTIVE' FOR UPDATE`. Invalidate all sessions of user when password changes or status set to BLOCKED.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_users_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/user.py backend/app/services/user_service.py backend/app/api/v1/users.py backend/tests/test_users_api.py
git commit -m "feat(users): implement users CRUD, password/status management and admin protection"
```

---

### Task 8: Equipment models, migrations, CRUD and Archive/Restore lifecycle

**Files:**
- Create: `backend/app/db/models/equipment.py`
- Create: `backend/app/schemas/equipment.py`
- Create: `backend/app/services/equipment_service.py`
- Create: `backend/app/api/v1/equipment.py`
- Create: `backend/app/db/alembic/versions/002_equipment_table.py`
- Test: `backend/tests/test_equipment_api.py`

**Interfaces:**
- Produces: `GET /api/v1/equipment`, `POST /api/v1/equipment`, `GET /api/v1/equipment/{id}`, `PATCH /api/v1/equipment/{id}`, `POST /api/v1/equipment/{id}/archive`, `POST /api/v1/equipment/{id}/restore`.

- [ ] **Step 1: Write failing test for Equipment CRUD, search `q`, archive and restore**

```python
# backend/tests/test_equipment_api.py
import pytest

@pytest.mark.asyncio
async def test_equipment_lifecycle(engineer_client):
    # Create
    res = await engineer_client.post("/api/v1/equipment", json={
        "name": "Lathe Machine",
        "inventory_number": "EQ-001",
        "category": "Machining",
        "location": "Shop Floor 1",
        "commissioned_on": "2026-01-01"
    })
    assert res.status_code == 201
    eq = res.json()
    eq_id = eq["id"]
    etag = res.headers["ETag"]
    
    # Substring search q
    q_res = await engineer_client.get("/api/v1/equipment?q=lathe")
    assert q_res.status_code == 200
    assert q_res.json()["total"] >= 1
    
    # Archive
    arc_res = await engineer_client.post(f"/api/v1/equipment/{eq_id}/archive")
    assert arc_res.status_code == 200
    assert arc_res.json()["archived_at"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_equipment_api.py`
Expected: FAIL

- [ ] **Step 3: Implement Equipment model, migration, Pydantic schemas and endpoints**

Enforce unique inventory_number (case-sensitive exact match, trimmed). Enforce status enum `OPERATIONAL`, `UNDER_REPAIR`, `OUT_OF_SERVICE`. Support filtering: `category`, `location`, `status`, `is_archived`, `commissioned_from`, `commissioned_to`, and case-insensitive substring search `q` across `name` and `inventory_number`. Prevent archive if there are active work orders.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_equipment_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models/equipment.py backend/app/schemas/equipment.py backend/app/services/equipment_service.py backend/app/api/v1/equipment.py backend/app/db/alembic/versions/ backend/tests/test_equipment_api.py
git commit -m "feat(equipment): implement equipment management, filters, and archive lifecycle"
```

---

### Task 9: Fault models, migrations, CRUD and linking rules

**Files:**
- Create: `backend/app/db/models/fault.py`
- Create: `backend/app/schemas/fault.py`
- Create: `backend/app/services/fault_service.py`
- Create: `backend/app/api/v1/faults.py`
- Create: `backend/app/db/alembic/versions/003_faults_table.py`
- Test: `backend/tests/test_faults_api.py`

**Interfaces:**
- Consumes: `Equipment`, `User`
- Produces: `GET /api/v1/faults`, `POST /api/v1/faults`, `GET /api/v1/faults/{id}`, `PATCH /api/v1/faults/{id}`.

- [ ] **Step 1: Write failing test for Fault creation and editing constraints**

```python
# backend/tests/test_faults_api.py
import pytest

@pytest.mark.asyncio
async def test_fault_create_and_operator_edit(operator_client, test_equipment):
    # Create fault
    res = await operator_client.post("/api/v1/faults", json={
        "equipment_id": str(test_equipment.id),
        "description": "Vibration in spindle motor",
        "detected_on": "2026-10-24"
    })
    assert res.status_code == 201
    f_data = res.json()
    assert f_data["status"] == "OPEN"
    etag = res.headers["ETag"]
    
    # Edit fault while OPEN
    patch_res = await operator_client.patch(
        f"/api/v1/faults/{f_data['id']}",
        headers={"If-Match": etag},
        json={"description": "High vibration in spindle motor bearing"}
    )
    assert patch_res.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_faults_api.py`
Expected: FAIL

- [ ] **Step 3: Implement Fault model, migration, schemas, services and router**

Fault statuses: `OPEN`, `IN_PROGRESS`, `RESOLVED`. Only OPERATOR (author) or ENGINEER can edit an OPEN fault with no active work order. Detected_on cannot be in future (`> local_today`). Substring `q` searches `description` case-insensitively.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_faults_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models/fault.py backend/app/schemas/fault.py backend/app/services/fault_service.py backend/app/api/v1/faults.py backend/app/db/alembic/versions/ backend/tests/test_faults_api.py
git commit -m "feat(faults): implement faults registration, editing and filters"
```

---

### Task 10: Maintenance Plans & Maintenance Schedules models, migrations and CRUD

**Files:**
- Create: `backend/app/db/models/maintenance_plan.py`
- Create: `backend/app/db/models/maintenance_schedule.py`
- Create: `backend/app/schemas/maintenance.py`
- Create: `backend/app/services/maintenance_service.py`
- Create: `backend/app/api/v1/maintenance_plans.py`
- Create: `backend/app/api/v1/maintenance_schedules.py`
- Create: `backend/app/db/alembic/versions/004_maintenance_tables.py`
- Test: `backend/tests/test_maintenance_api.py`

**Interfaces:**
- Consumes: `Equipment`
- Produces: `GET /api/v1/maintenance-plans`, `POST /api/v1/maintenance-plans`, `GET /api/v1/maintenance-plans/{id}`, `PATCH /api/v1/maintenance-plans/{id}`, `GET /api/v1/maintenance-schedules`, `GET /api/v1/maintenance-schedules/{id}`.

- [ ] **Step 1: Write failing test for MaintenancePlan creation and automatic schedule generation**

```python
# backend/tests/test_maintenance_api.py
import pytest

@pytest.mark.asyncio
async def test_create_plan_creates_schedules(engineer_client, test_equipment):
    res = await engineer_client.post("/api/v1/maintenance-plans", json={
        "name": "Monthly Inspection",
        "scope": "EQUIPMENT",
        "equipment_id": str(test_equipment.id),
        "interval_days": 30,
        "first_due_on": "2026-11-01",
        "checklist": [
            {"order": 1, "description": "Check oil level", "is_required": True}
        ]
    })
    assert res.status_code == 201
    plan = res.json()
    
    # Check schedule created
    sched_res = await engineer_client.get(f"/api/v1/maintenance-schedules?plan_id={plan['id']}")
    assert sched_res.status_code == 200
    items = sched_res.json()["items"]
    assert len(items) == 1
    assert items[0]["equipment_id"] == str(test_equipment.id)
    assert items[0]["next_due_on"] == "2026-11-01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_maintenance_api.py`
Expected: FAIL

- [ ] **Step 3: Implement MaintenancePlan and MaintenanceSchedule models, schemas and services**

Implement unique constraint `UNIQUE(plan_id, equipment_id)` across time. Support scope `EQUIPMENT` (with equipment_id) and `CATEGORY` (with category). Validate checklist items have unique orders and descriptions after whitespace normalization. Atomically create schedules on plan creation with `next_due_on = max(first_due_on, local_today)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_maintenance_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models/maintenance* backend/app/schemas/maintenance.py backend/app/services/maintenance_service.py backend/app/api/v1/maintenance* backend/app/db/alembic/versions/ backend/tests/test_maintenance_api.py
git commit -m "feat(maintenance): implement plans, checklist templates, and schedule generation"
```

---

### Task 11: Schedule synchronization, interval updates and non-advancing check

**Files:**
- Modify: `backend/app/services/maintenance_service.py`
- Modify: `backend/app/api/v1/maintenance_plans.py`
- Test: `backend/tests/test_schedule_recalculation.py`

**Interfaces:**
- Produces: `MaintenanceService.update_plan_interval` with `NON_ADVANCING_DUE_DATE` validation.

- [ ] **Step 1: Write failing test for interval change and non-advancing due date rejection**

```python
# backend/tests/test_schedule_recalculation.py
import pytest

@pytest.mark.asyncio
async def test_interval_update_rejects_non_advancing(engineer_client, plan_with_closed_order):
    plan_id, etag = plan_with_closed_order
    # Attempt interval change that would compute next_due_on <= last closed planned_due_on
    res = await engineer_client.patch(
        f"/api/v1/maintenance-plans/{plan_id}",
        headers={"If-Match": etag},
        json={"interval_days": 1}
    )
    assert res.status_code == 409
    assert res.json()["code"] == "NON_ADVANCING_DUE_DATE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_schedule_recalculation.py`
Expected: FAIL

- [ ] **Step 3: Implement schedule update logic in `MaintenanceService`**

When `interval_days` changes on a plan, recalculate `next_due_on = last_completed_on + new_interval` for schedules where `last_completed_on is not None`. Check `next_due_on > max(closed_planned_due_on)`; raise `AppException(409, "NON_ADVANCING_DUE_DATE")` if violated.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_schedule_recalculation.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/maintenance_service.py backend/tests/test_schedule_recalculation.py
git commit -m "feat(maintenance): add schedule recalculation and non-advancing date check"
```

---

### Task 12: Work Orders, Checklists, Events and History models & migrations

**Files:**
- Create: `backend/app/db/models/work_order.py`
- Create: `backend/app/db/models/work_order_event.py`
- Create: `backend/app/db/models/work_history.py`
- Create: `backend/app/schemas/work_order.py`
- Create: `backend/app/db/alembic/versions/005_work_orders_tables.py`
- Test: `backend/tests/test_work_order_models.py`

**Interfaces:**
- Produces: `WorkOrder`, `WorkChecklistItem`, `WorkOrderEvent`, `WorkHistory` models.

- [ ] **Step 1: Write failing test for Work Order models and constraints**

```python
# backend/tests/test_work_order_models.py
from app.db.models.work_order import WorkOrder
from app.db.models.work_order_event import WorkOrderEvent
from app.db.models.work_history import WorkHistory

def test_work_order_enums():
    wo = WorkOrder(type="REPAIR", status="CREATED", number="WO-0001", title="Fix pump")
    assert wo.version == 1
    assert wo.status == "CREATED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_work_order_models.py`
Expected: FAIL

- [ ] **Step 3: Implement WorkOrder, WorkChecklistItem, WorkOrderEvent, WorkHistory models and migration**

Include columns: `number` (sequential unique string), `type` (REPAIR, PLANNED), `status` (CREATED, ASSIGNED, IN_PROGRESS, COMPLETED, CLOSED, CANCELLED), `equipment_id`, `fault_id`, `schedule_id`, `assignee_id`, `author_id`, `planned_due_on`, `result`, `cancelled_reason`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_work_order_models.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models/work* backend/app/schemas/work_order.py backend/app/db/alembic/versions/ backend/tests/test_work_order_models.py
git commit -m "feat(work_orders): define work order models, checklist items, events, and history"
```

---

### Task 13: Work Order creation, snapshot copying and validation

**Files:**
- Create: `backend/app/services/work_order_service.py`
- Create: `backend/app/api/v1/work_orders.py`
- Test: `backend/tests/test_work_order_create.py`

**Interfaces:**
- Produces: `POST /api/v1/work-orders`, `GET /api/v1/work-orders/{id}`.

- [ ] **Step 1: Write failing test for creating REPAIR and PLANNED work orders**

```python
# backend/tests/test_work_order_create.py
import pytest

@pytest.mark.asyncio
async def test_create_planned_work_order_snapshots_checklist(engineer_client, test_schedule):
    res = await engineer_client.post("/api/v1/work-orders", json={
        "type": "PLANNED",
        "schedule_id": str(test_schedule.id),
        "title": "Monthly Pump Inspection"
    })
    assert res.status_code == 201
    wo = res.json()
    assert wo["type"] == "PLANNED"
    assert len(wo["checklist"]) > 0
    assert wo["checklist"][0]["is_checked"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_work_order_create.py`
Expected: FAIL

- [ ] **Step 3: Implement work order creation in `WorkOrderService`**

For REPAIR: reject `schedule_id`, accept optional `fault_id`, ensure no other active REPAIR exists for the same fault. For PLANNED: require `schedule_id`, copy `planned_due_on` from schedule under lock, snapshot plan checklist items into `work_checklist_items`, ensure no other active PLANNED order exists for the same schedule. Generate sequential work order number.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_work_order_create.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/work_order_service.py backend/app/api/v1/work_orders.py backend/tests/test_work_order_create.py
git commit -m "feat(work_orders): implement work order creation and checklist snapshotting"
```

---

### Task 14: Work Order FSM commands: assign, reassign, start, checklist item patch, cancel

**Files:**
- Modify: `backend/app/services/work_order_service.py`
- Modify: `backend/app/api/v1/work_orders.py`
- Test: `backend/tests/test_work_order_lifecycle.py`

**Interfaces:**
- Produces: `POST .../{id}/assign`, `POST .../{id}/reassign`, `POST .../{id}/start`, `PATCH .../{id}/checklist/{item_id}`, `POST .../{id}/cancel`.

- [ ] **Step 1: Write failing test for work order state transitions and checklist item marking**

```python
# backend/tests/test_work_order_lifecycle.py
import pytest

@pytest.mark.asyncio
async def test_work_order_fsm_assign_start_and_checklist(engineer_client, technician_client, created_work_order, test_technician):
    wo_id = created_work_order["id"]
    # Assign
    res = await engineer_client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assignee_id": str(test_technician.id)})
    assert res.status_code == 200
    assert res.json()["status"] == "ASSIGNED"
    
    # Start
    start_res = await technician_client.post(f"/api/v1/work-orders/{wo_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "IN_PROGRESS"
    etag = start_res.headers["ETag"]
    
    # Checklist patch
    item_id = start_res.json()["checklist"][0]["id"]
    chk_res = await technician_client.patch(
        f"/api/v1/work-orders/{wo_id}/checklist/{item_id}",
        headers={"If-Match": etag},
        json={"is_checked": True, "comment": "Checked and verified"}
    )
    assert chk_res.status_code == 200
    assert chk_res.json()["is_checked"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_work_order_lifecycle.py`
Expected: FAIL

- [ ] **Step 3: Implement state transitions and event logging**

Enforce role permissions: only ENGINEER can assign/reassign/cancel; only assigned TECHNICIAN can start and edit checklist. Append row to `work_order_events` on each transition. When cancelling, set `cancelled_at`, `cancelled_by`, and `cancelled_reason`. Check parent work order ETag on checklist item patch and atomically bump work order version.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_work_order_lifecycle.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/work_order_service.py backend/app/api/v1/work_orders.py backend/tests/test_work_order_lifecycle.py
git commit -m "feat(work_orders): implement assign, reassign, start, cancel and checklist updates"
```

---

### Task 15: Work Order complete and close commands with schedule advancement

**Files:**
- Modify: `backend/app/services/work_order_service.py`
- Modify: `backend/app/api/v1/work_orders.py`
- Create: `backend/app/api/v1/work_history.py`
- Test: `backend/tests/test_work_order_complete_close.py`

**Interfaces:**
- Produces: `POST .../{id}/complete`, `POST .../{id}/close`, `GET /api/v1/work-history`, `GET /api/v1/work-history/{id}`.

- [ ] **Step 1: Write failing test for complete (with early check), close and history creation**

```python
# backend/tests/test_work_order_complete_close.py
import pytest

@pytest.mark.asyncio
async def test_complete_and_close_lifecycle(technician_client, engineer_client, in_progress_work_order):
    wo_id = in_progress_work_order["id"]
    # Complete
    res = await technician_client.post(f"/api/v1/work-orders/{wo_id}/complete", json={
        "result": "Pump seals replaced successfully"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"
    
    # Close
    close_res = await engineer_client.post(f"/api/v1/work-orders/{wo_id}/close")
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"
    
    # Check WorkHistory
    hist_res = await engineer_client.get(f"/api/v1/work-history?work_order_id={wo_id}")
    assert hist_res.status_code == 200
    assert hist_res.json()["total"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_work_order_complete_close.py`
Expected: FAIL

- [ ] **Step 3: Implement complete, close and history logging**

In `complete`: verify all `is_required` checklist items are checked; for PLANNED, verify `local_date(completed_at) + interval_days > planned_due_on` (or raise 409 `TOO_EARLY_TO_COMPLETE`). In `close`: create immutable `WorkHistory` snapshot, update Fault to `RESOLVED` (if REPAIR), or advance `MaintenanceSchedule` (`last_completed_on = local_date(completed_at)`, `next_due_on = last_completed_on + interval_days`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_work_order_complete_close.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/work_order_service.py backend/app/api/v1/work_orders.py backend/app/api/v1/work_history.py backend/tests/test_work_order_complete_close.py
git commit -m "feat(work_orders): implement complete, close, and work history creation"
```

---

### Task 16: Work Orders and History listing, search `q`, and sorting

**Files:**
- Modify: `backend/app/api/v1/work_orders.py`
- Modify: `backend/app/api/v1/work_history.py`
- Test: `backend/tests/test_work_order_search_sort.py`

**Interfaces:**
- Produces: `GET /api/v1/work-orders` with `q`, `sort`, pagination, and role-based filtering.

- [ ] **Step 1: Write failing test for work order search `q` and status sort**

```python
# backend/tests/test_work_order_search_sort.py
import pytest

@pytest.mark.asyncio
async def test_work_order_sorting_and_q(engineer_client):
    # Search q across number, title, description
    res = await engineer_client.get("/api/v1/work-orders?q=inspection&sort=-status")
    assert res.status_code == 200
    items = res.json()["items"]
    # Check ordering by status
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_work_order_search_sort.py`
Expected: FAIL

- [ ] **Step 3: Implement multi-field substring search and custom status ordering**

In `list_work_orders`: support `q` matching `number`, `title`, or `description` (case-insensitive substring). Implement sorting by `status`: order `CREATED, ASSIGNED, IN_PROGRESS, COMPLETED, CLOSED, CANCELLED`, secondary `created_at DESC`, tertiary `id DESC`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_work_order_search_sort.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/work_orders.py backend/app/api/v1/work_history.py backend/tests/test_work_order_search_sort.py
git commit -m "feat(work_orders): implement multi-field search and custom status sorting"
```

---

### Task 17: Notification model, migrations and API

**Files:**
- Create: `backend/app/db/models/notification.py`
- Create: `backend/app/schemas/notification.py`
- Create: `backend/app/services/notification_service.py`
- Create: `backend/app/api/v1/notifications.py`
- Create: `backend/app/db/alembic/versions/006_notifications_table.py`
- Test: `backend/tests/test_notifications_api.py`

**Interfaces:**
- Produces: `GET /api/v1/notifications`, `GET /api/v1/notifications/{id}`.

- [ ] **Step 1: Write failing test for notifications listing and recipient isolation**

```python
# backend/tests/test_notifications_api.py
import pytest

@pytest.mark.asyncio
async def test_notifications_recipient_isolation(technician_client, engineer_client, dummy_notification):
    # Only recipient can view their notification
    res = await technician_client.get("/api/v1/notifications")
    assert res.status_code == 200
    assert all(n["recipient_id"] == str(technician_client.user_id) for n in res.json()["items"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_notifications_api.py`
Expected: FAIL

- [ ] **Step 3: Implement Notification model and API**

Model columns: `id`, `recipient_id`, `schedule_id`, `planned_due_on`, `type` (`THREE_DAYS_BEFORE`, `ON_DUE_DATE`), `title`, `message`, `created_at`. Unique index `UNIQUE(schedule_id, planned_due_on, type, recipient_id)`. GET requests never modify state or mark as read.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_notifications_api.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models/notification.py backend/app/schemas/notification.py backend/app/services/notification_service.py backend/app/api/v1/notifications.py backend/app/db/alembic/versions/ backend/tests/test_notifications_api.py
git commit -m "feat(notifications): implement notification models and isolated listing"
```

---

### Task 18: ARQ worker cron job: maintenance schedule scan and idempotent notification generation

**Files:**
- Create: `backend/app/worker/__init__.py`
- Create: `backend/app/worker/tasks.py`
- Create: `backend/app/worker/main.py`
- Test: `backend/tests/test_arq_tasks.py`

**Interfaces:**
- Produces: `app.worker.tasks.generate_maintenance_notifications(ctx)`.

- [ ] **Step 1: Write failing test for ARQ schedule notification task**

```python
# backend/tests/test_arq_tasks.py
import pytest
from app.worker.tasks import generate_maintenance_notifications

@pytest.mark.asyncio
async def test_arq_notification_generation(db_session, test_schedule_due_soon):
    ctx = {"session_maker": db_session}
    created_count = await generate_maintenance_notifications(ctx)
    assert created_count > 0
    # Duplicate run must be idempotent
    second_count = await generate_maintenance_notifications(ctx)
    assert second_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_arq_tasks.py`
Expected: FAIL

- [ ] **Step 3: Implement ARQ WorkerSettings and notification generation task**

Query all `active=True` schedules without completed work order for current period. If `next_due_on - local_today in (1, 2, 3)`, type is `THREE_DAYS_BEFORE`. If `next_due_on <= local_today`, type is `ON_DUE_DATE`. Insert notification for all active engineers and assigned technician with `ON CONFLICT DO NOTHING`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_arq_tasks.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/worker/ backend/tests/test_arq_tasks.py
git commit -m "feat(worker): implement ARQ cron task for idempotent maintenance reminders"
```

---

### Task 19: End-to-end integration and OpenAPI conformance validation

**Files:**
- Create: `backend/tests/test_e2e_contract.py`
- Test: `backend/tests/test_e2e_contract.py`

**Interfaces:**
- Consumes: All API endpoints, `docs/Mini_CMMS_API_Test_Cases.csv`, `docs/Mini_CMMS_API_Examples.yaml`.

- [ ] **Step 1: Write integration runner verifying the full acceptance flow**

```python
# backend/tests/test_e2e_contract.py
import pytest

@pytest.mark.asyncio
async def test_full_acceptance_flow(async_client):
    # Runs the 4 main acceptance flows from docs/Mini_CMMS_API_Examples.yaml
    # 1. Admin setup & users onboarding
    # 2. Equipment & Fault lifecycle
    # 3. Plan, Schedule & Planned Work Order execution
    # 4. Concurrency & error probes
    pass
```

- [ ] **Step 2: Run integration tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_e2e_contract.py`
Expected: PASS

- [ ] **Step 3: Run static validator on OpenAPI spec and acceptance artifacts**

Run: `uv run --with pyyaml --with 'jsonschema[format]' --with openapi-spec-validator python docs/Mini_CMMS_API_Validation.py`
Expected: PASS (0 errors)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_e2e_contract.py
git commit -m "test(e2e): add end-to-end contract conformance tests"
```
