"""Custom DRF authentication backends for the auth_app API."""

from rest_framework_simplejwt.authentication import JWTAuthentication


ACCESS_COOKIE = 'access_token'


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate users using a JWT stored in an HTTP-only cookie.

    Falls back to the default ``Authorization`` header authentication
    when no access token cookie is present.
    """

    def authenticate(self, request):
        access_token = request.COOKIES.get(ACCESS_COOKIE)
        if not access_token:
            return super().authenticate(request)

        validated_token = self.get_validated_token(access_token)
        user = self.get_user(validated_token)
        return user, validated_token
    

