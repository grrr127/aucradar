from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import (
    EmailSendCodeSerializer,
    EmailVerifyCodeSerializer,
    LoginSerializer,
    MeSerializer,
    SignUpSerializer,
)


class EmailSendCodeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailSendCodeSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.save()
        return Response(data)


class EmailVerifyCodeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerifyCodeSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.save()
        return Response(data)


class SignUpView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SignUpSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
        }

        response = Response(
            {
                "detail": "회원가입이 완료되었습니다.",
                "access": access,
                "user": user_data,
            },
            status=status.HTTP_201_CREATED,
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=False if settings.DEBUG else True,
            samesite="Lax",
            max_age=60 * 60 * 24 * 7,
            path="/",
        )


class LoginView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        refresh_token = ser.validated_data["refresh"]
        access_token = ser.validated_data["access"]
        user_info = ser.validated_data["user"]

        response = Response(
            {
                "access": access_token,
                "user": user_info,
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False if settings.DEBUG else True,
            samesite="Lax",
            max_age=60 * 60 * 24 * 7,
            path="/",
        )
        return response


class CookieRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get("refresh_token")
        if not refresh_cookie:
            return Response(
                "refresh 토큰이 없습니다.", status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_cookie)
        except TokenError:
            return Response(
                "유효하지 않은 refresh 토큰입니다.", status=status.HTTP_401_UNAUTHORIZED
            )

        jti = refresh.get("jti")

        if cache.get(f"blacklist:{jti}"):
            return Response(
                "로그아웃된 토큰입니다.", status=status.HTTP_401_UNAUTHORIZED
            )

        new_access = str(refresh.access_token)

        return Response({"access": new_access}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_cookie = request.COOKIES.get("refresh_token")
        if not refresh_cookie:
            return Response(
                "refresh 토큰이 없습니다.", status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_cookie)
        except TokenError:
            response = Response("로그아웃 되었습니다.", status=status.HTTP_200_OK)
            response.delete_cookie("refresh_token")
            return response

        jti = refresh.get("jti")
        exp_timestamp = refresh.get("exp")

        ttl = exp_timestamp - int(timezone.now().timestamp())

        cache.set(f"blacklist:{jti}", True, timeout=ttl)

        response = Response("로그아웃 되었습니다.", status=status.HTTP_200_OK)
        response.delete_cookie("refresh_token")
        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
