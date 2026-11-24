"""Protect half-open 30-minute intervals, including writes outside the services."""
from datetime import timedelta
from django.db import migrations


def install_guards(apps, schema_editor):
    Appointment = apps.get_model('clinic', 'Appointment')
    active = Appointment.objects.using(schema_editor.connection.alias).filter(status='confirmed')
    for row in active.iterator():
        conflicts = active.exclude(pk=row.pk).filter(
            starts_at__gt=row.starts_at-timedelta(minutes=30),
            starts_at__lt=row.starts_at+timedelta(minutes=30),
        )
        if conflicts.filter(doctor_id=row.doctor_id).exists() or conflicts.filter(patient_id=row.patient_id).exists():
            raise RuntimeError('Existing overlapping confirmed appointments must be reviewed before applying interval guards. No appointments were changed.')
    vendor = schema_editor.connection.vendor
    if vendor == 'sqlite':
        for action in ('INSERT', 'UPDATE'):
            schema_editor.execute(f"""
                CREATE TRIGGER clinic_appointment_no_overlap_{action.lower()}
                BEFORE {action} ON clinic_appointment
                WHEN NEW.status = 'confirmed'
                BEGIN
                  SELECT RAISE(ABORT, 'Confirmed appointment interval overlaps')
                  WHERE EXISTS (
                    SELECT 1 FROM clinic_appointment AS a
                    WHERE a.status = 'confirmed' AND a.id != NEW.id
                      AND (a.doctor_id = NEW.doctor_id OR a.patient_id = NEW.patient_id)
                      AND julianday(a.starts_at) < julianday(NEW.starts_at, '+30 minutes')
                      AND julianday(a.starts_at, '+30 minutes') > julianday(NEW.starts_at)
                  );
                END
            """)
    elif vendor == 'postgresql':
        schema_editor.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
        for owner in ('doctor', 'patient'):
            schema_editor.execute(f"""
                ALTER TABLE clinic_appointment ADD CONSTRAINT no_overlap_{owner}_interval
                EXCLUDE USING gist (
                  {owner}_id WITH =,
                  tsrange(starts_at AT TIME ZONE 'UTC',
                          (starts_at AT TIME ZONE 'UTC') + INTERVAL '30 minutes', '[)') WITH &&
                ) WHERE (status = 'confirmed')
            """)
    else:
        raise RuntimeError('Appointment interval guards support SQLite and PostgreSQL only.')


def remove_guards(apps, schema_editor):
    if schema_editor.connection.vendor == 'sqlite':
        for action in ('insert', 'update'):
            schema_editor.execute(f'DROP TRIGGER IF EXISTS clinic_appointment_no_overlap_{action}')
    elif schema_editor.connection.vendor == 'postgresql':
        for owner in ('doctor', 'patient'):
            schema_editor.execute(f'ALTER TABLE clinic_appointment DROP CONSTRAINT IF EXISTS no_overlap_{owner}_interval')
        # btree_gist may be used by other applications; leave it installed.


class Migration(migrations.Migration):
    dependencies = [('clinic', '0003_cancellation_reason')]
    operations = [migrations.RunPython(install_guards, remove_guards)]
