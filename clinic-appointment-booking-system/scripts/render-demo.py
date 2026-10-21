"""Interactive workstation entrypoint. Never imported by the web/build process."""
import argparse
import getpass
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'seed', 'verify'])
    args = parser.parse_args()
    # Do not inherit a test settings module or accidentally fall back to local .env.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['DJANGO_DEBUG'] = 'False'
    os.environ['DJANGO_SECRET_KEY'] = secrets.token_urlsafe(64)
    os.environ['ASSESSMENT_DEMO_ENABLED'] = 'False'
    private_url = getpass.getpass('Existing Render EXTERNAL PostgreSQL URL (hidden): ')
    target = urlsplit(private_url)
    if (target.scheme not in ('postgres', 'postgresql') or not target.hostname
            or not target.hostname.endswith('.render.com') or not target.path.strip('/')):
        raise ValueError('Use the full external Render database URL from its Connect menu.')
    import dj_database_url
    database = dj_database_url.parse(private_url, conn_max_age=0)
    # Enforce server identity verification; query parameters cannot downgrade it.
    database.setdefault('OPTIONS', {}).update(
        sslmode='verify-full', sslrootcert='system', connect_timeout=15,
        options='-c statement_timeout=30000 -c lock_timeout=10000',
    )
    os.environ['DATABASE_URL'] = private_url
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    settings.DATABASES['default'] = database
    connection.settings_dict.update(database)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(), ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()')
        actual, tls = cursor.fetchone()
    if actual != database['NAME'] or not tls:
        raise ValueError('Database identity or TLS check failed.')
    call_command('migrate', check=True)  # checks only; never applies migrations
    call_command('seed_assessment_demo', inspect=True)
    if args.action == 'seed':
        phrase = f'SEED {target.hostname}/{actual}'
        if input(f'After owner authorization, type {phrase}: ') != phrase:
            raise ValueError('Authorization phrase did not match; no seed executed.')
        os.environ['ASSESSMENT_DEMO_ENABLED'] = 'True'
        try:
            call_command('seed_assessment_demo', confirm_database=actual)
        finally:
            os.environ['ASSESSMENT_DEMO_ENABLED'] = 'False'
    elif args.action == 'verify':
        call_command('verify_assessment_demo')
    connection.close()


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt):
        # Connection exceptions can contain credentials; never render the exception.
        print('Operation stopped. Check target, network allowance, TLS trust, migrations and credential inputs privately.', file=sys.stderr)
        sys.exit(1)
