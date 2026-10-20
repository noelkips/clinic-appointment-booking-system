# Local development and database operations

Consolidated from the detailed README on 20 October 2026. Historical test figures remain labeled; current production/CI status is in [the Render guide](RENDER_DEPLOYMENT_GUIDE.md). Use `collectstatic --noinput --ignore=src` for production; Tailwind source is not a deployable CSS asset.

## 10. Local development setup (Windows)

These steps are for a **new environment**. The existing populated database is already configured; do not recreate it or rerun seeding to read this documentation.

Prerequisites: Git, Python 3.13, a running PostgreSQL server and command-line tools in PATH, and the matching Tailwind standalone binary if rebuilding CSS. No Node.js or package manager is required. Use PostgreSQL administrator credentials only for provisioning.

```powershell
git clone https://github.com/noelkips/clinic-appointment-booking-system.git
Set-Location clinic-appointment-booking-system\clinic-appointment-booking-system
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the example only if `.env` does not already exist. Paste the generated secret privately into `DJANGO_SECRET_KEY`. If PowerShell activation is restricted, use `.\.venv\Scripts\python.exe` instead of `python` without changing machine policy.

Install PostgreSQL locally with its Windows installer, retain the administrator credential privately, start the Windows PostgreSQL service, and add its `bin` directory to PATH if needed. Verify `psql --version` and `pg_isready -h 127.0.0.1 -p 5432`. Then open SQL Shell or `psql -U postgres -d postgres`. For a fresh database, use interactive SQL/psql commands:

```sql
CREATE ROLE clinic_local LOGIN;
\password clinic_local
CREATE DATABASE clinic_local OWNER clinic_local;
\connect clinic_local
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

`\password` prompts without embedding secrets in history. Inspect existing roles/databases instead of repeating CREATE. Configure `.env` with your connection (Section 11); local PostgreSQL authentication must permit the role to connect. Test privileges are separate (Section 14).

```powershell
python manage.py check
python manage.py showmigrations clinic
python manage.py migrate --plan
python manage.py migrate
python manage.py createsuperuser
```

A fresh database needs Doctor profiles and DoctorAvailability periods through `/django-admin/` or deliberately enabled local demo data. Migration `0004` installs overlap guards and checks preexisting conflicts; investigate conflicts rather than deleting appointments.

Compiled CSS is checked in. To rebuild, use the ignored `.local/tailwindcss.exe` (v4.1.18), or obtain a matching standalone Windows binary from Tailwind's release distribution and place it there:

```powershell
.\.local\tailwindcss.exe -i ./static/src/input.css -o ./static/css/tailwind.css --minify
python manage.py collectstatic --noinput --ignore=src
python manage.py runserver 127.0.0.1:8000
```

The binary is not included in a fresh clone. `static/css/app.css` is a separate handwritten component stylesheet. Open `http://127.0.0.1:8000/`; stop Django with Ctrl+C.

## 11. Environment configuration

[Settings](../config/settings.py) load `.env` from the application directory; process environment values take precedence. Use these names, rather than unprefixed `SECRET_KEY`, `DEBUG` or `ALLOWED_HOSTS`:

| Supported variable | Development | Production |
|---|---|---|
| `DJANGO_SECRET_KEY` | Private generated value; required | Distinct strong secret in provider configuration |
| `DJANGO_DEBUG` | `True` | `False` (default) |
| `DATABASE_URL` | Local PostgreSQL URL | Provider-managed PostgreSQL URL |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Actual hostnames without scheme; defaults are local-only |
| `DEMO_SEED_ENABLED` | `False` unless deliberately seeding fictional data | `False` |
| `DJANGO_ALLOW_SQLITE` | Diagnostic fallback only; exact `True` plus debug required | `False`; use PostgreSQL |

Illustrative `.env`; replace placeholders privately:

```dotenv
DJANGO_SECRET_KEY=<generated-private-secret>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://clinic_local:<url-encoded-password>@127.0.0.1:5432/clinic_local
DEMO_SEED_ENABLED=False
DJANGO_ALLOW_SQLITE=False
```

Percent-encode reserved characters in username/password components, not the entire URL: `@` becomes `%40`, `:` becomes `%3A`, `#` becomes `%23`. Do not put credential-bearing URLs in reports/logs.

`SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS` are Django setting names. Use the prefixed environment names in `.env.example`. `DJANGO_CSRF_TRUSTED_ORIGINS` accepts comma-separated HTTPS origins; it defaults to empty for same-origin operation. `DJANGO_TRUST_PROXY=True` trusts `X-Forwarded-Proto` only behind a proxy that strips/replaces incoming forwarding headers; leave it False on a direct local server. Render's `RENDER_EXTERNAL_HOSTNAME` is added to allowed hosts automatically. Debug-off settings enable HTTPS redirect, secure cookies, and one-hour host-only HSTS. See the deployment guide for policy and verification.

The seeder separately reads `DEMO_PASSWORD` (or a hidden prompt); explicit rotation can read `DEMO_PREVIOUS_PASSWORD`. Neither belongs in tracked files or production configuration.

## 12. Database management

Read-only diagnostics from the application directory:

```powershell
python manage.py check --database default
python manage.py showmigrations clinic
python manage.py migrate --plan
python manage.py inspectdb clinic_appointment
python manage.py dbshell
```

Inside `dbshell` (psql):

```sql
\conninfo
\dt
\d clinic_appointment
SELECT extname FROM pg_extension WHERE extname = 'btree_gist';
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'clinic_appointment'::regclass AND contype = 'x';
```

Apply pending migrations intentionally with `python manage.py migrate`. An appropriately privileged owner/administrator can enable `CREATE EXTENSION IF NOT EXISTS btree_gist;` on a new database; migration `0004` also requests it. Functional verification recorded both `no_overlap_doctor_interval` and `no_overlap_patient_interval`.

For a local backup, use an ignored path and interactive password prompt:

```powershell
New-Item -ItemType Directory -Force .local\backups | Out-Null
$backupFile = '.local\backups\clinic-local-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.dump'
pg_dump -h 127.0.0.1 -p 5432 -U clinic_local -W -Fc -d clinic_local -f $backupFile
pg_restore --list $backupFile
```

Check each exit code and retain backups securely. Listing an archive is not a restore test. Verify restoration in a **new, uniquely named disposable database**, using a role with CREATEDB:

```powershell
createdb -h 127.0.0.1 -U clinic_local -W clinic_restore_review
pg_restore -h 127.0.0.1 -U clinic_local -W --exit-on-error --no-owner -d clinic_restore_review $backupFile
```

Stop if that name already exists. Check extension privileges, tables, counts and application behavior on the restored copy. Never point a verification restore at populated development/production data. These operational examples were reviewed, not executed during this documentation task.

No separate PostgreSQL cheat sheet exists in the current repository. These concise procedures are the available database guide; historical reports are not a current operational runbook.

## 13. Demonstration data

The [seeder](../clinic/management/commands/seed_demo.py) creates 27 marked fictional accounts (2 administrators, 5 doctors, 20 patients), 49 working periods, 100 appointments and 115 booking/cancellation events on a fresh dataset. Fifteen appointments are cancelled. Recorded development data also has one additional patient, with 100 appointments and 115 events overall.

```powershell
python manage.py seed_demo --help
```

For a new disposable **local debug** database only, deliberate seeding requires `DEMO_SEED_ENABLED=True`, a loopback host and a password from a hidden prompt/private `DEMO_PASSWORD`. The command is `python manage.py seed_demo`; it is unnecessary for this populated environment. Disable the flag afterward. Never seed production.

The command marks owned accounts, refuses colliding unmarked usernames, preserves unrelated users and uses `set_password`. Existing marked accounts must authenticate with the supplied password; ordinary reruns preserve hashes. Existing demonstration visits are identified by patient/consultation marker and retained, so dates do not silently roll forward. Explicit reset/rotation options in command help are not routine setup steps.

Private account details are in ignored `docs/LOCAL_TEST_ACCOUNTS.md`, if present; it is intentionally not a reviewer-facing link or tracked artifact. Usernames are `admin`/`admin2`, `doctor1`–`doctor5`, `patient1`–`patient20`. No passwords are published here.

## 14. Testing and quality assurance

Tests use a separate database, normally `test_clinic_local`, derived from the configured database name. Never set the test name to an existing development/production database. Use local test credentials only.

Django needs test-database creation permission. An administrator can deliberately grant it to a dedicated local role:

```sql
ALTER ROLE clinic_local CREATEDB;
```

This is a local testing privilege, not a production recommendation. The test database owner also needs permission to install `btree_gist`; arrange administrator provisioning if necessary. `config.test_settings` uses fast test-only hashing/plain static storage while retaining the configured backend. Never deploy it.

```powershell
# Full suite; seeder/rotation tests affect isolated test data only.
python manage.py test --settings=config.test_settings --verbosity 2

# Targeted PostgreSQL and functional regressions.
python manage.py test clinic.tests.ClinicTests clinic.tests.ConstraintTests clinic.tests.PostgreSQLConcurrencyTests clinic.test_remediation.RemediationTests clinic.test_remediation.IntervalConcurrencyTests clinic.test_functional_verification --settings=config.test_settings --keepdb --noinput --verbosity 1

python manage.py check
python manage.py makemigrations --check --dry-run
python -m pip check
```

Verbosity `0` is minimal, `1` summarizes, `2` lists tests/setup, `3` adds diagnostics. `--keepdb` retains the isolated test database between runs; individual tests still manage their fixtures.

### Recorded verification, not fresh executions by this documentation task

| Result | Provenance / scope |
|---|---|
| 80/80 PostgreSQL tests passed, including concurrency | Confirmed milestone supplied by the developer; the original PostgreSQL full-run log was not available in inspected artifacts |
| 60 targeted PostgreSQL tests passed, no skips | Functional verification: 4.563 seconds; both concurrency scenarios, direct SQL guards and three date-boundary regressions |
| 57 reversible database checks passed | Populated development PostgreSQL; rollback and original-record comparisons |
| 63 responsive browser viewport checks passed | Actual Chrome at 320/768/1440px; no horizontal overflow, JS exceptions or failed local HTTP responses |
| 7 browser interaction checks passed | Mobile menu, validation, slot fetch/selection, empty availability and authenticated redirect |

The earlier SQLite-era 80-test run had 79 passes and one PostgreSQL skip. It is a separate historical result. Three later boundary regressions also mean the current suite should not be described as exactly 80 tests without a new full run. No full suite/browser matrix was rerun for this documentation audit.

Full browser booking, cancellation confirmation and rescheduling submissions remain manually unverified on the current PostgreSQL revision. Older SQLite UI workflows do not establish those current flows. See [functional verification](APPLICATION_FUNCTIONAL_VERIFICATION.md) for scope and evidence locations.
