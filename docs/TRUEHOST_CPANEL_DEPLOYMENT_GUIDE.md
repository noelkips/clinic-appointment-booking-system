# Truehost cPanel deployment guide

This project can run under cPanel's **Setup Python App** using Passenger. Deploy
it to a subdomain such as `appointments.example.com`; keep the Django application
directory outside `public_html`. The repository contains `passenger_wsgi.py`,
which imports the existing `config.wsgi:application` entry point.

## Confirm the hosting plan first

Ask Truehost to confirm all of the following for the specific account/plan:

- **Setup Python App** (CloudLinux Python Selector) and Passenger are enabled.
- A Python version compatible with the pinned packages in `requirements.txt` is
  available. The project was prepared for Python 3.13.12; don't select a different
  version without checking package compatibility.
- MySQL 8.0.16+ or MariaDB 10.5+ is available to this account. The project uses
  PyMySQL, a pure-Python driver, so no MySQL client compiler or headers are needed.
- The database uses the InnoDB storage engine and supports enforced `CHECK`
  constraints and stored generated columns. The appointment overlap protections
  depend on these features.
- SSH/Terminal is available if you want command-line deployment or GitHub-triggered
  deployment.

The cPanel deployment uses the Django MySQL backend. Django 5.2 supports MySQL
8.0.11+ and MariaDB 10.5+; this app requires MySQL 8.0.16+ because earlier MySQL
versions parse some `CHECK` syntax without enforcing it. Confirm the actual server
version and InnoDB support with Truehost. If the shared plan cannot meet these
requirements, use a compatible MySQL/MariaDB plan or VPS. PostgreSQL remains
supported for the existing Render setup and CI.

## 1. Create the subdomain and Python application

1. In cPanel, create the subdomain, for example `appointments.example.com`, and
   enable its SSL certificate. Wait until HTTPS works before serving the app.
2. Open **Software → Setup Python App → Create Application**.
3. Select a supported Python version. Set **Application root** to a private folder
   such as `savannah-clinic` (the full path is usually `/home/CPANEL_USER/savannah-clinic`),
   outside `public_html`.
4. Set **Application URL** to the new subdomain and its root path `/`.
5. Set startup file to `passenger_wsgi.py`, entry point to `application`, and a
   Passenger log path outside `public_html` if the form requests one.
6. Create the app. Record the virtual environment activation command shown by
   cPanel; it is specific to your account and selected Python version.

The application root must contain `manage.py`, `requirements.txt`, `passenger_wsgi.py`,
`config/`, `clinic/`, `templates/`, and `static/` directly. Avoid extracting the
repository into an extra nested folder inside the Application root.

## 2. Import the project

Use cPanel **Git Version Control** to clone the GitHub repository into the application
root, or upload the repository contents there. If the repository is private, set up
the GitHub SSH key/deploy key in cPanel first. Do not upload `.env`, local virtual
environments, database dumps, or secrets into a public web directory.

If the Python app created a placeholder `passenger_wsgi.py`, replace it with the
tracked repository version. cPanel's Python Selector supplies the virtual environment
to Passenger; the repository file adds the app root to Python's import path and loads
the Django WSGI application.

## 3. Create MySQL and configure secrets

In cPanel **MySQL Databases**, create a database and dedicated database user, then
grant that user all privileges on that database. cPanel usually prefixes the names
with the account username; use the full names displayed by cPanel. Require InnoDB
tables. Do not reuse the expired Render PostgreSQL URL. A PostgreSQL backup cannot
be restored directly into MySQL; transferring records would require a separate data
migration. A fresh database contains no users, doctors, schedules, or appointments.

The project supports a private `.env` file in its application root (`config/settings.py`
loads it). Create this file on the server, outside `public_html`, and set its
permissions to `600`. It is ignored by Git and excluded from the automated upload.
Use either this file for both Passenger and management commands, or set equivalent
variables in cPanel and provide the same environment to management commands.
Recommended `.env` values:

| Variable | Value |
| --- | --- |
| `DJANGO_SECRET_KEY` | A new, persistent random value generated privately with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | The exact subdomain, e.g. `appointments.example.com` (no scheme) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://appointments.example.com` |
| `DATABASE_URL` | `mysql://FULL_DB_USER:URL_ENCODED_PASSWORD@localhost:3306/FULL_DB_NAME` (use the host/port Truehost supplies) |
| `DJANGO_TRUST_PROXY` | Leave `False` unless Truehost confirms its proxy sanitizes and sets `X-Forwarded-Proto` correctly |
| `DEMO_SEED_ENABLED` | `False` |
| `DJANGO_ALLOW_SQLITE` | `False` |

Keep `DJANGO_SECRET_KEY` and `DATABASE_URL` out of Git, deployment logs, screenshots,
and chat. Never commit the production `.env` file.

## 4. Install and initialize

Open cPanel Terminal, activate the exact virtualenv command shown in **Setup Python
App**, then change directory to the application root. Run:

```bash
python -m pip install -r requirements.txt
python -m pip check
python -c "import pymysql, config, MySQLdb; print('MySQL driver ready')"
python manage.py check --deploy --fail-level WARNING
python manage.py migrate --noinput
python manage.py migrate --check
python manage.py collectstatic --noinput --ignore=src
python manage.py createsuperuser
```

Migration `0004` retains PostgreSQL/SQLite guards; `0005` adds a stored generated
active-slot column, an enforced check that confirmed starts are on the 30-minute
grid, and unique indexes for each doctor and patient slot. Together, these prevent
overlap for the app's fixed 30-minute slots and make cancelled appointments release
their slot. MySQL 8.0.16+ or MariaDB 10.5+ is required so the check is enforced.
The migrations fail on incompatible preexisting confirmed appointments rather than
silently changing them. `collectstatic` uses WhiteNoise and excludes the Tailwind
source directory.

### Optional fictional assessment seed

For a fresh database that should contain the fictional assessment dataset, use the
local-only `scripts/seed_truehost_demo.sh` file. It is ignored by Git because it
contains the three README demonstration passwords. Upload it privately to the app
root (outside `public_html`) using cPanel File Manager, then run
`bash scripts/seed_truehost_demo.sh` from the activated virtualenv and app root.
The script prints a read-only database inspection first and only proceeds after
you type the exact database name shown. It uses the existing ownership-checked,
transactional seeder, adds 27 fictional accounts and 100 sample appointments, and
then runs its read-only verifier. Other seeded accounts have unusable passwords;
the three primary accounts use the passwords listed in README. The command refuses
unmarked username collisions or mismatched existing credentials and never deletes
records. Remove the uploaded script immediately after it completes; do not commit
or leave it on the server. Use only for a fictional demo database, never for real
patient records.

The current hosted CI database job runs PostgreSQL. Before pointing the live app at
the new MySQL database, apply these migrations to a disposable MySQL 8.0.16+ database
with the same cPanel permissions and confirm they complete successfully.

This database configuration depends on the application invariant that confirmed
appointments start on a half-hour boundary and last exactly 30 minutes. The
database enforces the boundary and uniqueness; business validation enforces doctor
availability, advance notice and the rest of booking policy.

Restart the application from **Setup Python App**. If a restart button is unavailable,
Passenger commonly watches `tmp/restart.txt` under the application root; create/update
that file only after checking the path for your app.

## 5. Check the subdomain

Open these URLs over HTTPS and verify the responses:

- `https://appointments.example.com/health/` returns HTTP 200 with `{"status":"ok"}`.
- `https://appointments.example.com/accounts/login/` loads styles and permits login.
- The appropriate patient, doctor, and staff dashboards work.
- Doctor schedules and availability load; test booking, conflict prevention,
  cancellation, and rescheduling with disposable accounts/records.
- Static assets load from `/static/`; HTTP redirects to HTTPS without a redirect loop.

Check the Passenger error log and cPanel resource usage if it fails. Keep `DEBUG=False`;
do not expose detailed exception pages publicly. Confirm database backups and restore
procedures with the provider before using the app for real records.

## 6. Updates and automatic deployment

cPanel Git's **pull** workflow is manual: click **Update from Remote** and then
**Deploy HEAD Commit** in **Git Version Control**. cPanel's automatic push deployment
applies when you push commits to a cPanel-managed repository; it does not watch a
GitHub branch by itself. For updates from GitHub, either use the manual pull workflow
or configure a GitHub Actions SSH deployment after verifying cPanel SSH access.

An optional GitHub Actions workflow is included at
`.github/workflows/cpanel-deploy.yml`. It runs only after the `CI` workflow succeeds
on `main`, checks out that exact tested revision, copies the tracked source over
SSH (preserving the server-only `.env`), then runs
`scripts/cpanel-deploy-remote.sh` and restarts Passenger by touching `tmp/restart.txt`.
Configure these **repository Actions secrets** before enabling it:

| Secret | Value |
| --- | --- |
| `CPANEL_HOST` | SSH hostname from Truehost |
| `CPANEL_PORT` | SSH port from Truehost (often 22, but confirm) |
| `CPANEL_USER` | cPanel account username |
| `CPANEL_SSH_PRIVATE_KEY` | Private key whose public key is authorized for this cPanel account |
| `CPANEL_KNOWN_HOSTS` | Verified SSH host-key line for this host/port |
| `CPANEL_APP_ROOT` | Absolute app root, e.g. `/home/CPANEL_USER/savannah-clinic` |
| `CPANEL_VENV` | Absolute cPanel virtualenv path shown by Setup Python App |

First deploy manually and confirm the hostname, SSH key, app root, virtualenv, private
`.env`, and Passenger restart work. Then add the Actions secrets and set the repository
Actions variable `CPANEL_DEPLOY_ENABLED` to `true`; until then the deploy job is
skipped. The workflow uses strict host-key checking, never uploads the `.env`, and
does not delete files from the app root. The SSH key should be limited to this cPanel
account; protect `main` with review and required CI checks. The remote script stops
on any failed command so a failed migration or static build does not restart the app.

Use additive, backward-compatible database migrations. A code rollback does not
reverse database migrations; keep backups and a tested restore process.
