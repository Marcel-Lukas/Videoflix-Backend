"""Tests for ``RefreshTokenView``."""

from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .helpers import TEST_SETTINGS, make_user


@override_settings(**TEST_SETTINGS)
class RefreshTokenViewTests(APITestCase):
    """Tests for ``POST /api/token/refresh/``."""

    url = reverse('token_refresh')

    def setUp(self):
        self.user = make_user()
        self.refresh = RefreshToken.for_user(self.user)

    def test_refresh_success_sets_new_access_cookie(self):
        self.client.cookies['refresh_token'] = str(self.refresh)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)
        self.assertTrue(response.cookies['access_token'].value)

    def test_refresh_missing_cookie(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_refresh_invalid_token(self):
        self.client.cookies['refresh_token'] = 'not-a-valid-token'

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
