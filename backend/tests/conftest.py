import pytest
from rest_framework.test import APIClient

from factories import StaffUserFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_user(db):
    return StaffUserFactory(
        username="admin",
        role="admin",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def staff_user(db):
    return StaffUserFactory(role="staff")


@pytest.fixture
def admin_client(admin_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def staff_client(staff_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def agent_client(settings) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=settings.AGENT_API_KEY)
    return client
