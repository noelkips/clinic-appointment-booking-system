#!/usr/bin/env bash
set -euo pipefail

: "${CPANEL_APP_ROOT:?Set CPANEL_APP_ROOT to the Python app root}"
: "${CPANEL_VENV:?Set CPANEL_VENV to the cPanel Python virtualenv directory}"

cd "$CPANEL_APP_ROOT"
test -f manage.py
test -f passenger_wsgi.py
source "$CPANEL_VENV/bin/activate"
python -m pip install -r requirements.txt
python -m pip check
test -f .env
dotenv run -- python manage.py check --deploy --fail-level WARNING
dotenv run -- python manage.py migrate --noinput
dotenv run -- python manage.py migrate --check
dotenv run -- python manage.py collectstatic --noinput --ignore=src
mkdir -p tmp
touch tmp/restart.txt
