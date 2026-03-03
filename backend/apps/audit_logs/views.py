"""Views for the Audit Logs app."""

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ConversationLog
from .serializers import ConversationLogSerializer


@api_view(["GET"])
def history_view(request):
    """
    GET /api/audit/history/

    Returns paginated conversation history for
    the authenticated employee.
    """
    logs = ConversationLog.objects.filter(employee=request.user)
    # Manual pagination (DRF pagination works with generic views;
    # here we keep it simple for function-based views)
    page_size = 20
    page = int(request.query_params.get("page", 1))
    start = (page - 1) * page_size
    end = start + page_size

    total = logs.count()
    page_logs = logs[start:end]
    serializer = ConversationLogSerializer(page_logs, many=True)

    return Response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": serializer.data,
    })
