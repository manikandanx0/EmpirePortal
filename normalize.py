import csv
import sys

INPUT_FILE = "teams.csv"
OUTPUT_FILE = "normalized_teams.csv"

ROLE_MAPPING = {
    "INTERN NAME": "INTERN",
    "JUNIOR ANALYST NAME": "JUNIOR_ANALYST",
    "TEAM LEAD NAME": "TEAM_LEADER",
    "MANAGER NAME": "MANAGER",
    "CEO NAME": "CEO",
}

def normalize_csv(input_file, output_file):
    with open(input_file, newline="", encoding="utf-8") as infile, \
         open(output_file, mode="w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=["team_name", "player_name", "role"])
        writer.writeheader()

        for row in reader:
            # Uppercase + strip keys and values
            clean_row = {
                k.strip().upper(): (v.strip().upper() if v else "")
                for k, v in row.items()
            }

            team_name = clean_row.get("TEAM NAME", "")
            if not team_name:
                continue

            for column, role in ROLE_MAPPING.items():
                player_name = clean_row.get(column, "")
                if player_name:
                    writer.writerow({
                        "team_name": team_name,
                        "player_name": player_name,
                        "role": role
                    })

    print("✅ Normalization complete.")
    print(f"Saved as: {output_file}")


if __name__ == "__main__":
    # Allow optional CLI usage
    if len(sys.argv) == 3:
        normalize_csv(sys.argv[1], sys.argv[2])
    else:
        normalize_csv(INPUT_FILE, OUTPUT_FILE)
