import random
import string
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import (
    Team,
    Player,
    Zone,
    ZoneAttemptAccess,
    ZoneAttempt,
    Score,
)


def random_code(length=12):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class Command(BaseCommand):
    help = "Generate fake gameplay data for existing teams"

    def handle(self, *args, **kwargs):
        self.stdout.write("Generating gameplay data for existing teams...")

        teams = Team.objects.all()
        zones = Zone.objects.all().order_by("id")

        if not teams.exists():
            self.stdout.write(self.style.ERROR("No teams found."))
            return

        if not zones.exists():
            self.stdout.write(self.style.ERROR("No zones found."))
            return

        for team in teams:

            players = team.players.all()

            # If players missing roles, create them
            existing_roles = set(players.values_list("role", flat=True))
            for role, _ in Player.ROLE_CHOICES:
                if role not in existing_roles:
                    Player.objects.create(
                        name=f"{role}_{team.id}",
                        role=role,
                        team=team
                    )

            players = team.players.all()

            # Safely get or create Score
            score, _ = Score.objects.get_or_create(team=team)

            # Reset scores
            for i in range(1, 7):
                setattr(score, f"zone{i}", 0)
            score.save()

            # Clear old attempts + access codes
            ZoneAttempt.objects.filter(team=team).delete()
            ZoneAttemptAccess.objects.filter(team=team).delete()

            current_time = timezone.now() - timedelta(hours=4)

            for zone in zones:

                # 70% chance team solves zone
                if random.random() < 0.7:

                    player = random.choice(players)

                    access = ZoneAttemptAccess.objects.create(
                        zone=zone,
                        team=team,
                        player=player,
                        attempt_code=random_code(),
                        is_used=True
                    )

                    entry_time = current_time + timedelta(
                        minutes=random.randint(5, 15)
                    )

                    duration_minutes = random.randint(10, 40)
                    exit_time = entry_time + timedelta(minutes=duration_minutes)

                    ZoneAttempt.objects.create(
                        team=team,
                        zone=zone,
                        player=player,
                        access=access,
                        entry_time=entry_time,
                        exit_time=exit_time,
                        status="COMPLETED"
                    )

                    # Assign realistic points
                    zone_points = random.choice([100, 200, 300, 400, 500])
                    setattr(score, f"zone{zone.id}", zone_points)

                    current_time = exit_time

            score.save()

        self.stdout.write(self.style.SUCCESS("Gameplay data generated successfully!"))
