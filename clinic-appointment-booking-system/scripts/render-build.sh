#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt
python -m pip check
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput --ignore=src
# Free compute has no pre-deploy command. Only backward-compatible migrations
# are safe while the old instance is serving. Never seed production here.
python manage.py migrate --noinput
python manage.py migrate --check
