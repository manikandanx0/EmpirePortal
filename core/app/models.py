from django.db import models
from django.contrib.auth.models import User
import uuid
from django.conf import settings
from django.utils import timezone

from django.db import models
from django.contrib.auth.models import User


# -------------------------
# TEAM
# -------------------------
class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="team",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# -------------------------
# PLAYER
# -------------------------
class Player(models.Model):
    ROLE_CHOICES = [
        ("INTERN", "Intern"),
        ("JUNIOR_ANALYST", "Junior Analyst"),
        ("TEAM_LEADER", "Team Leader"),
        ("MANAGER", "Manager"),
        ("CEO", "CEO"),
    ]

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="players")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "role")  # one role per team

    def __str__(self):
        return f"{self.name} ({self.role}) - {self.team.name}"


# -------------------------
# TEAM SESSION (optional, team login tracking)
# -------------------------
class TeamSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_sessions")
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.session_key}"


# -------------------------
# ZONE
# -------------------------
class Zone(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


# -------------------------
# ZONE ATTEMPT ACCESS (per player, per zone code)
# -------------------------
class ZoneAttemptAccess(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="access_codes")
    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="zone_access_codes")
    player = models.ForeignKey("Player", on_delete=models.CASCADE, related_name="zone_access_codes")

    attempt_code = models.CharField(max_length=20, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("player", "zone")
        indexes = [
            models.Index(fields=["attempt_code"]),
            models.Index(fields=["zone"]),
        ]

    def __str__(self):
        return f"{self.team.name} - {self.zone.title} - {self.player.role}"


# -------------------------
# ZONE ATTEMPT (actual gameplay state)
# -------------------------
class ZoneAttempt(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("FORCED_EXIT", "Forced Exit"),
    ]

    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="zone_attempts")
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="attempts")
    player = models.ForeignKey("Player", on_delete=models.PROTECT, related_name="zone_attempts")

    access = models.OneToOneField(
        ZoneAttemptAccess,
        on_delete=models.PROTECT,
        related_name="attempt"
    )

    entry_time = models.DateTimeField(auto_now_add=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        unique_together = ("player", "zone")
        indexes = [
            models.Index(fields=["zone", "status"]),
            models.Index(fields=["player", "status"]),
        ]

    def end_attempt(self, status):
        if self.status == "ACTIVE":
            from django.utils import timezone
            self.status = status
            self.exit_time = timezone.now()
            self.save(update_fields=["status", "exit_time"])

    @property
    def time_taken_seconds(self):
        if self.exit_time:
            return int((self.exit_time - self.entry_time).total_seconds())
        return None

    def save(self, *args, **kwargs):
        # Safety checks: prevent mismatched access codes
        if self.access.player_id != self.player_id:
            raise ValueError("Access code does not belong to this player")
        if self.access.zone_id != self.zone_id:
            raise ValueError("Access code does not belong to this zone")
        if self.access.team_id != self.team_id:
            raise ValueError("Access code does not belong to this team")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.team.name} - {self.zone.title} - {self.player.role} ({self.status})"


# -------------------------
# SCORE (unchanged for now)
# -------------------------
class Score(models.Model):
    team = models.OneToOneField(
        "Team",
        on_delete=models.CASCADE,
        related_name="score"
    )

    zone1 = models.IntegerField(default=0)
    zone2 = models.IntegerField(default=0)
    zone3 = models.IntegerField(default=0)
    zone4 = models.IntegerField(default=0)
    zone5 = models.IntegerField(default=0)
    zone6 = models.IntegerField(default=0)

    @property
    def total(self):
        return (
            self.zone1 +
            self.zone2 +
            self.zone3 +
            self.zone4 +
            self.zone5 +
            self.zone6
        )

    def __str__(self):
        return f"{self.team.name} Score"
# -------------------------
# ZONE CONTENT (ROLE-BASED)
# -------------------------
class ZoneContent(models.Model):
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="contents"
    )

    role = models.CharField(
        max_length=20,
        choices=Player.ROLE_CHOICES
    )

    content = models.TextField(
        help_text="HTML / Markdown / plain text rendered inside the zone"
    )

    class Meta:
        unique_together = ("zone", "role")
        indexes = [
            models.Index(fields=["zone", "role"]),
        ]

    def __str__(self):
        return f"{self.zone.title} - {self.role}"
