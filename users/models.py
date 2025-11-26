from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if not password:
            raise ValueError("비밀번호는 필수입니다.")
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email=email, password=password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser는 is_staff=True여야 합니다.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser는 is_superuser=True여야 합니다.")

        return self._create_user(email=email, password=password, **extra_fields)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField("이메일주소", unique=True)
    name = models.CharField(max_length=150)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self) -> str:
        return f"{self.email} ({self.name})"


class TelegramProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_profile",
        verbose_name="유저",
    )
    chat_id = models.CharField(
        "텔레그램 chat_id",
        max_length=64,
        unique=True,
        help_text="텔레그램 봇 webhook에서 받은 chat_id",
    )
    is_active = models.BooleanField("알림 활성화 여부", default=True)

    class Meta:
        db_table = "telegram_profile"
        verbose_name = "텔레그램 프로필"
        verbose_name_plural = "텔레그램 프로필 목록"

    def __str__(self) -> str:
        return f"{self.user.name} : {self.chat_id}"
