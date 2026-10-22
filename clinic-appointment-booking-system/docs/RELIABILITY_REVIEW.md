# Reliability and permissions review

Prepared on development, 22 October 2026. No push, merge or deployment performed. README and demo seeding are unchanged.

## Administrator booking failure

The repository intentionally implements patient-only creation. Public home CTAs and doctor slot links previously sent every role to `clinic.views.book`. Its role guard raises PermissionDenied before processing the form or calling a service. `clinic.services.role` prioritizes staff as administrator, even if a patient profile also exists. `book_appointment` independently enforces patient-only creation; `clinic.api.create_appointment` does the same. Administrators may inspect and change eligible existing appointments, but cannot create them. Doctors may inspect their own appointments, but cannot create or change them.

Web forms use Django session authentication, login_required and CSRF middleware. Anonymous web requests redirect to sign-in; an authenticated wrong-role request receives 403. The web form calls the locked service directly, rather than POSTing to DRF. The slot picker fetches the authenticated GET availability endpoint. DRF independently authenticates the session, checks IsAuthenticated and enforces CSRF on unsafe authenticated requests, before the endpoint/service checks roles and validates slots. A missing/expired API session now returns 401 with `WWW-Authenticate: Session`; wrong-role or missing-CSRF requests remain 403. Session challenge adds no new authentication mechanism or CSRF exemption.

This reproduces the administrator denial from source and automated role tests. No live account, Render log or deployed revision was inspected, so the precise live request and possible additional CSRF/proxy failures cannot be certified. There is no evidence justifying broader administrator booking rights.

## Changes and contracts

- `clinic/errors.py`: shared safe HTML/JSON responses, DRF exception handler, session challenge, response normalization for both `/api/?` and the existing unprefixed API routes, unsupported-method handling and database/unexpected-error boundaries. Preserve Allow and Retry-After headers. Server diagnostics remain in server logs only.
- `config/settings.py`, `config/urls.py`: middleware, CSRF failure view and Django error handlers.
- `templates/errors/error.html`: responsive, accessible standalone branded error page. It renders without user/profile context or database lookups. Production manifest assets are required as with existing templates.
- `clinic/views.py`, `clinic/forms.py`: bound empty POST forms, retained field values/time selection, HTML 400 validation and 409 conflicts, retained cancellation/reschedule feedback. Existing success messages and redirect-after-success behavior remain.
- `templates/public/home.html`, `templates/public/doctor.html`: patient/anonymous booking CTAs; explicit patient-only guidance for other roles.
- `templates/appointments/detail.html`: retain rescheduling inputs; show errors even when an appointment can no longer be changed.
- `templates/public/base.html`, `templates/registration/login.html`: public notifications and expired-session guidance.
- `static/js/app.js`: selected slot restoration, session/cold-start availability guidance, POST double-submit guard, accessible submitting notice and back/forward reset. Availability requests are read-only; mutations are never automatically retried.
- `config/health.py`: public GET/HEAD process liveness, `{"status":"ok"}`, no-store, zero database queries; other methods return 405. This deliberately does not claim database readiness.
- Tests: `clinic/test_reliability.py`, existing permission/cancellation assertions in `clinic/tests.py`, `clinic/test_remediation.py`, and health tests in `config/test_production.py`.

API errors use `{"error":{"code":"invalid_request","message":"?","details":{"field":["?"]}}}`. Status/code pairs: 400 invalid_request, 401 authentication_required, 403 permission_denied (csrf_failed for CSRF), 404 not_found, 405 method_not_allowed, 409 appointment_conflict, 429 too_many_requests, 500 server_error, 503 service_unavailable. Existing successful payloads are unchanged. API clients consuming old top-level error fields must read error.details instead. No application throttling existed; 429 rendering and Retry-After preservation are supported without adding an arbitrary new throttle policy.

Service rules, atomic transactions, parent-row locks, overlap checks and PostgreSQL exclusion/uniqueness constraints are unchanged. Existing tests cover occupied and overlapping slots, past/one-hour restrictions, rescheduling validation, ownership, repeated cancellation and concurrent writes. Cancellation remains allowed for future confirmed appointments under the existing rule; the one-hour requirement applies to the new appointment time, not an invented cancellation cutoff.

## Render and deployment

[Render free-service documentation](https://render.com/docs/free) confirms spin-down after 15 idle minutes and a cold start of about one minute. Render serves its own loading page before Django can run. Application HTML/JS cannot replace that pre-start response. Wait for startup; after a failed booking submission, inspect your appointments before retrying. A lightweight health URL does not keep a suspended process running. No self-pinging thread, scheduler, uptime service or recurring workflow was added.

No new environment variables, migrations or dependencies are required. Keep production DJANGO_DEBUG=False, HTTPS cookies/proxy configuration and trusted origins correct for the actual hostname. Existing Render healthCheckPath is already `/health/`. Use the existing build command, including `collectstatic --noinput --ignore=src`; collecting Tailwind source input without that exclusion fails on its build-time import. The blueprint's branch/deployment trigger were deliberately left unchanged; review the intended revision and deployment settings before a later authorized deployment.

## Manual browser checks

1. Administrator: sign in, open home and a doctor profile; see patient-only guidance and no booking links. Direct `/appointments/book/` returns a friendly 403. Platform appointment inspection and permitted reschedule/cancellation still work. Direct POST `/api/appointments` with a valid session/CSRF token returns JSON 403.
2. Doctor: home/profile offer patient-only guidance. Direct booking is 403. Own dashboard appointments remain visible; changing an appointment is forbidden, and other users' appointments remain hidden.
3. Patient: book a future available slot more than one hour ahead. Confirm success notification and persistence. Reschedule, then cancel with a reason. Try a blank reason, invalid date/time, occupied slot, past time and within-hour time; expect actionable errors and retained inputs. Cancel again via direct request; expect 400 and no extra event. Open two sessions on the same slot; only one booking succeeds.
4. Signed out/expired: web booking redirects to sign-in with guidance; API mutations return 401. Sign in then expire/delete the session cookie and retry availability. Remove a CSRF token from an authenticated form: receive safe 403/reload guidance, with no write. A fresh page/token works.
5. Errors/accessibility: visit unknown HTML and API URLs, try an unsupported method, and inspect correct statuses/content types. Tab through recovery links, use a screen reader for notices, and check narrow mobile widths. Rapid double-click submits once; navigating back restores usable controls. Server/database failure injection belongs in automated/local testing, not public endpoints.
6. Health/cold start: GET and HEAD `/health/` succeed; POST is 405. After idle suspension, expect Render's loading page and wait. Do not automatically replay a mutation after a network failure.

## Verification

- Complete PostgreSQL suite: `.venv\Scripts\python.exe manage.py test --settings=config.test_settings --noinput` ? **119 tests passed**, 52.256 seconds. Includes existing PostgreSQL exclusion/uniqueness and concurrent booking regressions. No tests skipped in this run.
- Production settings (`DJANGO_DEBUG=False`): `check --deploy --fail-level WARNING` passed. The two preexisting intentional HSTS suppressions (`security.W005`, `security.W021`) are unchanged; their rationale remains in settings.
- `makemigrations --check --dry-run`: no changes detected. `migrate --check`: passed without applying migrations.
- Manifest collection using the existing build's `--ignore=src`: passed in isolated ignored `.local/reliability-static`. Production HTTPS smoke checks for health and HTML/API 404s passed.
- `pip check`: no broken requirements. `git diff --check`: passed. Branch remains development; README, management commands and build/seeding scripts have no diff.
- Local ignored evidence: `.local/reliability-tests.txt` and `.local/reliability-production.txt`. Expected error-injection tests log their synthetic exception details to server logs; response assertions confirm those details never reach users.

Browser/accessibility checks and Render execution remain manual; no claim of live deployment verification is made. No load or penetration testing was performed. API error-envelope and anonymous-status changes are deliberate compatibility changes for clients. The health endpoint tests process liveness only, not database availability.
