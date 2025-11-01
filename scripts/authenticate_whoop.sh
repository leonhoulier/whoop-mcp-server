#!/bin/bash
# Whoop OAuth Re-authentication Script Wrapper

cd "$(dirname "$0")/.."
source venv/bin/activate
set -a
source config/.env
set +a

python3 scripts/authenticate_whoop.py "$@"

