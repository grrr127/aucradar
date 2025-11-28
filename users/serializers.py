import re
from secrets import randbelow

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class EmailSendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return email

    def save(self, **kwargs):
        email = self.validated_data["email"]
        existing_code = cache.get(f"email_verify:{email}")

        if existing_code:
            code = existing_code
            message_suffix = "이미 발급된 인증번호를 다시 전송했습니다."
        else:
            code = f"{randbelow(1000000):06d}"
            message_suffix = "인증번호가 이메일로 전송되었습니다."

        cache.set(f"email_verify:{email}", code, timeout=600)
        send_mail(
            "[AucRadar] 이메일 인증번호 ",
            f"인증번호는 {code} 입니다. 인증번호는 10분동안 유효합니다.",
            None,
            [email],
        )

        return {"detail": message_suffix}


class EmailVerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        code = attrs["code"]
        stored_code = cache.get(f"email_verify:{email}")

        if not stored_code:
            raise serializers.ValidationError(
                "인증번호가 만료되었거나 요청되지 않았습니다."
            )
        if stored_code != code:
            raise serializers.ValidationError("인증번호가 올바르지 않습니다.")

        attrs["email"] = email
        return attrs

    def save(self):
        email = self.validated_data["email"].lower()
        cache.set(f"email_verified:{email}", True, timeout=600)
        return {"verified": True}


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "name", "password", "password2"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return email

    def validate(self, attrs):
        email = attrs["email"].lower()

        if not cache.get(f"email_verified:{email}"):
            raise serializers.ValidationError("이메일 인증이 필요합니다.")

        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        password = attrs["password"]

        if len(password) < 8:
            raise serializers.ValidationError("비밀번호는 8자 이상이어야 합니다.")

        if not re.search(r"\d", password):
            raise serializers.ValidationError("비밀번호에는 숫자가 포함되어야 합니다.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=~`/]", password):
            raise serializers.ValidationError(
                "비밀번호에는 특수문자가 포함되어야 합니다."
            )

        validate_password(password)
        attrs["email"] = email
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        email = validated_data.pop("email").lower()
        password = validated_data.pop("password")
        user = User.objects.create_user(
            email=email, password=password, **validated_data
        )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower()
        user = authenticate(email=email, password=attrs["password"])
        if not user:
            raise serializers.ValidationError(
                "이메일 또는 비밀번호가 올바르지 않습니다."
            )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            },
        }


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name"]
