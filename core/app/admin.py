from django.contrib import admin
from .models import (
    Team,
    Player,
    TeamSession,
    Zone,
    ZoneContent,
    ZoneAttemptAccess,
    ZoneAttempt,
    Score,
)

# -------------------------
# TEAM
# -------------------------

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


# -------------------------
# PLAYER
# -------------------------


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "role", "team")
    list_filter = ("role", "team")
    search_fields = ("name", "role", "team__name")  # 🔍 allow searching by name & role


# -------------------------
# TEAM SESSION
# -------------------------

@admin.register(TeamSession)
class TeamSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "last_seen_at")
    list_filter = ("user",)


# -------------------------
# ZONE
# -------------------------
# -------------------------
# ZONE CONTENT (INLINE)
# -------------------------

class ZoneContentInline(admin.TabularInline):
    model = ZoneContent
    extra = 0

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    inlines = [ZoneContentInline]  


# -------------------------
# ZONE ATTEMPT ACCESS (PER PLAYER CODES)
# -------------------------

@admin.register(ZoneAttemptAccess)
class ZoneAttemptAccessAdmin(admin.ModelAdmin):

    list_display = ("team", "zone", "player", "attempt_code", "is_used", "created_at")
    list_filter = ("zone", "team", "is_used")
    autocomplete_fields = ["player", "team"]
    search_fields = ("attempt_code", "player__name", "team__name")
    ordering = ("team__name", "zone__title", "player__role")





# -------------------------
# ZONE ATTEMPT (LIVE ATTEMPTS)
# -------------------------

@admin.register(ZoneAttempt)
class ZoneAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "zone",
        "get_role",
        "status",
        "entry_time",
        "exit_time",
    )

    list_filter = ("zone", "status", "team")
    ordering = ("team__name", "zone__title", "player__role")
    readonly_fields = ("entry_time", "exit_time")

    def get_role(self, obj):
        return obj.player.role

    get_role.short_description = "Role"


# -------------------------
# SCORE
# -------------------------

@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "zone1",
        "zone2",
        "zone3",
        "zone4",
        "zone5",
        "zone6",
        "total_display",
    )

    list_editable = (
        "zone1",
        "zone2",
        "zone3",
        "zone4",
        "zone5",
        "zone6",
    )

    ordering = ("team__name",)

    def total_display(self, obj):
        return obj.total  # property, no parentheses

    total_display.short_description = "Total"
