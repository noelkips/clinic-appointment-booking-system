from django.db import migrations, models
import re

from django.db.models import Case, F, Q, Value, When
from django.db.models.functions import Extract
from django.db.models.lookups import Exact


class AddFieldIfMissing(migrations.AddField):
    """Make the DDL safe to retry after MySQL's implicit DDL commits."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        with schema_editor.connection.cursor() as cursor:
            columns = schema_editor.connection.introspection.get_table_description(
                cursor, model._meta.db_table
            )
        if not any(column.name == self.name for column in columns):
            super().database_forwards(app_label, schema_editor, from_state, to_state)


class AddConstraintIfMissing(migrations.AddConstraint):
    """Skip a constraint already committed by a partially failed migration."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        with schema_editor.connection.cursor() as cursor:
            constraints = schema_editor.connection.introspection.get_constraints(
                cursor, model._meta.db_table
            )
        if self.constraint.name not in constraints:
            super().database_forwards(app_label, schema_editor, from_state, to_state)


def verify_mysql_support(apps, schema_editor):
    """Fail early unless this server enforces the schema features we depend on."""
    connection = schema_editor.connection
    if connection.vendor != 'mysql':
        return
    with connection.cursor() as cursor:
        cursor.execute('SELECT VERSION()')
        version_string = cursor.fetchone()[0]
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_string)
        version = tuple(map(int, match.groups())) if match else None
        is_mariadb = 'mariadb' in version_string.lower()
        minimum = (10, 5, 0) if is_mariadb else (8, 0, 16)
        if version is None or version < minimum:
            required = 'MariaDB 10.5 or newer' if is_mariadb else 'MySQL 8.0.16 or newer'
            raise RuntimeError(
                f'Appointment slot constraints require {required}; '
                f'the connected server reports {version_string}.'
            )
        for table in ('clinic_appointment', 'clinic_doctor', 'clinic_patient'):
            cursor.execute(
                'SELECT ENGINE FROM information_schema.TABLES '
                'WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s',
                [table],
            )
            row = cursor.fetchone()
            if not row or (row[0] or '').lower() != 'innodb':
                raise RuntimeError(
                    f'MySQL table {table} must use InnoDB for appointment transactions.'
                )


def remove_old_partial_indexes(apps, schema_editor):
    """Drop PostgreSQL/SQLite conditional indexes; MySQL never created them."""
    Appointment = apps.get_model('clinic', 'Appointment')
    old_constraints = (
        models.UniqueConstraint(
            fields=('doctor', 'starts_at'),
            condition=Q(status='confirmed'),
            name='unique_confirmed_doctor_slot',
        ),
        models.UniqueConstraint(
            fields=('patient', 'starts_at'),
            condition=Q(status='confirmed'),
            name='unique_confirmed_patient_slot',
        ),
    )
    with schema_editor.connection.cursor() as cursor:
        installed = schema_editor.connection.introspection.get_constraints(
            cursor, Appointment._meta.db_table
        )
    for constraint in old_constraints:
        if constraint.name in installed:
            schema_editor.remove_constraint(Appointment, constraint)


class Migration(migrations.Migration):
    dependencies = [('clinic', '0004_appointment_interval_guards')]

    operations = [
        migrations.RunPython(verify_mysql_support, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(remove_old_partial_indexes, migrations.RunPython.noop)
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name='appointment', name='unique_confirmed_doctor_slot'
                ),
                migrations.RemoveConstraint(
                    model_name='appointment', name='unique_confirmed_patient_slot'
                ),
            ],
        ),
        AddFieldIfMissing(
            model_name='appointment',
            name='active_slot_starts_at',
            field=models.GeneratedField(
                db_persist=True,
                expression=Case(
                    When(status='confirmed', then=F('starts_at')),
                    default=Value(None),
                    output_field=models.DateTimeField(),
                ),
                output_field=models.DateTimeField(null=True),
            ),
        ),
        AddConstraintIfMissing(
            model_name='appointment',
            constraint=models.CheckConstraint(
                condition=Q(status='cancelled')
                | (
                    Q(starts_at__minute__in=(0, 30))
                    & Q(starts_at__second=0)
                    & Q(Exact(Extract(F('starts_at'), 'microsecond'), 0))
                ),
                name='confirmed_appointment_half_hour_grid',
            ),
        ),
        AddConstraintIfMissing(
            model_name='appointment',
            constraint=models.UniqueConstraint(
                fields=('doctor', 'active_slot_starts_at'),
                name='unique_confirmed_doctor_slot',
            ),
        ),
        AddConstraintIfMissing(
            model_name='appointment',
            constraint=models.UniqueConstraint(
                fields=('patient', 'active_slot_starts_at'),
                name='unique_confirmed_patient_slot',
            ),
        ),
    ]
