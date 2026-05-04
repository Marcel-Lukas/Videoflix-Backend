import django_rq

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from auth_app.tasks import job_send_reset_password_mail

from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)


User = get_user_model()

ACCESS_COOKIE = 'access_token'
REFRESH_COOKIE = 'refresh_token'

COOKIE_OPTIONS = {
    'httponly': True,
    'secure': True,
    'samesite': 'None',
}


def _set_auth_cookie(response, key, value):
    """Set an authentication cookie with the project-wide options."""
    response.set_cookie(key=key, value=str(value), **COOKIE_OPTIONS)


def _decode_user_from_uid(uidb64):
    """Return the user identified by ``uidb64`` or ``None`` if invalid."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
        return None


class RegisterView(APIView):
    """Register a new (inactive) user account."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        return Response(
            {
                'user': {'id': user.id, 'email': user.email},
                'token': user.activation_token,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Issue JWT tokens and store them as HTTP-only cookies."""

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data['access']
        refresh = serializer.validated_data['refresh']

        response = Response({
            'detail': 'Login successful',
            'user': {
                'id': serializer.user.id,
                'username': serializer.user.email,
            },
        })
        _set_auth_cookie(response, ACCESS_COOKIE, access)
        _set_auth_cookie(response, REFRESH_COOKIE, refresh)
        return response


class RefreshTokenView(TokenRefreshView):
    """Refresh the access token using the refresh token cookie."""

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh_token:
            return Response(
                {'error': 'Refresh token not found in cookies.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {'error': 'Refresh token invalid!.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = serializer.validated_data.get('access')

        response = Response(
            {'detail': 'Token refreshed', 'access': str(access_token)},
            status=status.HTTP_200_OK,
        )
        _set_auth_cookie(response, ACCESS_COOKIE, access_token)
        return response


class LogoutView(APIView):
    """Blacklist the refresh token and clear authentication cookies."""

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response(
            {
                'detail': (
                    'Logout successful! All tokens will be deleted. '
                    'Refresh token is now invalid.'
                )
            },
            status=status.HTTP_200_OK,
        )

        token = RefreshToken(refresh_token)
        token.blacklist()

        response.delete_cookie(ACCESS_COOKIE)
        response.delete_cookie(REFRESH_COOKIE)
        return response


class ActivateAccountView(APIView):
    """Activate a user account via the e-mailed activation link."""

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        user = _decode_user_from_uid(uidb64)
        if user is None:
            return Response(
                {'error': 'Ungültiger Link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Der Aktivierungs-Link ist ungültig oder abgelaufen.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()
        return Response(
            {'message': 'Account successfully activated.'},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """Send a password reset e-mail if a matching active user exists."""

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        user = User.objects.filter(email=email, is_active=True).first()

        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = (
                f'{settings.FRONTEND_URL}/pages/auth/confirm_password.html'
                f'?uid={uid}&token={token}'
            )
            django_rq.enqueue(job_send_reset_password_mail, user.email, reset_link)

        return Response(
            {'detail': 'An email has been sent to reset your password.'},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Validate a reset token and set the new password."""

    def post(self, request, uidb64, token):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = _decode_user_from_uid(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Der Link zur Passwortzurücksetzung ist ungültig oder abgelaufen.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'detail': 'Your Password has been successfully reset.'},
            status=status.HTTP_200_OK,
        )
        



