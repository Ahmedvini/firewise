#!/usr/bin/env bash
# Rebuild the scientific database from the NASA sources and stage it for deployment (deploy/firewise.sqlite).
# Requires the original files (Data/, sources/psi_files/) that are not in git. Run from the repo root.
set -euo pipefail
python3 -I scripts/twin_validate.py .
python3 -I scripts/load_db.py .
cp build/firewise.sqlite deploy/firewise.sqlite
echo "Staged deploy/firewise.sqlite ($(du -h deploy/firewise.sqlite | cut -f1)). Commit it to redeploy."
