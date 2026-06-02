from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import POSTokenObtainPairSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = POSTokenObtainPairSerializer

    @extend_schema(
        summary="Login",
        description="Returns access + refresh tokens plus the authenticated user object.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Current user", responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)
