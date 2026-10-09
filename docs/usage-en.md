# User Guide (English)

Badminton club matchmaking tool: a web app for multiple clubs and multiple courts — auto-generates doubles pairings, records scores, updates ratings, and queries match history. The UI is Chinese by default; switch to English in the sidebar.

## Install & run

```bash
./setup.sh      # first time: creates the venv and installs dependencies
./startup.sh    # starts the app (default http://localhost:8501)
```

## First-time setup

1. On first open, **create a club** (the name must be unique).
2. Use the sidebar **Club** dropdown to switch clubs at any time; expand **New club** to add another.
3. Go to the **Members** page and add players: name is required, initial rating is optional (default 1000). Names must be unique within a club.

## Nightly workflow (Tonight page)

1. **Check in attendance**: tick everyone who showed up. You can tick/untick at any time during the night; only currently ticked players are considered for pairings. Anyone already on court is automatically excluded from the pool.
2. **Set court count**: adjust 1–12 courts at the top. It is saved automatically and remembered next time.
3. **Generate pairings**: click “Generate pairings for N free court(s)”. The app balances rest time (players who rested longest are picked first), then team strength, then varies partners/opponents.
   - Each court needs 4 free players. If there are not enough, only some courts are filled; the rest show “Free”.
   - The “On court” column shows each player's court number (e.g. 1, 2); anyone not assigned shows “Rest”.
4. **Start**: confirm the pairing on a court card and click “Start” — the match start time is recorded.
5. **Shuffle**: click “Shuffle” for a different pairing (you get a notice if no alternative is available).
6. **Enter the score**: after the match, type the final scores for teams A and B (integers, 0–30, a winner is required) and click “Submit score”. Ratings update automatically and the match is written to history. Finished matches cannot be edited, so double-check before submitting.
7. **Cancel**: a started match with no score yet can be cancelled; those players return to the pool.

## Other pages

- **Members**: view / add / delete players (deleting also clears their attendance records; past matches stay in history).
- **Standings**: ranked by current rating, with games, W/L, and win rate.
- **History**: filter by time range (today / last 7 / last 30 days / all time) and by player; shows score, duration, and rating changes per match.

## Rating system in brief

Team-sum Elo (K=32): expected score is computed from the sum of each team's ratings, then multiplied by a margin multiplier (bigger for larger score lines and closer teams, clamped to 1.0–2.0). Every winner gains the same delta; every loser loses the same delta. Ratings are snapshotted at match start and applied when the score is submitted; values keep one decimal and never go below 0. Full formula and worked example: [docs/rating.md](rating.md).

## Data

Everything is stored locally as JSON under `data/`: club list, members and ratings, daily attendance, match history, and court settings. Deleting that folder wipes all data; never commit `data/` to version control.
