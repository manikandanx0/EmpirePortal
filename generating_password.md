# How to Import Teams & Players (Simple Steps)

This guide shows **exactly how to use the import command** to create teams, players, and login credentials.

---

## Step 1: Prepare the CSV File

Create a CSV file (for example: `teams_players.csv`).

### Format (required)

```csv
team_name,    player_name, role
Alpha Coders, Aarav,       TEAM_LEADER
Alpha Coders, Riya,        CEO
Alpha Coders, Neha,        MANAGER
Alpha Coders, Dev,         JUNIOR_ANALYST
Alpha Coders, Kunal,       INTERN
````

### Rules

* One row = one player
* Same team name = same team
* Each role can appear only once per team
* Roles must be exactly:

  * `INTERN`
  * `JUNIOR_ANALYST`
  * `TEAM_LEADER`
  * `MANAGER`
  * `CEO`

---

## Step 2: Place the CSV File

Copy the CSV file into the project root (same folder as `manage.py`).

Example:

```bash
EmpirePortal/
├── manage.py
├── teams_players.csv
```

---

## Step 3: Run the Import Command

Open terminal in the project folder and run:

```bash
python manage.py import_teams_players teams_players.csv
```

---

## Step 4: Get the Output File

After successful import, a file is generated automatically:

```sh
generated_team_credentials.csv
```

### Example Output

```csv
team_name,username,password
Alpha Coders,alpha_coders_4832,K9#Pq2@M
Byte Force,byte_force_9123,L2!XpQ8@
```

---

## Step 5: Share Login Details

* Each team gets **one username & password**
* Share the credentials with the respective team
* Teams use these credentials to log in

---

## Optional: Custom Output File Name

```bash
python manage.py import_teams_players teams_players.csv --output round1_logins.csv
```

---

## If Something Goes Wrong

* If there is an error, **no data is saved**
* Fix the CSV and run the command again
* Common issues:

  * Invalid role name
  * Duplicate role in the same team
  * Missing column in CSV

---

## That’s It 🎯

1. Prepare CSV
2. Run command
3. Share credentials

No admin panel work. No manual setup.
