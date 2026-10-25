import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus


async def bootstrap_admin_core(
    session: AsyncSession,
    login: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> tuple[bool, str]:
    """
    Core logic for bootstrapping the initial administrator account.
    Safe against concurrent executions using pg_advisory_xact_lock.
    Returns (created: bool, message: str).
    """
    admin_login = (login or settings.security.FIRST_ADMIN_LOGIN or "admin").strip()
    if not admin_login:
        raise ValueError("Admin login cannot be empty.")

    admin_password = (
        password
        or settings.security.FIRST_ADMIN_PASSWORD
        or os.getenv("FIRST_ADMIN_PASSWORD")
        or os.getenv("SECURITY_FIRST_ADMIN_PASSWORD")
    )
    if not admin_password:
        raise ValueError(
            "Bootstrap admin password is not configured. Set SECURITY_FIRST_ADMIN_PASSWORD "
            "(or FIRST_ADMIN_PASSWORD) environment variable, or provide it via stdin/prompt."
        )

    if len(admin_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    # 1. Acquire transaction advisory lock on PostgreSQL to prevent races
    conn = await session.connection()
    if conn.dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(84729104)"))

    # 2. Check if a user with this login already exists
    stmt = select(User).where(func.lower(User.login) == admin_login.lower())
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is not None:
        if existing.role == UserRole.ADMIN and existing.status == UserStatus.ACTIVE:
            return False, f"Admin user '{existing.login}' already exists and is active. No action taken."
        else:
            raise RuntimeError(
                f"User '{existing.login}' already exists with role '{existing.role}' "
                f"and status '{existing.status}'. Cannot bootstrap or elevate."
            )

    # 3. Check if any ACTIVE ADMIN already exists
    active_admin_stmt = select(func.count(User.id)).where(
        User.role == UserRole.ADMIN,
        User.status == UserStatus.ACTIVE,
    )
    admin_count = (await session.execute(active_admin_stmt)).scalar_one()
    if admin_count > 0:
        return (
            False,
            f"An active administrator already exists in the system ({admin_count} active admin(s)). No action taken.",
        )

    # 4. Create first administrator
    new_admin = User(
        login=admin_login,
        password_hash=hash_password(admin_password),
        full_name=full_name or "System Administrator",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(new_admin)
    await session.commit()
    await session.refresh(new_admin)
    return True, f"Administrator '{new_admin.login}' successfully created."


async def run_bootstrap(
    login: str | None = None,
    password_stdin: bool = False,
    full_name: str | None = None,
) -> None:
    password = None
    if password_stdin:
        password = sys.stdin.read().strip()
    elif not (
        settings.security.FIRST_ADMIN_PASSWORD
        or os.getenv("FIRST_ADMIN_PASSWORD")
        or os.getenv("SECURITY_FIRST_ADMIN_PASSWORD")
    ):
        if sys.stdin.isatty():
            password = getpass.getpass("Enter administrator password: ")
            confirm = getpass.getpass("Confirm administrator password: ")
            if password != confirm:
                print("Error: Passwords do not match.", file=sys.stderr)
                sys.exit(1)

    engine = create_async_engine(str(settings.db.DSN), echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        try:
            created, msg = await bootstrap_admin_core(
                session=session,
                login=login,
                password=password,
                full_name=full_name,
            )
            print(msg)
            if not created:
                sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Mini-CMMS Administrative CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap-admin", help="Create the first administrator user")
    bootstrap_parser.add_argument("--login", default=None, help="Administrator login (defaults to config)")
    bootstrap_parser.add_argument("--full-name", default=None, help="Administrator full name")
    bootstrap_parser.add_argument(
        "--password-stdin", action="store_true", help="Read administrator password from stdin"
    )

    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        asyncio.run(
            run_bootstrap(
                login=args.login,
                password_stdin=args.password_stdin,
                full_name=args.full_name,
            )
        )


if __name__ == "__main__":
    main()
