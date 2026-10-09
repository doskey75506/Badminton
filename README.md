# Badminton Club Matchmaker

A single-page Streamlit web app for running a badminton club night: take attendance, auto-generate balanced 4-player doubles pairings, record scores, and update player ratings. UI language is Chinese.

## Quick start

```bash
./setup.sh                       # creates the `badminton` venv + installs deps
source badminton/bin/activate
streamlit run app.py             # opens http://localhost:8501
python -m pytest                 # run tests from the repo root
```

## System diagram

```
                 Browser (localhost:8501)
                          │ HTTP
                          ▼
 ┌─────────────────────────────────────────────────┐
 │ app.py  —  Streamlit UI server                  │
 │ pages: Members / Tonight's Attendance /         │
 │        Matchmaking & Scores / Standings         │
 └──────────────┬─────────────────────┬────────────┘
                │ suggest_match()     │ apply_result()
                ▼                     ▼
 ┌───────────────────────────┐  ┌─────────────────────────┐
 │ matchmaking.py            │  │ ratings.py              │
 │ pairing engine            │  │ team-sum Elo, K=32      │
 │ (pure logic, no IO)       │  │ (pure logic, no IO)     │
 └─────────────┬─────────────┘  └───────────┬─────────────┘
               │      read / write          │
               ▼                            ▼
 ┌─────────────────────────────────────────────────────────┐
 │ storage.py — atomic JSON read/write                     │
 └──────────────────────────┬──────────────────────────────┘
                            ▼
 ┌─────────────────────────────────────────────────────────┐
 │ data/                                                   │
 │   members.json     ratings + names                      │
 │   attendance.json  checked-in players per date          │
 │   matches.json     history, scores, rating snapshots    │
 └─────────────────────────────────────────────────────────┘

 tests/ ──imports──▶ matchmaking.py + ratings.py
                     (pure logic only — no Streamlit, no IO)
```

## How it works

- **Matchmaking priority** (lexicographic, in `suggest_match`):
  1. balance rest time — pick the quad with the fewest total games tonight, breaking ties by longest consecutive bench streak
  2. balance teams — compare rating sums in 100-point buckets ("basically balanced")
  3. vary partners/opponents — minimize repeated partners, then repeated opponents
- **Ratings**: team-sum Elo (K=32) with a margin-of-victory multiplier. The snapshot is taken at match confirmation; submitting the score applies the update.
- **Data**: everything lives in `data/*.json`. Deleting that folder resets the club.

## Layout

| File | Role |
| --- | --- |
| `app.py` | all UI (Streamlit, Chinese strings) |
| `matchmaking.py` | pairing engine (pure) |
| `ratings.py` | rating math (pure) |
| `storage.py` | JSON persistence |
| `tests/` | pytest tests for the pure modules |
