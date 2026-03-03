"""Views for the Authentication app."""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .serializers import LoginSerializer, EmployeeSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/auth/login/

    Accepts employee_id + password.
    Returns an auth token on success.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    employee = authenticate(
        request,
        employee_id=serializer.validated_data["employee_id"],
        password=serializer.validated_data["password"],
    )

    if employee is None:
        return Response(
            {"error": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Create or retrieve the token for this employee
    token, _created = Token.objects.get_or_create(user=employee)

    return Response({
        "message": "Login successful.",
        "token": token.key,
        "employee": EmployeeSerializer(employee).data,
    })
