# Savannah Informatics Clinic Booking System

A Django monolith for clinic appointment booking, migrated from the original Next.js visual prototype. Django Templates render the responsive dashboard; Django REST Framework exposes the booking API; PostgreSQL is the production database.

## Stack

- Python, Django, Django REST Framework, Django ORM
- PostgreSQL via `DATABASE_URL` (SQLite is available only as a local fallback)
- Django Templates, responsive CSS, vanilla HTML/SVG
- Gunicorn and WhiteNoise for Render deployment
- GitHub Actions for migrations and tests

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000`. Register a patient at `/accounts/register/`. Doctors, schedules, and appointments are managed in `/admin/`.

## API

- `POST /api/appointments`
- `GET /api/doctors/{id}/availability?date=YYYY-MM-DD`
- `PATCH /api/appointments/{id}/cancel`
- `PATCH /api/appointments/{id}/reschedule`
- `GET /api/patients/{id}/appointments`

Booking validation enforces a one-hour minimum lead time, doctor/patient ownership, and database-backed conditional uniqueness to prevent double booking. Appointment mutations run inside transactions.

## Styling

The checked-in `static/css/app.css` is deployable without Node. `static/src/input.css` is also provided for teams using the Tailwind standalone CLI; download and pin the official platform binary, then compile with `tailwindcss -i ./static/src/input.css -o ./static/css/app.css --minify` before `collectstatic`.

## Deployment and status

`render.yaml` provisions a Python web service and Render PostgreSQL database. `.github/workflows/test.yml` runs the Django test suite on pushes and pull requests. The visual dashboard, authentication, persistence, API endpoints, admin surface, deployment configuration, and representative tests are implemented. Remaining production work includes configuring Render secrets, loading real clinic seed data, and expanding role-specific doctor/admin screens and test coverage.
