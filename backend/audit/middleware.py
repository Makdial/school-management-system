"""Lightweight middleware that records write activity for auditing."""

from .services import log_activity

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if (
                request.path.startswith("/api/")
                and request.method in AUDITED_METHODS
                and response.status_code >= 400
                and response.status_code != 401
            ):
                user = getattr(request, "user", None)
                log_activity(
                    f"{request.method} {request.path} -> {response.status_code}",
                    user=user if getattr(user, "is_authenticated", False) else None,
                    level="WARNING",
                    metadata={"status": response.status_code},
                )
        except Exception:  # pragma: no cover - never break a request over logging
            pass
        return response
