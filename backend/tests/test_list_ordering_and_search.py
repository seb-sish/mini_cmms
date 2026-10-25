"""Нормативная сортировка списков и буквальный поиск."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus


@pytest.fixture
async def admin_with_users(db_session: AsyncSession) -> tuple[User, str]:
    admin = User(
        login="aaa_admin",
        password_hash=hash_password("Pass12345!"),
        full_name="Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    for login in ("zeta_user", "beta_user", "gamma_user", "under_score", "plain"):
        db_session.add(
            User(
                login=login,
                password_hash=hash_password("Pass12345!"),
                full_name=login,
                role=UserRole.OPERATOR,
                status=UserStatus.ACTIVE,
            )
        )
    await db_session.commit()
    await db_session.refresh(admin)

    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=admin.id,
            token_hash=t_hash,
            expires_at=admin.created_at.replace(year=admin.created_at.year + 1),
        )
    )
    await db_session.commit()
    return admin, raw_token


@pytest.mark.asyncio
async def test_users_are_sorted_by_login_asc(async_client: AsyncClient, admin_with_users):
    _, token = admin_with_users
    res = await async_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    logins = [item["login"] for item in res.json()["items"]]
    assert logins == sorted(logins)


@pytest.mark.asyncio
async def test_users_search_is_literal(async_client: AsyncClient, admin_with_users):
    """Символы _ и % в поиске трактуются буквально, а не как wildcard SQL."""
    _, token = admin_with_users
    # Буквальный "_a": подходит только логин, содержащий подстроку "_a".
    # Как wildcard "_a" совпал бы и с "beta_user" и другими.
    res = await async_client.get("/api/v1/users?q=_a", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["login"] == "aaa_admin"

    res = await async_client.get("/api/v1/users?q=%25", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["total"] == 0


@pytest.mark.asyncio
async def test_equipment_is_sorted_by_name_asc(async_client: AsyncClient, db_session: AsyncSession):
    from datetime import date

    engineer = User(
        login="sort_engineer",
        password_hash=hash_password("Pass12345!"),
        full_name="Sort Engineer",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(engineer)
    for name, inventory in (("Zeta Press", "EQ-SORT-1"), ("Alpha Press", "EQ-SORT-2"), ("Mid Press", "EQ-SORT-3")):
        db_session.add(
            Equipment(
                name=name,
                inventory_number=inventory,
                category="Machining",
                location="Shop",
                commissioned_on=date(2026, 1, 1),
                status=EquipmentStatus.OPERATIONAL,
            )
        )
    await db_session.commit()
    await db_session.refresh(engineer)

    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=engineer.id,
            token_hash=t_hash,
            expires_at=engineer.created_at.replace(year=engineer.created_at.year + 1),
        )
    )
    await db_session.commit()

    res = await async_client.get("/api/v1/equipment", headers={"Authorization": f"Bearer {raw_token}"})
    assert res.status_code == 200
    names = [item["name"] for item in res.json()["items"]]
    assert names == sorted(names)
    assert names == ["Alpha Press", "Mid Press", "Zeta Press"]


@pytest.mark.asyncio
async def test_equipment_search_is_literal(async_client: AsyncClient, db_session: AsyncSession):
    from datetime import date

    engineer = User(
        login="search_engineer",
        password_hash=hash_password("Pass12345!"),
        full_name="Search Engineer",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(engineer)
    db_session.add(
        Equipment(
            name="Press 100%",
            inventory_number="EQ-SEARCH-1",
            category="Machining",
            location="Shop",
            commissioned_on=date(2026, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
    )
    db_session.add(
        Equipment(
            name="Plain Press",
            inventory_number="EQ-SEARCH-2",
            category="Machining",
            location="Shop",
            commissioned_on=date(2026, 1, 1),
            status=EquipmentStatus.OPERATIONAL,
        )
    )
    await db_session.commit()
    await db_session.refresh(engineer)

    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=engineer.id,
            token_hash=t_hash,
            expires_at=engineer.created_at.replace(year=engineer.created_at.year + 1),
        )
    )
    await db_session.commit()

    res = await async_client.get("/api/v1/equipment?q=%25", headers={"Authorization": f"Bearer {raw_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Press 100%"
