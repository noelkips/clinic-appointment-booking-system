"""Temporary deployment-only orchestration; no external database access."""
import io
import os
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor

from .seed_assessment_demo import PRIMARY


class Command(BaseCommand):
    help = 'Explicit Render build seed and verification; requires private target confirmation.'

    def handle(self, *args, **options):
        if os.getenv('RUN_ASSESSMENT_DEMO_SEED', 'false') != 'true':
            self.stdout.write('Assessment demo seed disabled; no action taken.')
            return
        if os.getenv('ASSESSMENT_DEMO_ENABLED', '').lower() != 'true':
            raise CommandError('Assessment deployment seed requires both authorization gates.')
        if (settings.DEBUG or os.getenv('RENDER') != 'true'
                or os.getenv('DJANGO_SETTINGS_MODULE') != 'config.settings'
                or os.getenv('IS_PULL_REQUEST') == 'true'):
            raise CommandError('Assessment deployment seed requires the Render production environment.')
        required = ['ASSESSMENT_EXPECTED_SERVICE_ID', 'ASSESSMENT_EXPECTED_DB_HOST',
                    'ASSESSMENT_EXPECTED_DB_NAME']
        if any(not os.getenv(key) for key in required):
            raise CommandError('Missing assessment target confirmation variables.')
        if os.getenv('RENDER_SERVICE_ID') != os.environ['ASSESSMENT_EXPECTED_SERVICE_ID']:
            raise CommandError('Render service identity mismatch; no writes performed.')
        try:
            target = urlsplit(os.environ.get('DATABASE_URL', ''))
            configured = connection.settings_dict
            if (connection.vendor != 'postgresql' or target.scheme not in ('postgres', 'postgresql')
                    or not target.hostname or not target.hostname.startswith('dpg-')
                    or '.' in target.hostname
                    or target.hostname != os.environ['ASSESSMENT_EXPECTED_DB_HOST']
                    or configured['HOST'] != target.hostname
                    or configured['NAME'] != os.environ['ASSESSMENT_EXPECTED_DB_NAME']
                    or target.path != '/' + configured['NAME']):
                raise ValueError()
        except Exception:
            raise CommandError('Internal database target mismatch; no writes performed.') from None
        if any(not os.getenv('ASSESSMENT_' + kind.upper() + '_PASSWORD') for kind in PRIMARY):
            raise CommandError('Missing required assessment password environment variables; no writes performed.')
        output = io.StringIO()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT current_database()')
                if cursor.fetchone()[0] != os.environ['ASSESSMENT_EXPECTED_DB_NAME']:
                    raise ValueError()
            executor = MigrationExecutor(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise ValueError()
            with transaction.atomic():
                call_command('seed_assessment_demo', confirm_database=configured['NAME'],
                             no_input=True, stdout=output, stderr=output)
                call_command('verify_assessment_demo', no_input=True, stdout=output, stderr=output)
        except Exception:
            raise CommandError('Assessment seed/verification failed; seed transaction rolled back. Check target, migrations, ownership and private credentials.') from None
        self.stdout.write(output.getvalue())
        self.stdout.write(self.style.SUCCESS('RENDER ASSESSMENT DEMO SEED VERIFIED. Disable both gates and remove temporary password variables now.'))
