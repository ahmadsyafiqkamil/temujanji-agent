import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.auth import decode_access_token, hash_password
from backend.app.db import get_session
from backend.app.main import app
from backend.app.models import StaffRole, StaffUser


class FakeResult:
    def __init__(self, staff_user: StaffUser | None) -> None:
        self.staff_user = staff_user

    def first(self) -> StaffUser | None:
        return self.staff_user


class FakeSession:
    def __init__(self, staff_user: StaffUser) -> None:
        self.staff_user = staff_user

    async def exec(self, _statement: object) -> FakeResult:
        return FakeResult(self.staff_user)


@pytest.fixture
def admin_session_override():
    admin = StaffUser(
        id=1,
        username="admin",
        password_hash=hash_password("correct-password"),
        role=StaffRole.ADMIN,
    )

    async def override_session():
        yield FakeSession(admin)

    app.dependency_overrides[get_session] = override_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_rejects_bad_password(admin_session_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "nope"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_returns_token_with_admin_role(admin_session_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "correct-password"},
        )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert decode_access_token(response.json()["access_token"])["sub"] == "1"
