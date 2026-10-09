# Badminton Club Matchmaker

A Streamlit web app for running badminton club nights: multiple clubs, configurable courts, auto-generated balanced doubles pairings, score entry, rating updates, and match history. UI language is selectable (中文 / English).

## Quick start

```bash
./setup.sh                       # one-time: creates the `badminton` venv + installs deps
./startup.sh                     # start the app (opens http://localhost:8501)
                                 # auto-exits ~15s after the last browser tab closes;
                                 # IDLE_EXIT_SECONDS=0 disables it, or set other seconds

# or manually:
source badminton/bin/activate
streamlit run app.py
python -m pytest                 # run tests from the repo root
```

## Documentation

- [使用说明（中文）](docs/使用说明.md)
- [User guide (English)](docs/usage.md)
- [积分规则（中文）](docs/积分规则.md)
- [Rating rules (English)](docs/rating.md)
