#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d badminton ]; then
  echo "Virtual environment not found. Run ./setup.sh first." >&2
  exit 1
fi

source badminton/bin/activate
exec streamlit run app.py "$@"
