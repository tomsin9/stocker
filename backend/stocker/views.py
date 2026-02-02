"""
Custom auth views (e.g. token with Cloudflare Turnstile verification).
"""
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def verify_turnstile_token(token: str) -> bool:
    """Verify Turnstile token with Cloudflare Siteverify API."""
    secret = getattr(settings, 'TURNSTILE_SECRET_KEY', None) or ''
    if not secret:
        return True  # Skip verification when secret not configured (e.g. dev)
    if not token:
        return False
    try:
        r = requests.post(
            TURNSTILE_VERIFY_URL,
            data={'secret': secret, 'response': token},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data.get('success') is True
    except Exception:
        return False


class TurnstileTokenObtainPairView(TokenObtainPairView):
    """
    JWT token obtain view that requires a valid Cloudflare Turnstile token
    when TURNSTILE_SECRET_KEY is set. Accepts username, password, and
    cf_turnstile_response in the request body.
    """

    def post(self, request, *args, **kwargs):
        secret = getattr(settings, 'TURNSTILE_SECRET_KEY', None) or ''
        if secret:
            token = (
                request.data.get('cf_turnstile_response')
                or request.data.get('cf-turnstile-response')
                or ''
            ).strip()
            if not token:
                return Response(
                    {'detail': 'Turnstile verification required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not verify_turnstile_token(token):
                return Response(
                    {'detail': 'Turnstile verification failed.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # Proceed with JWT token obtain
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
