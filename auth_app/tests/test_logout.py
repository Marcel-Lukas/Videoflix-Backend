"""Tests for ``LogoutView``."""

from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from .helpers import TEST_SETTINGS, make_user


@override_settings(**TEST_SETTINGS)
class LogoutViewTests(APITestCase):
    """Tests for ``POST /api/logout/``."""

    url = reverse('logout')

    def setUp(self):
        self.user = make_user()
        self.refresh = RefreshToken.for_user(self.user)

    @patch('auth_app.api.views.RefreshToken')
    def test_logout_success_clears_cookies(self, mocked_refresh_token):
        self.client.cookies['refresh_token'] = str(self.refresh)
        self.client.cookies['access_token'] = str(self.refresh.access_token)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_refresh_token.return_value.blacklist.assert_called_once()
        # Cookies are cleared by setting them to an empty value with max-age=0.
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')

    def test_logout_blacklists_refresh_token(self):
        self.client.cookies['refresh_token'] = str(self.refresh)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_logout_missing_refresh_cookie_returns_400(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
