from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    # Create ADMIN user
    user = User(
        login="admin.schema",
        password_hash=hash_password("admin_pass12345"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db_session.add(user)
    await db_session.flush()

    token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_login_rejects_extra_properties(async_client: AsyncClient, db_session: AsyncSession):
    """POST /auth/login with extra properties must return 422 VALIDATION_ERROR."""
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"login": "admin.schema", "password": "password12345", "extra_arg": "injected"},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_login_response_strict_conformance(async_client: AsyncClient, db_session: AsyncSession):
    """POST /auth/login success must return strictly TokenResponse schema (no legacy token, no user.full_name)."""
    user = User(
        login="login.test",
        password_hash=hash_password("password12345"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db_session.add(user)
    await db_session.commit()

    res = await async_client.post(
        "/api/v1/auth/login",
        json={"login": "login.test", "password": "password12345"},
    )
    assert res.status_code == 200
    data = res.json()
    # Contract requirements:
    assert "token" not in data, "Legacy 'token' field must not be in TokenResponse"
    assert "access_token" in data
    assert "token_type" in data
    assert "expires_at" in data
    assert "user" in data
    assert "full_name" not in data["user"], "'full_name' must not be in User schema"
    assert data["user"]["login"] == "login.test"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_user_create_rejects_extra_properties(async_client: AsyncClient, auth_headers: dict[str, str]):
    """POST /users with forbidden extra properties like full_name or random props must return 422."""
    res = await async_client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "login": "new.user",
            "password": "valid_password123",
            "role": "TECHNICIAN",
            "full_name": "Should Be Rejected",
        },
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_user_patch_rejects_role_null(async_client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession):
    """PATCH /users/{id} with explicit role: null must return 422 (role is not nullable)."""
    user = User(
        login="target.patch",
        password_hash=hash_password("password12345"),
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db_session.add(user)
    await db_session.commit()

    res = await async_client.patch(
        f"/api/v1/users/{user.id}",
        headers={**auth_headers, "If-Match": f'"{user.id}:1"'},
        json={"role": None},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("if_match_header", "expected_status", "expected_code"),
    [
        (None, 428, "PRECONDITION_REQUIRED"),
        ("unquoted-value", 422, "VALIDATION_ERROR"),
        ('W/"33333333-3333-4333-8333-333333333333:1"', 422, "VALIDATION_ERROR"),
        ("*", 422, "VALIDATION_ERROR"),
        ('"33333333-3333-4333-8333-333333333333:01"', 422, "VALIDATION_ERROR"),  # leading zero
        ('"33333333-3333-4333-8333-333333333333:+1"', 422, "VALIDATION_ERROR"),  # signed
        ('"33333333-3333-4333-8333-333333333333:0"', 422, "VALIDATION_ERROR"),   # zero version
        ('"invalid-uuid:1"', 422, "VALIDATION_ERROR"),
        ('"11111111-1111-4111-8111-111111111111:1"', 412, "VERSION_CONFLICT"),  # wrong resource UUID
    ],
)
async def test_if_match_matrix_compliance(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    if_match_header: str | None,
    expected_status: int,
    expected_code: str,
):
    """Verifies strict compliance with OpenAPI If-Match schema regex and Precondition semantics."""
    user = User(
        login="ifmatch.test",
        password_hash=hash_password("password12345"),
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db_session.add(user)
    await db_session.commit()

    headers = dict(auth_headers)
    if if_match_header is not None:
        headers["If-Match"] = if_match_header

    res = await async_client.patch(
        f"/api/v1/users/{user.id}",
        headers=headers,
        json={"status": "BLOCKED"},
    )
    assert res.status_code == expected_status
    assert res.json()["code"] == expected_code


@pytest.mark.contract
@pytest.mark.asyncio
async def test_query_params_validation_and_filtering(
    async_client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
):
    """Verifies limit, offset validation and q/location filtering."""
    # 1. limit=0 and offset=-1 must return 422
    res_limit0 = await async_client.get("/api/v1/users?limit=0", headers=auth_headers)
    assert res_limit0.status_code == 422
    assert res_limit0.json()["code"] == "VALIDATION_ERROR"

    res_offset_neg = await async_client.get("/api/v1/users?offset=-1", headers=auth_headers)
    assert res_offset_neg.status_code == 422
    assert res_offset_neg.json()["code"] == "VALIDATION_ERROR"

    # 2. users?q=... substring search
    user_alpha = User(login="search_alpha", password_hash="h", role=UserRole.OPERATOR, status=UserStatus.ACTIVE, version=1)
    user_beta = User(login="search_beta", password_hash="h", role=UserRole.OPERATOR, status=UserStatus.ACTIVE, version=1)
    db_session.add_all([user_alpha, user_beta])
    await db_session.commit()

    res_q = await async_client.get("/api/v1/users?q=alpha", headers=auth_headers)
    assert res_q.status_code == 200
    items = res_q.json()["items"]
    assert any(u["login"] == "search_alpha" for u in items)
    assert not any(u["login"] == "search_beta" for u in items)

    # 3. equipment?location=... exact search (engineer auth)
    eng_user = User(
        login="engineer.query",
        password_hash="h",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db_session.add(eng_user)
    await db_session.flush()

    token_eng, token_hash_eng = create_opaque_token()
    session_eng = UserSession(
        user_id=eng_user.id,
        token_hash=token_hash_eng,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(session_eng)

    eq1 = Equipment(
        name="Pump 1",
        inventory_number="PUMP-001",
        category="Pumps",
        location="Zone-A",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2020, 1, 1),
        version=1,
    )
    eq2 = Equipment(
        name="Pump 2",
        inventory_number="PUMP-002",
        category="Pumps",
        location="Zone-B",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2020, 1, 1),
        version=1,
    )
    db_session.add_all([eq1, eq2])
    await db_session.commit()

    eng_headers = {"Authorization": f"Bearer {token_eng}"}
    res_loc = await async_client.get("/api/v1/equipment?location=Zone-A", headers=eng_headers)
    assert res_loc.status_code == 200
    eq_items = res_loc.json()["items"]
    assert any(e["inventory_number"] == "PUMP-001" for e in eq_items)
    assert not any(e["inventory_number"] == "PUMP-002" for e in eq_items)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_work_order_whitespace_and_extra_fields(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies that whitespace-only fields and injected status in WorkOrderCreate return 422."""
    author = User(
        login="author.engineer",
        password_hash="h",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
        version=1,
    )
    tech = User(
        login="tech.executor",
        password_hash="h",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db_session.add_all([author, tech])
    await db_session.flush()

    token_eng, token_hash_eng = create_opaque_token()
    token_tech, token_hash_tech = create_opaque_token()
    session_eng = UserSession(
        user_id=author.id,
        token_hash=token_hash_eng,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    session_tech = UserSession(
        user_id=tech.id,
        token_hash=token_hash_tech,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add_all([session_eng, session_tech])

    eq = Equipment(
        name="Turbine 1",
        inventory_number="TURB-001",
        category="Turbines",
        location="Hall 1",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2020, 1, 1),
        version=1,
    )
    db_session.add(eq)
    await db_session.flush()

    wo = WorkOrder(
        number="WO-0001",
        author_id=author.id,
        assignee_id=tech.id,
        equipment_id=eq.id,
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.IN_PROGRESS,
        priority=WorkOrderPriority.NORMAL,
        title="Repair Turbine",
        description="Fix the oil leak",
        version=1,
    )
    db_session.add(wo)
    await db_session.commit()

    eng_headers = {"Authorization": f"Bearer {token_eng}"}
    tech_headers = {"Authorization": f"Bearer {token_tech}"}

    # Injected status in create -> 422
    res_injected = await async_client.post(
        "/api/v1/work-orders",
        headers=eng_headers,
        json={
            "type": "REPAIR",
            "equipment_id": str(eq.id),
            "title": "Valid Title",
            "description": "Valid Description",
            "priority": "HIGH",
            "status": "COMPLETED",  # Forbidden in create
        },
    )
    assert res_injected.status_code == 422
    assert res_injected.json()["code"] == "VALIDATION_ERROR"

    # Whitespace-only result in complete -> 422
    res_ws_result = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/complete",
        headers={**tech_headers, "If-Match": f'"{wo.id}:1"'},
        json={"result": "   ", "replaced_parts": []},
    )
    assert res_ws_result.status_code == 422
    assert res_ws_result.json()["code"] == "VALIDATION_ERROR"

    # Whitespace-only item in replaced_parts -> 422
    res_ws_parts = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/complete",
        headers={**tech_headers, "If-Match": f'"{wo.id}:1"'},
        json={"result": "Fixed properly", "replaced_parts": ["   "]},
    )
    assert res_ws_parts.status_code == 422
    assert res_ws_parts.json()["code"] == "VALIDATION_ERROR"

    # Whitespace-only cancel reason -> 422
    res_ws_cancel = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/cancel",
        headers={**eng_headers, "If-Match": f'"{wo.id}:1"'},
        json={"reason": "   "},
    )
    assert res_ws_cancel.status_code == 422
    assert res_ws_cancel.json()["code"] == "VALIDATION_ERROR"
