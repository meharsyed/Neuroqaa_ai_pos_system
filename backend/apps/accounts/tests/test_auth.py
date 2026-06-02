import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="StrongPass123!",
        first_name="Admin",
        last_name="User",
        role="owner",
    )


@pytest.mark.django_db
class TestLoginEndpoint:
    def test_login_returns_tokens_and_user(self, api_client, user):
        url = reverse("auth-login")
        resp = api_client.post(url, {"email": user.email, "password": "StrongPass123!"})
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data
        assert resp.data["user"]["email"] == user.email
        assert resp.data["user"]["role"] == "owner"

    def test_login_bad_credentials(self, api_client):
        url = reverse("auth-login")
        resp = api_client.post(url, {"email": "nobody@example.com", "password": "wrong"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMeEndpoint:
    def test_me_requires_auth(self, api_client):
        url = reverse("auth-me")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_user_data(self, api_client, user):
        login = api_client.post(
            reverse("auth-login"), {"email": user.email, "password": "StrongPass123!"}
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        resp = api_client.get(reverse("auth-me"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["email"] == user.email

    def test_refresh_token_works(self, api_client, user):
        login = api_client.post(
            reverse("auth-login"), {"email": user.email, "password": "StrongPass123!"}
        )
        resp = api_client.post(reverse("auth-refresh"), {"refresh": login.data["refresh"]})
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
