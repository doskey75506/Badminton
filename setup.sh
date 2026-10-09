#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d badminton ]; then
  python3 -m venv badminton
fi
badminton/bin/pip install --upgrade pip --quiet
badminton/bin/pip install --quiet -r requirements.txt

echo "Setup complete. Next steps:"
echo "  source badminton/bin/activate"
echo "  streamlit run app.py"
echo "Run tests:"
echo "  python -m pytest"
