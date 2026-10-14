from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def health(request):
    """Liveness/readiness probe used by docker and the frontend."""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:  # pragma: no cover - defensive
        db_ok = False
    from django.http import JsonResponse

    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok})
