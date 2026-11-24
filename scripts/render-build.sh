#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt
python -m pip check
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput --ignore=src
# Free compute has no pre-deploy command. Only backward-compatible migrations
# are safe while the old instance is serving.
python manage.py migrate --noinput
python manage.py migrate --check
# Temporary opt-in; command independently validates environment and target.
if [[ "${RUN_ASSESSMENT_DEMO_SEED:-false}" == "true" ]]; then
    python manage.py run_render_demo_seed
fi
