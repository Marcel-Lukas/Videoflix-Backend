"""Serializers for the auth_app API."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()

INVALID_CREDENTIALS_MSG = 'Bitte überprüfe deine Eingaben und versuche es erneut.'
PASSWORDS_DO_NOT_MATCH_MSG = 'Passwords do not match'


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for creating a new (inactive) user account."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirmed_password'):
            raise serializers.ValidationError(
                {'confirmed_password': PASSWORDS_DO_NOT_MATCH_MSG}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirmed_password', None)
        email = validated_data['email']
        password = validated_data['password']

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False,
        )

        # Attach uid/token to the instance so the view can build the
        # activation link and enqueue the mail job.
        user.activation_uid = urlsafe_base64_encode(force_bytes(user.pk))
        user.activation_token = default_token_generator.make_token(user)

        return user


class LoginSerializer(serializers.Serializer):
    """Authenticate a user by e-mail/password and return JWT tokens."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs['email']
        password = attrs['password']

        user = User.objects.filter(email=email).first()
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'Kein Konto mit dieser E-Mail gefunden.'}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {'detail': 'Dein Konto ist nicht aktiv. Bitte aktiviere es.'}
            )

        authenticated_user = authenticate(username=email, password=password)
        if authenticated_user is None:
            raise serializers.ValidationError({'detail': INVALID_CREDENTIALS_MSG})

        refresh = RefreshToken.for_user(authenticated_user)
        self.user = authenticated_user
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset link."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a password reset and setting a new password."""

    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Die Passwörter stimmen nicht überein.'}
            )

        try:
            validate_password(attrs['new_password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})

        return attrs
    



