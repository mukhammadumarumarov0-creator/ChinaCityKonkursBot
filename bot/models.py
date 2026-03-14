from django.db import models
from django.contrib.auth.models import AbstractUser
from decouple import config
import random
import string
from django.db.models import F
from asgiref.sync import sync_to_async

BOT_FULL_PATH = config("BOT_FULL_PATH")

class User(AbstractUser):
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True)
    inviter = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="invited_users")
    referral_points = models.IntegerField(default=0) 


    def get_invite_link(self):
        return f"{BOT_FULL_PATH}_{self.telegram_id}"


    def generate_username(self) -> str:
        base = f"user_{self.telegram_id}"
        if not User.objects.filter(username=base).exists():
            return base
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{base}_{rand_str}"


    def save(self, *args, **kwargs):
      if not self.username:
            self.username = self.generate_username()
      super().save(*args, **kwargs)


    async def add_referral_points_async(self, points: int = 5):
     await sync_to_async(
        User.objects.filter(pk=self.pk).update
    )(referral_points=F("referral_points") + points)

    # agar keyin self.referral_points kerak bo‘lsa
     await sync_to_async(self.refresh_from_db)()

    def __str__(self):
        return self.full_name or self.username



class LiveSession(models.Model):
    title = models.CharField(max_length=255,null=True,blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Live {self.id} - {self.title}"

    def generate_title(self) -> str:
        base = f"live_{self.pk}"
        title = base

        while LiveSession.objects.filter(title=title).exists():
            rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            title = f"{base}_{rand_str}"

        return title

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)  # First save to get a PK

        if not self.title:
            self.title = self.generate_title()
            # Update only the title to avoid recursion
            super().save(update_fields=["title"])


# ================= LIVE PARTICIPANT =================
class LiveParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    live = models.ForeignKey(LiveSession, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "live")  # Har user har live uchun faqat 1 qatnashuv

    def __str__(self):
        return f"{self.user.username} - Live {self.live.id}"







