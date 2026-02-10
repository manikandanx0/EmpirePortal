import csv
import random
import string

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError

from app.models import Team, Player


def random_password(length=8):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(chars) for _ in range(length))


def slugify_name(name):
    return name.lower().replace(" ", "_")


VALID_ROLES = {choice[0] for choice in Player.ROLE_CHOICES}


class Command(BaseCommand):
    help = "Import teams & players from CSV and generate TEAM login credentials"

    def add_arguments(self, parser):
        parser.add_argument("input_csv", type=str)
        parser.add_argument(
            "--output",
            type=str,
            default="generated_team_credentials.csv"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        input_csv = options["input_csv"]
        output_csv = options["output"]

        teams_created = {}
        credentials = []

        # ✅ utf-8-sig fixes Excel BOM issue
        with open(input_csv, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            required_columns = {"team_name", "player_name", "role"}

            if not reader.fieldnames:
                raise Exception("CSV file is empty or missing header row")

            if not required_columns.issubset(reader.fieldnames):
                raise Exception(
                    f"CSV must contain columns {required_columns}, "
                    f"but found {reader.fieldnames}"
                )

            for row in reader:
                team_name = row["team_name"].strip()
                player_name = row["player_name"].strip()
                role = row["role"].strip()

                if role not in VALID_ROLES:
                    raise ValueError(
                        f"Invalid role '{role}' for player '{player_name}' "
                        f"in team '{team_name}'"
                    )

                # --- Create team + team user only once ---
                if team_name not in teams_created:
                    username = slugify_name(team_name)
                    password = random_password()

                    user = User.objects.create_user(
                        username=username,
                        password=password
                    )

                    team = Team.objects.create(
                        name=team_name,
                        user=user
                    )

                    teams_created[team_name] = team
                    credentials.append([
                        team_name,
                        username,
                        password
                    ])
                else:
                    team = teams_created[team_name]

                # --- Create player (role must be unique per team) ---
                try:
                    Player.objects.create(
                        name=player_name,
                        role=role,
                        team=team
                    )
                except IntegrityError:
                    raise IntegrityError(
                        f"Role '{role}' already exists in team '{team_name}'"
                    )

        # --- Write output credentials ---
        with open(output_csv, "w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out)
            writer.writerow(["team_name", "username", "password"])
            writer.writerows(credentials)

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Teams & players imported successfully\n"
                f"✔ Team credentials saved to {output_csv}"
            )
        )
