# Savannah Informatics Clinic Booking System

Django + Django REST Framework clinic scheduling, rendered with Django Templates, compiled Tailwind CSS, custom component CSS, and vanilla JavaScript. There are no React, Next.js, NPM, PNPM, or Yarn build dependencies.

## Verified local status — October 18, 2026

- Windows 11 Pro; Python 3.13.12; Django 5.2.18.
- Public landing page, doctor directory, centered authentication, and separate administrator, doctor, and patient workspaces are implemented.
- Local URL: http://127.0.0.1:8000/.
- PostgreSQL is the default/approved backend. It is **not installed or verified on this machine**. The current ignored `.env` explicitly enables SQLite for local demonstration. SQLite results do not verify PostgreSQL concurrency.
- 27 marked demo accounts, 100 seeded appointments, and 49 working periods were created. An additional non-demo patient account was preserved. Browser workflow checks created two additional cancelled appointments.
- 48 automated tests: 47 passed, one PostgreSQL concurrency test skipped. Real Chrome verification covered 120 page/viewport combinations and the patient booking/reschedule/cancel workflow.
- Render deployment and GitHub Actions are pending and unverified. This downloaded copy has no `.git` metadata; Git is not available on PATH.

## Windows setup

Run commands in the directory containing this README and `manage.py` (the inner `clinic-appointment-booking-system` directory).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated key into `.env`; never commit it. Activation is optional: use `.\.venv\Scripts\python.exe` directly if PowerShell activation is restricted. On this machine Python is installed at `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`.

The application loads `.env` through `python-dotenv` without overriding process environment variables. Required settings:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Random secret; startup fails if absent |
| `DJANGO_DEBUG` | `True` locally; defaults to `False` |
| `DJANGO_ALLOWED_HOSTS` | Local example: `localhost,127.0.0.1` |
| `DATABASE_URL` | PostgreSQL connection URL |
| `DEMO_SEED_ENABLED` | Explicit local-only seed permission; defaults to `False` |
| `DJANGO_ALLOW_SQLITE` | Diagnostic opt-in only; defaults to disabled |

Production uses `DJANGO_DEBUG=False`, secure cookies and manifest static storage. Do not deploy `.env`, demonstration data, credential references, or `config.test_settings`.

## PostgreSQL on Windows 11

1. Download a supported stable Windows x64 server installer from [PostgreSQL's official Windows download page](https://www.postgresql.org/download/windows/). That page links the EDB installer.
2. Install PostgreSQL Server and command-line tools, choose port `5432`, and set a private `postgres` administrator password. Retain the Windows service installation.
3. Open SQL Shell (psql), connect to localhost as `postgres`, and run:

```sql
CREATE ROLE clinic_local LOGIN CREATEDB;
\password clinic_local
CREATE DATABASE clinic_local OWNER clinic_local;
```

`CREATEDB` is for Django's local test database. Use a separate, least-privilege account for production. Choose a local password at the hidden prompt.

4. Set these values in the ignored `.env` (URL-encode special characters in the database password):

```dotenv
DATABASE_URL=postgresql://clinic_local:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/clinic_local
DJANGO_DEBUG=True
DJANGO_ALLOW_SQLITE=False
```

5. Verify the local Windows PostgreSQL service and connect:

```powershell
Get-Service *postgres*
# Adapt version/path if PostgreSQL was installed elsewhere.
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -U clinic_local -d clinic_local -c 'SELECT version();'
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py migrate
python manage.py test --settings=config.test_settings
```

The concurrency test executes only against PostgreSQL. Never point local commands at Render. Switching databases does not transfer existing SQLite records; rerun local seeding on the new database. Keep the existing SQLite file intact.

### Explicit SQLite diagnostic mode

If PostgreSQL and Docker are unavailable, `.env` may deliberately contain `DATABASE_URL=sqlite:///db.sqlite3`, `DJANGO_DEBUG=True`, and `DJANGO_ALLOW_SQLITE=True`. This is the current local demonstration configuration, not the approved final database configuration. SQLite is rejected without the explicit development opt-in.

## Migrations, demo data and startup

```powershell
python manage.py migrate --plan
python manage.py migrate
# Set DEMO_SEED_ENABLED=True in local .env before seeding.
python manage.py seed_demo
# Enter the supplied local demo password at the hidden prompt.
python manage.py runserver 127.0.0.1:8000
```

The seed command verifies 2 administrators (`admin`, `admin2`), 5 doctors (`doctor1`–`doctor5`), and 20 patients (`patient1`–`patient20`). It creates a Git-ignored `docs/LOCAL_TEST_ACCOUNTS.md` containing the actual credentials. The shared password is intentionally absent from tracked source and documentation.

Seeding is restricted to debug mode, explicit enablement, and a loopback/local database. Users must carry the demo ownership marker; a colliding real username aborts the transaction. Repeated seeding does not duplicate records. `python manage.py seed_demo --reset-passwords` deliberately refreshes only marked demo passwords. Use the original password on ordinary reruns. Seeded historical appointments remain historical; on subsequent days reruns preserve existing dates and changes rather than rewrite appointment history.

## Routes

| Route | Access / behavior |
|---|---|
| `/` | Public landing page |
| `/doctors/` | Public searchable doctor directory |
| `/doctors/<id>/` | Profile, split schedules, and available slots |
| `/accounts/login/` | Shared role-aware login |
| `/accounts/register/` | Patient-only registration |
| `/accounts/forgot-password/` | Coming Soon information; no reset email |
| `/dashboard/` | Patient workspace |
| `/doctor-dashboard/` | Doctor workspace |
| `/dashboard/redirect/` | Redirects to the user's role workspace |
| `/appointments/` | Role-scoped appointment records |
| `/appointments/book/` | Patient booking form |
| `/appointments/<id>/` | Authorized detail, cancellation and rescheduling |
| `/platform/` | Administrator metrics and analytics |
| `/platform/appointments/` | Search and doctor/patient/date/status filters |
| `/platform/doctors/` | Doctor directory and profile management |
| `/platform/patients/` | Restricted patient directory and history |
| `/platform/schedules/` | Schedule listing and non-overlapping period creation |
| `/platform/activity/` | Recorded appointment events and registrations |
| `/account/` | Authenticated account summary |
| `/django-admin/` | Optional Django maintenance interface |

Django Admin moved from `/admin/`; primary administration is `/platform/`. Doctors and patients receive HTTP 403 on administrator routes. Unauthorized appointment objects return 404.

## API and booking rules

Session authentication and CSRF protection apply. Both the existing `/api/` URLs and assessment root aliases are supported:

- `POST /appointments` (also `/api/appointments`)
- `GET /doctors/<id>/availability?date=YYYY-MM-DD` (also `/api/doctors/...`)
- `PATCH /appointments/<id>/cancel` (also `/api/appointments/...`)
- `PATCH /appointments/<id>/reschedule` (also `/api/appointments/...`)
- `GET /api/patients/<id>/appointments` (patient owner or administrator only)

Booking and rescheduling require an active, available doctor, a complete 30-minute slot within a working period, more than one hour of advance notice, and no doctor/patient conflict. Split-period gaps are excluded. Mutations use atomic transactions; parent-row locks serialize PostgreSQL booking writes, and conditional unique constraints provide a final SQL safeguard. Invalid input returns 400, unauthorized access 403/404, conflicts 409. Only patients and administrators can mutate upcoming confirmed appointments. Cancellation releases the slot. Past appointments cannot be modified through the application.

## Styling without Node

The official standalone Tailwind CLI **v4.1.18** was used successfully:

```powershell
.\.local\tailwindcss.exe -i ./static/src/input.css -o ./static/css/tailwind.css --minify
python manage.py collectstatic --noinput
```

Obtain that platform binary from the [official Tailwind standalone releases](https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.1.18). The binary is local-only and ignored. Included `static/css/tailwind.css` is compiled output; `static/css/app.css` remains the custom component design layer. The interface has not been converted entirely to Tailwind utilities. No NPM build step is needed.

Hero art, profile monograms, icons and branding are local CSS/SVG, with no external image or font dependency. Authentication uses an animated gradient rather than a photographic carousel; it respects reduced motion and pauses when hidden.

## Verification

```powershell
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --settings=config.test_settings --verbosity 1
```

`config.test_settings` uses fast test-only password hashing and plain static storage for isolated test databases. Application accounts use Django's normal password hashing. The full ordinary `manage.py test` command was also executed; it is slower because demo-account authentication uses the normal hasher.

Local Chrome evidence and the executable verification harness are in ignored `.local/browser/` and `.local/browser_verify.py`. Chrome checked 320, 375, 390, 768, 1024 and 1440px. The browser workflow creates a local cancelled verification appointment; it is separate from the 100 seeded appointments.

See `docs/IMPLEMENTATION_REPORT.md` for detailed evidence and the compliance matrix. PostgreSQL, deployed CI/CD, pagination at scale, full Tailwind conversion, and an operational password recovery service remain future work.
