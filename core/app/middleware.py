from django.utils import timezone
from .models import TeamSession

class TeamSessionHeartbeatMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            TeamSession.objects.filter(
                session_key=request.session.session_key
            ).update(last_seen_at=timezone.now())

        return response
