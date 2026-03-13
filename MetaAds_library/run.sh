#!/usr/bin/env bash
# Run meta-ads CLI from project root with dependencies.
# Usage: ./run.sh fetch --query "guard.io" --country US --csv-only
set -e
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -e .
fi
exec .venv/bin/python -m meta_ads.cli "$@"
