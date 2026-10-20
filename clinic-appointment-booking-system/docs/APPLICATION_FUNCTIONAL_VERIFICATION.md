# Application functional verification

Verification date: 20 October 2026 (Africa/Nairobi).

**PASS: ready to proceed to GitHub Actions CI/CD implementation and Render deployment preparation.** This is a development functionality result, not production deployment approval. Browser submission of cancellation/rescheduling and production configuration checks remain outstanding below.

## Environment and data protection

- **PASS** Windows, Python 3.13 virtual environment, Django 5.2 application; PostgreSQL 18.6 at `127.0.0.1:5432`, database `clinic_local`. Runtime backend confirmed as `postgresql`.
- **PASS** `manage.py check`: no issues. Development server started on `http://127.0.0.1:8003` and served actual browser requests.
- **PASS** Existing data accessible: 5 doctors, 21 patients, 100 appointments, 115 appointment events. Final appointment/event counts remain 100/115.
- **PASS** Development migrations `0001` through `0004` already recorded as applied; no development setup, migration, reset, seeding or credential rotation performed.
- **PASS** Mutation probes ran inside one outer PostgreSQL transaction with explicit rollback. Before/after comparison of every field in User, Doctor, Patient, Appointment and AppointmentEvent matched. Rollback consumes sequence values; gaps in IDs are expected. Browser logins cause ordinary session/last-login writes, but do not edit clinical demo records.
- Regression tests used the separate `test_clinic_local` database with `--keepdb`. Django initialized its test schema on the first run; the populated development database was not migrated. No seeder tests were selected.
- No commit, push, production access or Render deployment performed. Existing unrelated working-tree changes preserved.

## Results by feature

| Area | Status | Executed evidence |
|---|---|---|
| Public landing, directory, profile, login, registration | PASS | Anonymous HTTP checks and actual Chrome navigation; profile availability rendered |
| Invalid URLs and dates | PASS | Unknown page 404; invalid availability date 400; missing doctor 404; maximum date boundary fixed and retested |
| Static and Tailwind assets | PASS | Chrome loaded app CSS, Tailwind CSS, JavaScript and branding; no failed local HTTP responses in the 63-page matrix |
| Role login and redirects | PASS | Existing `admin`, `doctor1`, `patient20` logged in through real forms; `patient19` also authenticated in transactional HTTP probes |
| Administrator management | PASS | Overview, appointments, doctors, patients, schedules, activity and account pages rendered; targeted tests cover filtering and metrics |
| Doctor workspace | PASS | Dashboard, assigned appointments, schedule and account pages rendered; isolation and patient API restrictions tested |
| Patient workspace | PASS | Dashboard, history/list, booking and account pages rendered; appointment isolation tested |
| Incorrect credentials, anonymous and cross-role access | PASS | Incorrect password stays on login form; protected HTML redirects; API anonymous requests 403; cross-role workspaces 403; unrelated appointment access 404 |
| CSRF and sessions | PASS | Enforced-CSRF clients reject tokenless HTML/API writes with 403; role login/redirect tests pass; patient logout redirects home and then blocks dashboard access |
| Registration | PASS | Registration page in browser; isolated regression creates patient-only account and tests role behavior |
| Availability and booking | PASS | 30-minute slots from existing schedule; successful 201 persisted in PostgreSQL and visible to patient, assigned doctor and administrator; booked slot removed |
| Conflicts and validation | PASS | Second patient same-slot 409; overlap rejected; adjacent slot 201; working-hour, notice, invalid timestamp and doctor validation 400; shifted-grid and exact-notice regressions pass |
| Cancellation | PASS | Missing, blank, non-string and overlong reason 400; valid trimmed reason persisted; cancelled status and history event stored; slot released; repeat cancellation 400; unauthorized patient 404 and doctor 403 |
| Rescheduling | PASS | Successful update occupies new slot and releases old one; conflict 409 leaves original start unchanged; cancelled appointment cannot reschedule; targeted doctor/patient overlap regressions pass |
| Database integrity/concurrency | PASS | `btree_gist` present; both native interval exclusions present; direct insert/update constraint and concurrent request regressions executed on PostgreSQL |
| Responsive layout | PASS | Actual headless Chrome at 320, 768, 1440px: 63 page/viewport combinations, no horizontal overflow, JS exceptions or local HTTP failures |
| Browser interactions | PASS | Seven checks: mobile menu opens/closes, empty booking form validation, availability fetch, slot selection, empty availability, authenticated login redirect |
| Full browser booking/cancel/reschedule submission | NOT TESTED | Real browser checks intentionally avoided persistent clinical writes; Django HTTP/API and isolated HTML regression tests exercised mutations |
| Physical devices / other browser engines | NOT TESTED | Chrome viewport emulation only |
| Password recovery delivery | NOT TESTED | Existing page explicitly says recovery is coming soon and refers users to administrator; no reset email workflow is implemented |

Expected rejected requests generated 400/403/404/409 development log entries, including Django PermissionDenied traces in DEBUG mode. These are intentional authorization probes. No unexpected server exception remained after the boundary fix.

## REST API verification

Actual primary paths have `/api` prefixes and **no trailing slash**. Root aliases also exist. Session authentication requires login and CSRF for unsafe methods.

| Method/path | Status | Verified behavior |
|---|---|---|
| `POST /api/appointments` | PASS | 201 with appointment representation; patient inferred from session; validation 400; booking conflict 409; unauthorized role 403 |
| `GET /api/doctors/{id}/availability?date=YYYY-MM-DD` | PASS | 200 with `date` and `slots`; booked intervals excluded; invalid date 400; unknown doctor 404; maximum date returns empty slots |
| `PATCH /api/appointments/{id}/cancel` | PASS | `reason` required; representation includes persisted cancellation reason/status; repeated cancellation rejected |
| `PATCH /api/appointments/{id}/reschedule` | PASS | `starts_at` validated; atomic success or unchanged original on conflict |
| `GET /api/patients/{id}/appointments` | PASS | Future confirmed appointments only; owner/administrator access; doctor/unrelated patient denied; ordering/filter regression executed |
| Root aliases | PASS | Existing API alias regressions plus live `/doctors/{id}/availability` transactional check |

Booking representations include `id`, `patient`, `doctor`, `starts_at`, `reason`, `cancellation_reason`, `status`, `created_at`. API status/error checks ran against Django's HTTP request stack connected to actual PostgreSQL; the browser additionally fetched live availability over HTTP from the development server.

## Database integrity and prior evidence

Verified `no_overlap_doctor_interval` and `no_overlap_patient_interval`: GiST exclusions combine the relevant foreign key with a UTC half-open 30-minute timestamp range, restricted to confirmed appointments. Database enforcement was preserved. Existing exact-start uniqueness remains in the model.

The user supplied the previous milestone result of 80 passing PostgreSQL tests. That historical run's log was not found in the inspected local evidence; the older `.local/remediation-tests.txt` instead records a SQLite-era run with one PostgreSQL skip. It is not used as current PostgreSQL evidence. This task independently executed both PostgreSQL concurrency tests in the targeted 60-test run with no skips, along with direct constraint insert/update tests.

## Defect discovered and fixed

**FAIL before fix / PASS after fix: availability on `9999-12-31` returned an unhandled OverflowError.** Both public doctor profile and authenticated API reproduced it. `available_slots` computed the next midnight beyond Python's representable date range. The shared service now returns an empty list for the final representable day, keeping both consumers consistent without changing normal schedules or booking rules.

Changed `clinic/services.py`; added `clinic/test_functional_verification.py` with service, public-profile and API-prefix regression tests. All three pass. Both live-database HTTP paths return 200 after correction, and actual Chrome navigation to the corrected public boundary page passes. No framework, architecture, migration or page redesign introduced.

## Executed checks and reproducibility

From the application directory:

```powershell
.venv/Scripts/python.exe manage.py test clinic.tests.ClinicTests clinic.tests.ConstraintTests clinic.tests.PostgreSQLConcurrencyTests clinic.test_remediation.RemediationTests clinic.test_remediation.IntervalConcurrencyTests clinic.test_functional_verification --settings=config.test_settings --keepdb --noinput --verbosity 1
```

**PASS: 60 tests in 4.563 seconds, zero failures/errors/skips.** Covers authentication/registration/CSRF, dashboards, booking, schedules, cancellation HTML/API, rescheduling, filtering, SQL enforcement, both concurrent request scenarios and the new date boundary. The separate initial boundary-only run also passed 3 tests in 0.152 seconds. Full suite and seeding tests were not rerun.

Additional **PASS** results: 57 reversible development-database checks; 63 browser page/viewport combinations; 7 browser interaction checks; corrected boundary browser navigation; system check and `git diff --check` (only existing line-ending conversion notices).

Local evidence (ignored, not deployment artifacts): `.local/task4_verify.py`, `task4-results.json`, `task4-regression.txt`, `task4-expected-http.log`, `task4_browser.py`, `task4-browser-results.json`, `task4_interactions.py`, `task4-browser-interactions.json`, `task4_edges.py`, `task4_browser_boundary.py` and `.local/browser/task4-*.png`. Credentials are read privately from the ignored account reference and never included in this report or emitted by probes. Early harness attempts failed on Python import-path setup, a seeded patient conflict, and a redirect wait assumption; corrected probes were rerun successfully. These harness issues are not counted as application defects or passing executions.

## Manual verification and remaining risks

- **NOT TESTED:** complete browser submission of booking, cancellation confirmation and rescheduling, with visual notification review. HTTP/API and isolated HTML regressions pass, but do not establish every browser interaction.
- **NOT TESTED:** logout through each role's visible menu, detailed keyboard/screen-reader review, physical devices, Safari/Firefox, loading animation timing and every empty dashboard variant.
- **NOT TESTED:** visual review of patient/doctor/admin dashboards after each reschedule in a shared live browser session. Authorization, persistence, slot release and shared-query behavior have automated coverage.
- **NOT TESTED:** GitHub Actions, production HTTPS/cookies, Render environment/static configuration, production database permissions and deployment health. These belong to the next milestone.
- Existing password recovery remains administrator-assisted. CI should include PostgreSQL and both concurrency tests; carry the new boundary regressions forward.

The verified application is ready for the next CI/CD preparation milestone. Complete the browser mutation checklist before calling end-to-end browser verification complete, and validate production configuration before releasing on Render.
