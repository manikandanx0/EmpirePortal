import re
import csv
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out

from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from .models import Team
from django.utils.crypto import get_random_string
from django.contrib.sessions.models import Session
from django.utils import timezone


def normalize_username(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    return s


def append_team_credentials(team_name, username, password):
    # Persist credentials to a CSV for admins to share with teams.
    csv_path = settings.BASE_DIR / "generated_team_credentials.csv"
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        if not file_exists:
            writer.writerow(["team_name", "username", "password"])
        writer.writerow([team_name, username, password])

@receiver(post_save, sender=Team)
def create_user_for_team(sender, instance, created, **kwargs):
    if created and instance.user is None:
        username = normalize_username(instance.name)
        password = get_random_string(12)
        user = User.objects.create_user(username=username, password=password)
        instance.user = user
        instance.save(update_fields=["user"])
        append_team_credentials(instance.name, username, password)
        print(f"[Team Login Created] {username} / {password}")

@receiver(pre_save, sender=Team)
def sync_username_on_rename(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = Team.objects.get(pk=instance.pk)
    except Team.DoesNotExist:
        return

    if old.name != instance.name and instance.user:
        new_username = normalize_username(instance.name)
        instance.user.username = new_username
        instance.user.save(update_fields=["username"])

from django.contrib.sessions.models import Session
from django.utils import timezone

def cleanup_sessions():
    Session.objects.filter(expire_date__lt=timezone.now()).delete()
from .models import ZoneAttempt

@receiver(user_logged_out)
def end_active_attempt_on_logout(sender, request, user, **kwargs):
    if not hasattr(user, "team"):
        return

    attempts = ZoneAttempt.objects.filter(
        team=user.team,
        status="ACTIVE"
    )

    for attempt in attempts:
        attempt.end_attempt(status="FORCED_EXIT")

        
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Team, Score

@receiver(post_save, sender=Team)
def create_score_for_team(sender, instance, created, **kwargs):
    if created:
        Score.objects.create(team=instance)