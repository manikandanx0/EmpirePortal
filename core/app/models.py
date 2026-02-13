from django.db import models
from django.contrib.auth.models import User
import uuid
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
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
        verbose_name = "Create Code"
        verbose_name_plural = "Create Codes"

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

    # -------------------------
    # ZONE SCORES
    # -------------------------
    zone1 = models.IntegerField(default=0)
    zone2 = models.IntegerField(default=0)
    zone3 = models.IntegerField(default=0)
    zone4 = models.IntegerField(default=0)
    zone5 = models.IntegerField(default=0)
    zone6 = models.IntegerField(default=0)

    # -------------------------
    # CREDITS (Standalone Resource)
    # -------------------------
    credit = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Standalone credits used for tie-breaking or advantages."
    )

    # -------------------------
    # TOTAL SCORE (does NOT include credit)
    # -------------------------
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

    # -------------------------
    # TOTAL TIME (All completed zones)
    # -------------------------
    def get_total_time_seconds(self):
        """
        Returns total time taken across all completed zone attempts.
        """
        completed_attempts = self.team.zone_attempts.filter(
            status="COMPLETED"
        )

        total_seconds = sum(
            attempt.time_taken_seconds or 0
            for attempt in completed_attempts
        )

        return total_seconds

    # -------------------------
    # DISPLAY TIME (Optional helper)
    # -------------------------
    def get_total_time_display(self):
        """
        Returns formatted time as HH:MM:SS
        """
        total_seconds = self.get_total_time_seconds()

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02}:{minutes:02}:{seconds:02}"

    # -------------------------
    # LEADERBOARD RANKING VALUE
    # -------------------------
    @property
    def tie_break_value(self):
        """
        Used for ordering:
        1. Total score
        2. Credit (higher wins)
        3. Time (lower wins)
        """
        return (self.total, self.credit, -self.get_total_time_seconds())
    class Meta:
        verbose_name = "Enter Scores"
        verbose_name_plural = "Enter Scores"
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

    exit_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Code required to exit/submit this zone"
    )

    class Meta:
        unique_together = ("zone", "role")
        indexes = [
            models.Index(fields=["zone", "role"]),
        ]

    def __str__(self):
        return f"{self.zone.title} - {self.role}"
