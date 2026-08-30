import pytest
from rest_framework_simplejwt.tokens import AccessToken


@pytest.mark.django_db
def test_login_rejects_bad_password(api_client, admin_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"username": "admin", "password": "nope"},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_login_returns_token_with_admin_role(api_client, admin_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"username": "admin", "password": "correct-password"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    token = AccessToken(body["access_token"])
    assert str(token["sub"]) == str(admin_user.id)
