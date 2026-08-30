from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class AgentAPIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        provided = request.headers.get("X-API-Key")
        if not provided:
            return None
        if provided != settings.AGENT_API_KEY:
            raise AuthenticationFailed("Invalid API key")
        return (AnonymousUser(), "agent")
