from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from collections import defaultdict
from django.utils.timezone import make_naive

from .models import (
    TeamSession,
    Zone,
    ZoneAttemptAccess,
    ZoneAttempt,
    ZoneContent,
    Player,
    Score,
)

from django.utils.timezone import make_naive
from django.db.models import Prefetch
from .models import Score, ZoneAttempt



# -------------------------
# CONFIG
# -------------------------

MAX_SESSIONS = 5
SESSION_IDLE_MINUTES = 30


# -------------------------
# AUTH (TEAM LOGIN)
# -------------------------

def team_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request, "login.html", {"error": "Invalid credentials"})

        # cleanup stale sessions
        cutoff = timezone.now() - timedelta(minutes=SESSION_IDLE_MINUTES)
        TeamSession.objects.filter(last_seen_at__lt=cutoff).delete()

        with transaction.atomic():
            active_sessions = (
                TeamSession.objects
                .select_for_update()
                .filter(user=user)
                .count()
            )

            if active_sessions >= MAX_SESSIONS:
                return HttpResponseForbidden("Maximum sessions reached")

            login(request, user)

            if not request.session.session_key:
                request.session.save()

            TeamSession.objects.get_or_create(
                session_key=request.session.session_key,
                defaults={"user": user},
            )

        return redirect("index")

    return render(request, "login.html")


@login_required(login_url="/login/")
def team_logout(request):
    TeamSession.objects.filter(
        session_key=request.session.session_key
    ).delete()

    logout(request)
    return redirect("team_login")


# -------------------------
# DASHBOARD (TEAM VIEW)
# -------------------------

@login_required(login_url="/login/")
def index(request):
    team = getattr(request.user, "team", None)
    players = team.players.all()

    return render(request, "index.html", {
        "team": team,
        "players": players,
    })


# -------------------------
# ZONES (TEAM VIEW)
# -------------------------
@login_required(login_url="/login/")
def zones_view(request):
    team = request.user.team
    zones = Zone.objects.all()
    print(f"DEBUG: Found {zones.count()} zones for team {team.name}")

    # 1️⃣ Game state
    attempts = (
        ZoneAttempt.objects
        .filter(team=team)
        .select_related("zone")
    )

    attempts_by_zone = {}
    for attempt in attempts:
        attempts_by_zone.setdefault(attempt.zone_id, []).append(attempt)

    # 2️⃣ Access state (ONLY UNUSED)
    access_by_zone = (
        ZoneAttemptAccess.objects
        .filter(team=team, is_used=False)
        .values_list("zone_id", flat=True)
    )
    access_zone_ids = set(access_by_zone)

    score_obj = getattr(team, "score", None)

    for zone in zones:
        zone_attempts = attempts_by_zone.get(zone.id, [])

        zone.has_active = any(a.status == "ACTIVE" for a in zone_attempts)
        zone.has_completed = any(a.status == "COMPLETED" for a in zone_attempts)

        zone.has_access = zone.id in access_zone_ids

        # SCORE
        if score_obj:
            zone.score = getattr(score_obj, f"zone{zone.id}", 0)
        else:
            zone.score = 0

        # 🔐 ENTRY PERMISSION (THIS IS THE FIX)
        if zone.has_active:
            zone.can_enter = True
        elif zone.has_completed:
            zone.can_enter = zone.has_access
        else:
            zone.can_enter = zone.has_access

    print(f"DEBUG: Passing {len(zones)} zones to template")
    for z in zones:
        print(f"  Zone {z.id}: {z.title} - Active:{getattr(z, 'has_active', None)} Completed:{getattr(z, 'has_completed', None)} CanEnter:{getattr(z, 'can_enter', None)}")
    
    return render(request, "zones.html", {
        "zones": zones,
    })
# -------------------------
# PLAYER ENTRY (ATTEMPT CODE AUTH)
# -------------------------

def enter_zone(request):
    """
    Player enters zone using their unique attempt code.
    This does NOT require team login.
    """

    if request.method == "POST":
        attempt_code = request.POST.get("attempt_code", "").strip()

        if not attempt_code:
            return render(request, "enter_zone.html", {
                "error": "Attempt code is required"
            })

        try:
            access = ZoneAttemptAccess.objects.select_related(
                "team", "zone", "player"
            ).get(attempt_code=attempt_code, is_used=False)
        except ZoneAttemptAccess.DoesNotExist:
            return render(request, "enter_zone.html", {
                "error": "Invalid or already used attempt code"
            })

        # Block re-attempt by same player
        if ZoneAttempt.objects.filter(
            player=access.player,
            zone=access.zone
        ).exists():
            return render(request, "enter_zone.html", {
                "error": "This player has already attempted this zone"
            })

        # Create attempt
        attempt = ZoneAttempt.objects.create(
            team=access.team,
            zone=access.zone,
            player=access.player,
            access=access
        )

        # Burn code
        access.is_used = True
        access.save(update_fields=["is_used"])

        # Store attempt in session (player identity)
        request.session["active_attempt_id"] = attempt.id

        return redirect("zone_play", zone_id=attempt.zone.id)

    return render(request, "enter_zone.html")


# -------------------------
# ZONE PLAY (PLAYER VIEW)
# -------------------------
def zone_play(request, zone_id):
    attempt_id = request.session.get("active_attempt_id")
    if not attempt_id:
        return redirect("enter_zone")

    attempt = get_object_or_404(
        ZoneAttempt,
        id=attempt_id,
        zone_id=zone_id,
        status="ACTIVE"
    )

    zone_content = get_object_or_404(
        ZoneContent,
        zone=attempt.zone,
        role=attempt.player.role
    )

    return render(request, "zone_play.html", {
        "attempt": attempt,
        "zone": attempt.zone,
        "player": attempt.player,
        "role": attempt.player.role,
        "content": zone_content.content,
        "exit_code": zone_content.exit_code or "",
    })
# -------------------------
# SUBMIT ZONE (PLAYER)
# -------------------------
@login_required
def submit_zone(request, zone_id):
    team = request.user.team

    attempt = (
        ZoneAttempt.objects
        .filter(
            team=team,
            zone_id=zone_id,
            status="ACTIVE"
        )
        .order_by("-entry_time")  # ✅ correct field
        .first()
    )

    if not attempt:
        return redirect("zones")

    # Validate exit code
    zone_content = ZoneContent.objects.filter(
        zone=attempt.zone,
        role=attempt.player.role
    ).first()

    if zone_content and zone_content.exit_code:
        submitted_exit_code = request.POST.get("exit_code", "").strip()
        
        if submitted_exit_code != zone_content.exit_code:
            from django.contrib import messages
            messages.error(request, "Incorrect exit code. Please try again.")
            return redirect("zone_play", zone_id=zone_id)

    attempt.end_attempt(status="COMPLETED")

    # Optional cleanup
    request.session.pop("active_attempt_id", None)

    return redirect("zones")
# -------------------------------------
# LEADERBOARD (PUBLIC / TEAM VIEW)
# -------------------------------------
from collections import defaultdict
from django.shortcuts import render
from django.utils.timezone import make_naive


def leaderboard_view(request):
    scores = Score.objects.select_related("team").all()

    # -----------------------
    # Leaderboard Data
    # -----------------------
    leaderboard_data = []

    for score in scores:
        total_time = score.get_total_time_seconds()

        leaderboard_data.append({
            "score": score,
            "total_time_seconds": total_time,  # used only for display
            "total_time_display": format_time_display(total_time),
        })

    # -----------------------
    # Leaderboard Sorting
    # -----------------------
    # 1️⃣ Total DESC
    # 2️⃣ Credit DESC
    leaderboard = sorted(
        leaderboard_data,
        key=lambda x: (
            -x["score"].total,
            -x["score"].credit,
        ),
    )

    # -----------------------
    # Timeline Graph Data
    # -----------------------

    attempts = (
        ZoneAttempt.objects
        .filter(status="COMPLETED", exit_time__isnull=False)
        .select_related("team", "zone")
        .order_by("exit_time")
    )

    team_progress = defaultdict(list)
    team_scores = defaultdict(int)

    for attempt in attempts:
        team = attempt.team
        team_name = team.name

        score_obj = getattr(team, "score", None)
        if not score_obj:
            continue

        zone_field = f"zone{attempt.zone.id}"
        zone_points = getattr(score_obj, zone_field, 0)

        team_scores[team_name] += zone_points

        team_progress[team_name].append({
            "x": make_naive(attempt.exit_time).isoformat(),
            "y": team_scores[team_name],
        })

    graph_data = [
        {
            "label": team,
            "data": data,
        }
        for team, data in team_progress.items()
    ]

    return render(request, "leaderboard.html", {
        "leaderboard": leaderboard,
        "graph_data": graph_data,
    })

def format_time_display(seconds):
    """Format seconds into MM:SS or HH:MM:SS"""
    if seconds == 0:
        return "--:--"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def leaderboard_data_api(request):
    scores = Score.objects.select_related("team").all()

    user_team = None
    if request.user.is_authenticated:
        user_team = getattr(request.user, "team", None)

    leaderboard_data = []

    for score in scores:
        total_time = score.get_total_time_seconds()

        leaderboard_data.append({
            "team": score.team.name,
            "total": score.total,
            "credit": score.credit,
            "time": format_time_display(total_time),
            "is_you": user_team == score.team if user_team else False,
        })

    leaderboard = sorted(
        leaderboard_data,
        key=lambda x: (-x["total"], -x["credit"]),
    )

    return JsonResponse({"leaderboard": leaderboard})

