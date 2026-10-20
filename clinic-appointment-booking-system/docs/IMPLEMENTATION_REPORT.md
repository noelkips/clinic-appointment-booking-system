# Implementation report

> Current status: the October 19 targeted remediation section at the end supersedes the original API/test/credential findings. Local suite: 80 tests, 79 passed, zero failures/errors, one PostgreSQL skip. Delivery and reflection gaps remain.


## Historical note
The original sections below preserve implementation history and prior intentions. Their security, CI/CD and validation claims were not all verified. The dated local verification report appended below supersedes those claims; this download has no GitHub Actions workflow or Git metadata.

## Migration
The original React/Next.js dashboard was replaced with a Django monolith. The visual reference was translated into Django templates and reusable CSS rather than copied as JSX. Next.js source, package manifests, and Node build configuration are obsolete and should be removed from the repository after review.

## Architecture
`config/` contains settings, URLs, and WSGI. `clinic/` contains ORM models, forms, server views, DRF API views, admin registrations, and tests. `templates/` contains the base layout, dashboard, booking, login, and registration views. Production uses PostgreSQL from `DATABASE_URL`, Gunicorn, and WhiteNoise.

## Database and booking rules
Doctor, Patient, DoctorAvailability, and Appointment models use Django ORM. Conditional unique constraints prevent two confirmed bookings for the same doctor/time or patient/time. `full_clean()` and transaction handling enforce the one-hour lead-time rule and validate mutations.

## API/authentication
The five required routes are present, including patient appointment listing. Django session authentication protects the API. Patients register and book; doctors and administrators use Django roles and the admin interface. Object-level checks protect cancel, reschedule, and patient listing operations.

## Frontend migration
The responsive sidebar, clinic header, metric cards, schedule, activity SVG, booking page, authentication forms, alerts, and empty states are rendered by Django Templates. Metrics and appointment rows are queried from the database.

## Validation
Automated tests cover persistence, duplicate booking rejection, and availability. GitHub Actions runs migrations and `manage.py test`. Local validation should run `pip install -r requirements.txt`, `python manage.py migrate`, and `python manage.py test`.

## Known limitations / remaining work
Render environment variables and production domain settings must be configured. The activity chart is intentionally a lightweight presentation chart and should be wired to an aggregated activity query when reporting requirements are finalized. Expand doctor-specific schedules, richer admin permissions, seed data, and integration tests before handling real patient data. Tailwind standalone CLI compilation is documented; the checked-in CSS remains usable if the binary is not available locally.

---

# Local Environment Audit and Verification

Audit and enhancement date: **October 18, 2026**, Africa/Nairobi. Windows 11 Pro 64-bit. Python 3.13.12, Django 5.2.18, DRF 3.18.3. PostgreSQL version: unavailable; no local installation or Docker was found. No production database or Render service was contacted.

## A. Executive Summary

Implemented a public clinic website, redesigned authentication, role-specific workspaces, administrator management pages, safe demo seeding, and the authorization/booking repairs required before populating patient records. The Django application starts at http://127.0.0.1:8000/.

**The local UI and functional milestone is verified on explicitly enabled SQLite. The full approved PostgreSQL milestone remains incomplete.** No PostgreSQL concurrency, Render deployment, or CI/CD success is claimed.

The project is inside the inner `clinic-appointment-booking-system` directory. A working Python installation, virtual environment, and requirements were established. Workspace write access was confirmed before this implementation. No `.git` metadata exists in the downloaded copy and Git is unavailable on PATH, so a working-tree diff/commit could not be produced. Existing source and data were inspected and preserved except for identified obsolete prototype configuration.

## B. Files Changed

Important additions:

- `clinic/services.py`: shared authorization, availability and atomic booking/cancellation/rescheduling.
- `clinic/management/commands/seed_demo.py`: protected, idempotent development dataset command.
- `clinic/migrations/0002_appointmentevent_alter_doctoravailability_options_and_more.py`: split periods, schedule constraints, biography, event model.
- `config/test_settings.py`: isolated test configuration with fast hashing.
- `templates/public/`: landing page, directory, profiles, doctor cards and public layout.
- `templates/platform/`: overview, appointment management, doctor management, patient profiles, schedules and activity.
- `templates/partials/`: appointment tables, working periods, actual event lists, chart rendering, SVG icons and form errors.
- `static/js/app.js`, `static/brand.svg`, `static/css/tailwind.css`, `.env.example`.

Modified: `clinic/models.py`, `clinic/forms.py`, `clinic/views.py`, `clinic/api.py`, `clinic/urls.py`, `config/settings.py`, `config/urls.py`, `clinic/tests.py`, authentication and dashboard templates, booking templates, `static/css/app.css`, `requirements.txt`, `.gitignore`, and README.

Removed after confirming they were unused by Django: `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `next.config.mjs`, `postcss.config.mjs`, `tsconfig.json`, `components.json`, and `lib/utils.ts`. No Node dependencies were installed. Django migration history and the existing SQLite database were retained.

Local-only, ignored artifacts: `.env`, `.venv/`, standalone Tailwind executable, Chrome screenshots and JSON evidence under `.local/`, generated static files, SQLite databases, and `docs/LOCAL_TEST_ACCOUNTS.md`.

## C. Landing Page

Public `/` now contains responsive navigation, a teal/sage hero, original CSS healthcare illustration, appointment CTA, searchable doctor navigation, real database doctor previews, three-step booking guidance, a clearly labeled illustrative appointment preview, closing CTA, and footer.

Doctor names, biographies, specializations and availability actions come from database profiles. Profile artwork uses monograms and original local illustration, not purported real doctor photographs. No testimonials, accreditations, clinical outcomes, or fabricated trust metrics were added. Public links lead to implemented pages; protected booking preserves the intended authorized destination through login.

## D. Authentication

`/accounts/login/` is the consistent application login for all roles. The centered card uses an original animated gradient backdrop rather than third-party imagery. CSS respects reduced motion; JavaScript pauses animation when the document is hidden. Features include labeled username/password fields, visibility toggle, field and credential errors, secure session-duration selection, account registration and home navigation.

`/accounts/register/` creates only ordinary users and Patient profiles, atomically. Public input cannot assign staff or doctor roles. Django password validation and hashing are used.

`/accounts/forgot-password/` displays the requested Coming Soon information; it sends no email and invents no administrator contact details.

Login routes administrators to `/platform/`, doctors to `/doctor-dashboard/`, and patients to `/dashboard/`. External and incompatible role destinations are rejected. Django's optional maintenance interface is at `/django-admin/`. Logout uses CSRF-protected POST.

## E. Administrator Dashboard

All `/platform/` routes require authenticated staff access. Doctors and patients receive 403.

Implemented navigation/pages:

| Route | Implemented behavior |
|---|---|
| `/platform/` | Live metrics, charts, upcoming visits, event activity and registrations |
| `/platform/appointments/` | Search; doctor, patient, date and status filters; detail links |
| `/platform/doctors/` | Biographies, specialties, availability state and appointment counts |
| `/platform/doctors/<id>/` | Edit doctor specialty, biography and booking availability |
| `/platform/patients/` | Searchable private directory, registration dates, appointment counts |
| `/platform/patients/<id>/` | Profile and appointment history |
| `/platform/schedules/` | Working-period listing and validated non-overlapping period creation |
| `/platform/activity/` | Real recorded appointment events and patient registrations |
| `/account/` | Authenticated identity, role, registration date and maintenance link for staff |

Metrics derive from ORM queries: patient count, doctor count, appointment count, upcoming confirmed visits, today's confirmed visits, confirmed/cancelled status totals, and doctors with appointment records.

Database-driven charts show scheduled appointments and cancellations over the last seven days, bookings by creation date, upcoming distribution over the next seven days, and doctor totals/upcoming counts. Zero data produces real empty/zero states rather than presentation numbers.

`AppointmentEvent` records successful application booking, rescheduling and cancellation mutations within the same transaction. Historical demo events are explicitly part of the fictional seeded dataset. The interface does not fabricate rescheduling events or reconstruct them from status alone. Direct maintenance edits are not a complete audit trail.

## F. Doctor and Patient Dashboards

Doctors see only assigned appointment records, today's counts, upcoming appointments, status/history and working periods. They cannot retrieve patient-wide API lists or mutate bookings through the patient management actions.

Patients see only their own metrics, upcoming visits and history. The doctor/date form fetches real available slots, then the server revalidates on submission. Appointment details support valid future rescheduling and cancellation. Released slots become available again. Historical visits are labeled by timestamp rather than inventing a completed status.

Every protected appointment lookup uses role-scoped queries. Unauthorized records are not returned even when the caller knows an ID. Shared responsive navigation collapses into an accessible toggle on smaller screens, and tables scroll within their own container.

## G. Demonstration Data

The idempotent command created **27 marked demo users**:

- 2 administrators.
- 5 doctors and profiles, covering General Medicine, Pediatrics, Dermatology, Cardiology and Orthopedics.
- 20 patients and profiles.
- 49 working periods across seven weekdays; the first two doctors have morning and afternoon periods.
- 100 fictional appointments across past, current and future dates, with varied booking dates and 15 seeded cancellations.

Live database totals after two browser workflow verifications:

| Record | Count |
|---|---:|
| Users | 28 |
| Demo users | 27 |
| Administrators | 2 |
| Doctors | 5 |
| Patients | 21 |
| Demo patients | 20 |
| Working periods | 49 |
| Appointments | 102 |
| Seeded appointments | 100 |
| Cancelled appointments | 17 |
| Upcoming confirmed appointments | 47 |
| Appointments scheduled today | 5 |
| Appointment events | 121 |

One non-demo patient account was preserved. Two extra cancelled appointments were created by real browser booking/rescheduling/cancellation checks. Future/today counts are time-dependent and reflect the verification time on October 18.

Active doctor/time and patient/time duplicates were checked. Every scheduled timestamp was checked against the configured working periods. Historical demo insertion deliberately permits past timestamps while enforcing valid working slots; normal booking cannot create historical visits.

Repeated seeding preserved 27 demo accounts and 100 seeded appointments. Reruns retain existing appointment dates/history. To roll a dataset forward after time passes, a future explicit refresh/archive design is needed; seeding does not silently rewrite history.

## H. Test Accounts

Actual username login identifiers: `admin`, `admin2`, `doctor1`–`doctor5`, and `patient1`–`patient20`. All are active. Doctors and patients have the appropriate one-to-one profiles.

The local shared password and full name/role table are in **Git-ignored** `docs/LOCAL_TEST_ACCOUNTS.md` and provided directly in the conversation. The password is not embedded in source, README, or this tracked report. The command reads a hidden prompt or process `DEMO_PASSWORD`, uses `set_password()`, and authenticates the accounts.

Seeding requires debug mode, explicit `DEMO_SEED_ENABLED`, and a loopback/local database. A preexisting unmarked username aborts the entire transaction. Password refresh requires deliberate `--reset-passwords`; real accounts are never updated.

## I. Database and Migrations

PostgreSQL remains the approved default backend. `DATABASE_URL` is loaded from process environment or local `.env`; SQLite is rejected unless debug mode and explicit diagnostic opt-in are both enabled. The local `.env` deliberately enables SQLite because no local PostgreSQL or Docker is available. PostgreSQL connection attempts time out; no PostgreSQL version or migration result is claimed.

Migration `0001_initial` was already applied to SQLite. Migration `0002` was inspected, planned and applied successfully without resetting/deleting data. It removes the old one-period-per-weekday restriction, adds positive-duration/weekday/30-minute constraints and unique schedule starts, adds doctor biography and records appointment events. Existing conditional doctor/time and patient/time uniqueness constraints remain.

`makemigrations --check --dry-run` reports no missing model migrations. `manage.py check` and `pip check` pass. `collectstatic --noinput` copied 159 files.

Booking and changes run in `transaction.atomic()`. PostgreSQL `select_for_update()` locks doctor/patient parent rows before checking availability. SQLite cannot validate the effectiveness of those locks. A real two-thread PostgreSQL test exists and is skipped on SQLite.

README includes exact Windows PostgreSQL installation, local role/database, environment, migration, and testing instructions using the official Windows installer entrypoint: https://www.postgresql.org/download/windows/. No paid or production resources were provisioned.

## J. Automated Tests

Final complete suite:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings --verbosity 1
```

**48 tests executed: 47 passed, 0 failed, 1 skipped.** The skipped test requires a real PostgreSQL test database and checks two concurrent requests for the same slot.

The ordinary `manage.py test` command also completed on the earlier 45-test revision: **44 passed, 0 failed, 1 skipped**, in 385.252 seconds. The final test configuration uses a fast hasher only for isolated tests; persistent account authentication was separately verified with the normal application hasher.

Coverage includes role login redirects, invalid login, unsafe/incompatible destinations, patient-only registration, anonymous protection, administrator page permissions, patient and doctor isolation, patient-list API restrictions, booking persistence, doctor and patient conflicts, absent working hours, split gaps, off-grid/partial slots, past/one-hour restrictions, unavailable and invalid doctors, malformed timestamps/dates, schedule overlap and missing fields, cancellation slot release, aware rescheduling and rollback, forbidden mutations, cancelled-record restrictions, assessment API aliases, actual metrics/filtering, CSRF, database uniqueness, and demo seeding/idempotence/password safety.

Initial test failures exposed a missing manifest asset and DRF uniqueness validation returning 400 before the service could return 409. Static handling was corrected and duplicate-slot handling moved consistently into the locked service. Later browser attempts exposed stale server state and a verification-harness cookie precondition; the process/harness were corrected and the final checks passed.

## K. Browser Verification

Real installed Chrome ran headlessly through the Chrome DevTools Protocol, using an isolated local profile. This was browser verification, not just HTTP requests.

**120 page/viewport combinations** checked at **320, 375, 390, 768, 1024 and 1440px**, plus a complete patient workflow:

- Public home, login, registration, Coming Soon, doctor directory and doctor profile.
- Administrator overview, appointments, doctors, patients, schedules, activity and account.
- Doctor overview, appointment listing and account.
- Patient overview, appointment listing, booking and account.

Final run: **0 horizontal-overflow assertions, 0 JavaScript exceptions, 0 HTTP errors**. Mobile menu expansion, password visibility and reduced-motion styling were exercised. The patient HTML forms completed booking → dashboard confirmation → detail → rescheduling → cancellation. Two complete workflow runs left two clearly labeled, cancelled verification appointments.

Screenshots were captured at all six widths; landing, login and administrator screenshots were visually inspected at desktop/mobile sizes. Local evidence: `.local/browser/results.json`, `.local/browser/*.png`, `.local/browser_verify.py` and `.local/final_verification.json`. These artifacts are intentionally ignored. Verification covers Chrome; other browser engines and real mobile virtual keyboards were not tested.

## L. Security Review

The original vulnerabilities are repaired and regression-tested:

- Another patient's appointment is excluded from patient dashboard/list/detail queries.
- Doctors are denied patient-wide API lists and only see assigned appointments.
- All administrator views require staff access; patient directories/activity are never public.
- Public registration cannot assign elevated roles.
- External/incompatible login redirects are rejected.
- Session-authenticated mutations require CSRF tokens.
- Invalid schedule/time/doctor input is rejected server-side; duplicate slots return 409.
- Cancellation and rescheduling are atomic and ownership-checked.
- Secrets and demonstration credentials are excluded from source and generated credential references are ignored.
- Error responses avoid exposing raw database exceptions.

PostgreSQL race behavior remains explicitly unverified until the skipped test runs against PostgreSQL. This is a functional/security regression review, not a comprehensive penetration test.

## M. Known Issues

1. **High:** PostgreSQL installation, connectivity, migration application and concurrency verification remain outstanding. Current local evidence uses explicit SQLite diagnostics.
2. **High for submission:** Restore a proper Git checkout; create and verify GitHub Actions and Render deployment in the final deployment phase. No deployment/CI/CD completion is claimed.
3. **Medium:** Schedule management supports adding validated periods; editing/removing periods and creating new doctor accounts remain maintenance tasks in Django Admin. A safe policy for changes affecting existing bookings is still needed.
4. **Medium:** Core design remains custom component CSS with compiled Tailwind utilities; full utility conversion is unfinished.
5. **Medium:** Password recovery is intentionally informational. No email reset service exists.
6. **Medium:** Patient/appointment directories are not paginated for large production datasets. Activity captures application events, not every direct ORM/maintenance change.
7. **Low:** Chrome-only responsive testing; Safari/Firefox, assistive-technology review and real-device keyboards remain unverified.
8. **Low:** Demo reruns preserve history and do not automatically roll dates forward. The sample roster is intentionally fictional and includes weekend schedules.

## N. Assessment Compliance

| Requirement | Evidence / status |
|---|---|
| Django + DRF + templates | Implemented; application and API tests pass |
| PostgreSQL | Configuration and locks implemented; actual local backend verification blocked |
| No React/Next/NPM/PNPM build | Obsolete manifests/configuration removed; Django runs without Node |
| Tailwind standalone / vanilla JS | Official v4.1.18 standalone compilation passed; custom CSS retained and identified |
| Authentication / role authorization | Tested for anonymous, patient, doctor and administrator requests |
| Public landing and auth redesign | Implemented, real browser screenshots and responsive checks |
| Custom administration | Implemented at `/platform/`; default admin retained for maintenance |
| One-hour / 30-minute / working-hour rules | API and service tests pass; split periods and gaps covered |
| Double-booking protection | Service checks and SQL constraints tested; PostgreSQL concurrency test pending |
| Required assessment API routes | Preserved under root aliases and existing `/api/` prefix |
| Cancellation / rescheduling | API and real HTML browser workflow verified |
| Protected realistic demo data | 27 marked users and 100 seeded appointments; reruns verified |
| Real dashboard/chart data | ORM-backed counts and time series; no hardcoded clinical metrics |
| Documentation / test credentials | README/report updated; credential reference generated and ignored |
| GitHub Actions on pull requests | Not implemented/verified in downloaded copy; final phase pending |
| Render / successful-check deployment | Not provisioned or verified; final phase pending |

## O. Recommended Next Steps

1. Install local PostgreSQL using README, configure a loopback-only development database, migrate and seed it, then run the entire suite including the concurrency test.
2. Restore Git metadata from the intended repository and review the implementation as a normal diff. Confirm secret/demo exclusions before committing.
3. Review the new pages with the project owner; extend schedule editing policies and pagination where needed.
4. Finish production settings/domain/CSRF checks, operational password recovery, monitoring and a complete audit policy before real patient use.
5. Implement GitHub Actions pull-request tests and gated Render deployment, then verify the end-to-end pipeline without demo credentials.
6. Document current Render cold starts, ephemeral storage, database lifetime and backup constraints during that deployment phase; do not infer that a free-tier deployment or managed backup has already been established.

The application is ready for local visual/functional review and further development. The PostgreSQL and assessment-deployment requirements remain open gates.


## Public Navigation Redesign and Responsive UX

Implemented October 19, 2026 using Django templates, component CSS, standalone Tailwind CLI and vanilla JavaScript.

- **Issues addressed:** the primary links and account actions previously formed one cramped group, with a narrow effective header width, a vertical divider, and desktop navigation squeezed down to 801px.
- **Layout:** the reusable `templates/components/public_header.html` now separates branding, primary navigation and account actions. A three-column grid centers the primary links independently, with branding left and actions right. The 1440px outer container and 6% gutters align with the public page content. Desktop height is 80px; compact height is 76px. Legacy public header rules were removed from `static/css/app.css`.
- **Shared components:** homepage, directory and doctor profiles continue to include the same partial through `templates/public/base.html`. Authentication retains its centered layout and shared brand component. Named Django routes and existing role-aware workspace URLs are preserved.
- **Sticky behavior:** an opaque white background, stable height, subtle border and scroll shadow keep navigation readable. Header stacking remains at 100; native modal dialogs use the browser top layer. The How It Works anchor has a 104px scroll offset.
- **Tablet/mobile:** below 1120px, a right-hand drawer opens beneath the branding. It includes distinct website and account navigation, a close control, active item highlight and full-width account buttons. The shared controller reads the public breakpoint from the panel while keeping the workspace breakpoint at 800px. Escape, backdrop and link selection close the drawer; focus returns to the trigger, Tab/Shift+Tab wrap within the drawer, background content becomes inert, and body scrolling is locked. Resizing to desktop restores normal interaction. Reduced motion disables transitions.
- **Active state:** existing resolver-name context identifies Home and both directory/detail routes. Active links have an underline on desktop and a side marker with background on mobile, plus `aria-current`. The existing section observer and anchor handler identify How It Works and focus the section after navigation.
- **Browser verification:** real local headless Chrome checked homepage, directory and doctor detail at **320, 375, 390, 480, 768, 1024, 1280, 1440 and 1920px**, for anonymous visitors, patients, doctors and administrators: **108 combinations passed**. No horizontal overflow, desktop group collisions, JavaScript exceptions or HTTP failures were found. Sticky positioning, menu open/close, Escape focus restoration, backdrop dismissal and section activation passed. Desktop (1280px and 1440px), tablet (1024px) and fully opened 320px drawer screenshots were visually inspected. Additional Chrome checks passed for Tab/Shift+Tab focus wrapping, desktop resize cleanup, every navigation destination across four visitor roles and reduced motion. Evidence and harness are local/ignored: `.local/browser/navigation-*.png`, `.local/browser/nav-stable-320.png`, `.local/nav_verify.py`, `.local/navigation-redesign-results.json`.
- **Automated results:** all **9 NavigationTests passed**, including shared headers, nested active routes and account/workspace destinations for all roles. The full suite before the new test ran 64 tests: 53 passed, 10 errors in demo-seeder setup, 1 PostgreSQL concurrency skip. Seeder errors report the existing one-hour advance-notice validation for generated appointments and are outside this navigation change. Standalone Tailwind v4.1.18 compilation succeeded.
- **Remaining issues:** full-suite demo-seeder failures and unavailable PostgreSQL concurrency verification remain. Browser checks used Chrome emulation rather than physical devices; other browser engines were not verified. No backend booking rules were changed.

## Public Header Reference-Based Redesign

This October 19, 2026 revision supersedes the earlier public-navigation design described above. The owner-provided Chiromo Hospital screenshot was inspected directly in the conversation. Its left-aligned logo, broad white navigation row, distributed central links and far-right appointment button guide the structure; Savannah branding and the illustrated landing-page hero are preserved.

### Defects and structural correction

The earlier header used a three-column grid with `display: contents` to flatten the navigation wrapper, coupled with public/workspace drawer media rules. This made desktop grouping depend on implicit grid placement and shared overrides. It also constrained the header to a 1440px container, leaving larger screens underused. Reported defects included crowded links and account actions falling onto a second row.

The shared `templates/components/public_header.html` is rebuilt with an explicit brand region and a real flexible navigation wrapper containing separate primary and account navigation regions. The main row is 88px high and occupies the full available width with responsive gutters (4.5vw, bounded at 24?96px). The logo and account region do not shrink or wrap; the primary navigation distributes its links through the available middle space. There are no negative margins, absolute-positioned desktop links or `display: contents` dependencies. Public drawer styles are isolated from workspace rules in `static/css/app.css`.

Anonymous users see Sign In and **Book an Appointment**, which links to the named `book` route and preserves the existing login `next` redirect. Registration remains available through authentication pages. Authenticated users see My Account and their role-aware My Workspace destination. All navigation uses existing Django routes. The shared header remains included through the public base template on the landing page, directory and doctor profiles; authentication keeps the shared brand and centered form layout.

No verified Savannah contact details are configured in this repository, so the optional top contact strip is deliberately omitted. No Chiromo contact information, services, images or text were copied.

### Responsive and sticky behavior

Below 1120px, the desktop links switch to a right-hand drawer underneath the visible branding, with a 76px compact header. The existing vanilla JavaScript controller supplies ARIA state, Escape/backdrop/link dismissal, focus restoration, Tab/Shift+Tab trapping, inert background content, scroll locking, reduced-motion support and desktop resize cleanup. The drawer keeps the appointment/workspace CTA accessible at 320px.

The opaque white main row stays sticky at the top with a border and subtle scroll shadow. Its height stays constant during scrolling. The How It Works section retains an appropriate anchor offset (108px desktop, 96px compact). Header stacking is 100; native modal dialogs remain in the browser top layer. Resolver-based Home and directory/detail active states retain an underline or mobile marker plus `aria-current`; the section observer handles How It Works.

### Verification

- Django navigation tests: **9 passed**, including shared components, all role workspace destinations, anonymous appointment CTA, nested active states and POST-only logout.
- Full Django suite: **65 run: 54 passed, 10 errors, 1 skipped**. The ten existing demo-seeder setup errors fail the one-hour booking advance-notice validation; the PostgreSQL concurrency test is skipped on local SQLite. Booking rules and seeder logic were not changed for this task.
- Django system check: passed. Tailwind standalone CLI v4.1.18 compilation: passed. No Node package manager or framework was introduced.
- Chrome viewport matrix: **108 combinations passed** across homepage, directory and doctor detail for anonymous visitors, patients, doctors and administrators, at **320, 375, 390, 768, 1024, 1280, 1440, 1580 and 1920px**. Checks cover no horizontal overflow, single-row desktop alignment, right-gutter CTA placement, sticky shadow, Escape/backdrop dismissal and keyboard focus wrap. Additional checks passed for all public navigation destinations, registration access, anonymous booking login redirect, How It Works section focus/active state, reduced motion and desktop resize cleanup. The resize harness was corrected to wait for the asynchronous viewport change; registration is checked while anonymous because authenticated visitors are redirected by the existing application.
- Browser evidence: local headless Chrome at `http://127.0.0.1:8001/`; screenshots and harness are ignored local artifacts under `.local/browser/reference-*.png` and `.local/reference_nav_verify.py`.
- Additional Chrome checks: **zero console errors and zero HTTP failures** across public/authentication pages at 390px and 1580px. The authenticated patient booking page and actual POST logout flow passed at both widths.
- Visually inspected: anonymous landing page at **1580px** and **1280px**, authenticated patient landing page at **1580px**, and the open anonymous drawer at **320px**. Desktop branding, links, account action and CTA share one row; the CTA reaches the right gutter and the hero remains intact.

### Remaining issues

Existing demo-seeder test errors and unverified PostgreSQL concurrency remain outside this header task. Browser emulation does not establish behavior on physical devices or other browser engines. Verified Savannah contact information is needed before enabling a contact strip.

## Assessment Compliance Audit - October 19, 2026

The original four-page `Savannah Informatics Backend Assessment (AI) (1).pdf` has now been read directly. [ASSESSMENT_COMPLIANCE_AUDIT.md](ASSESSMENT_COMPLIANCE_AUDIT.md) supersedes earlier broad compliance/security/repository claims. Status: **not ready for submission**. The PDF permits any database; PostgreSQL is an engineering choice, not an assessment requirement.

Verified gaps: cancellation reason is neither validated nor stored; bonus patient listing includes historical/cancelled appointments; shifted doctor grids permit overlapping patient bookings. Isolated audit probes reproduced these behaviors. The current suite ran 65 tests in 8.690s: **54 pass, 10 errors, one PostgreSQL-only skip**. All ten errors originate in the near-now demo-seeder validation path. Six additional diagnostic audit tests passed by confirming actual behavior, including defects, not by establishing compliance.

Fresh read-only Chrome verification covered 63 page/viewport combinations at 320/768/1440px across anonymous, patient, doctor and administrator pages, with no horizontal overflow, JavaScript exceptions or HTTP failures. Public homepage at 1440px and administrator overview at 320/1440px were visually inspected. Core API mutations were tested on isolated test data; no new persistent browser booking workflow or production test was claimed.

Current runtime: SQLite, 27 marked demo users, two demo administrators, five doctors, twenty demo patients plus one unrelated patient, 49 periods, 103 appointments (100 demo), 17 cancellations, 45 upcoming confirmed and 122 events. Zero current exact-start duplicate groups or schedule-validation failures were found. These checks do not eliminate the reproduced interval-overlap defect. No persistent seeding or credential rotation was performed.

Git now works and the outer checkout has history and origin `https://github.com/noelkips/clinic-appointment-booking-system.git`; main/remote-tracking main are at 7edf178. This corrects the earlier no-Git claim. Essential source/templates are untracked or modified; SQLite and bytecode are already tracked despite ignore rules. The README had exposed shared local demo credentials; its rewrite retains the roster but removes plaintext passwords in line with the audit's credential-safety requirement. The ignored local credential reference remains; no account password was changed and prior exposure is not revoked by documentation edits.

No public deployment URL, checked-in PR workflow, successful CI run or exercised merge-triggered deployment was found. Render config needs inner working-directory/env/hosts/runtime review. Reflection is an explicitly incomplete evidence-backed draft; personal independent decisions are deferred as requested. Design-before-code timing remains unverified. README is rewritten around current setup, retrospective design/trade-offs, actual API behavior, test status and delivery gaps while historical results remain in this report.

Next: correct reason/overlap/seeder defects and bonus filtering with maintained tests; clean repository artifacts and assess credential exposure; verify chosen database concurrency; implement PR CI, deploy and demonstrate automatic updates on merge; finish truthful owner-specific reflection. No major application feature was implemented during this audit.

## Targeted Audit Remediation - October 19, 2026

This section supersedes earlier open-defect statuses for the fixes below. The original audit remains a dated snapshot; this is the current remediation result. **Mandatory Section 2 endpoint regressions pass locally. Full suite: 80 run in 16.272s, 79 passed, zero failures, zero errors, one PostgreSQL-only skip.** Overall submission remains blocked on delivery/CI/CD and incomplete owner reflection, not these repaired API defects.

### Defect-by-defect evidence

| Original problem and root cause | Correction and files | Regression/verification | Remaining limitation |
|---|---|---|---|
| Cancellation accepted no reason and discarded supplied text; no dedicated persisted field | `models.py`, `api.py`, `services.py`, `forms.py`, `views.py`, `templates/appointments/detail.html`, migration `0003_cancellation_reason`: trimmed nonblank reason, maximum 500, required through API and HTML, persisted separately from consultation reason, read-only in ordinary booking serializer | `RemediationTests.test_cancel_missing_blank_invalid_and_long_reasons_leave_booking_intact`, `test_cancel_reason_persisted_trimmed_and_repeated_cancel_rejected`, `test_direct_service_also_requires_reason`, `test_html_reason_validation_and_persistence`, `test_cancellation_authorization_with_valid_reason`; all pass. Repeat cancellation 400; successful cancellation releases slot and permits another patient to rebook | Legacy cancelled appointments retain blank reason; no historical explanation fabricated. Direct maintenance writes still require a reason policy |
| Equal-start conflict checks missed intervals on shifted doctor grids; availability used a set of starts | `services.py` checks half-open [start,start+30min) overlap for doctor and patient; availability excludes every overlapping doctor interval, including a booking from the previous date. Rescheduling uses the same validator. Migration `0004_appointment_interval_guards` adds native SQL guards; exact-start unique constraints remain | Shifted-patient and shifted-doctor bookings rejected 409; adjacent intervals accepted; doctor/patient reschedule overlap rolls back; previous-day availability tested; direct insert/update overlap raises IntegrityError; simultaneous overlapping API requests yield one 201 and one 409. All corresponding tests in `test_remediation.py` pass | PostgreSQL code/extension not executed here; see database limitations below. Schedule interval configuration still uses model/form validation |
| Seeder generated same-day future visits inside the required one-hour notice, causing ten errors including rotation-test setup | `management/commands/seed_demo.py` moves remaining visits for today to tomorrow's weekly schedule. `demo.validate_demo_slot` is a separate local-demo-gated path allowing past fictional visits only; future visits still use normal notice validation. Generated cancelled demo visits receive an explicitly fictional reason | Existing seed and rotation tests pass. `SeederBoundaryTests.test_seed_at_near_notice_boundary_is_idempotent_and_preserves_real_user` freezes time, verifies 100 records, past/future correctness, repeat IDs/times, unchanged password hashes and unrelated-user preservation | Existing stored demo dates are intentionally not rolled forward. Persistent database was not reseeded |
| Bonus patient API returned full history because it lacked future/status filters | `api.patient_appointments` filters future confirmed appointments, orders by starts_at then pk, retains owner/staff-only access | `test_bonus_upcoming_filter_sort_and_permissions` mixes past/cancelled/future/other-patient records, tests both URL prefixes and owner/admin/doctor/unrelated/anonymous access; passes | Full authorized history remains available through existing appointment/workspace views; admin nonexistent-patient behavior remains empty list |
| Tracked SQLite/bytecode persisted despite ignore rules | `.gitignore` expanded for SQLite WAL/journal filenames; 17 data/bytecode files removed from index with git rm --cached, preserving local files. Essential new runtime/test components prepared in Git for review; no commit, push, force-push or history rewrite | git ls-files reports no sqlite3/pyc runtime files; local database exists; backup comparison confirms original data preserved | Old Git history still contains earlier artifacts. Review/commit current source/index changes before submission; owner-provided PDF remains a separate reviewable artifact |
| Shared exposed local demo credential still authenticated 27 marked users | Checked old credential, then rotated exactly 27 designated accounts using `rotate_passwords` and a generated Savannah-prefixed password. Updated only ignored `docs/LOCAL_TEST_ACCOUNTS.md`; no passwords printed in reports | Helper verifies new authentication and old rejection for all 27. Snapshot comparison confirms unrelated users, appointments, events, doctors, patients and working periods unchanged. Credential evidence: `.local/remediation-credential-results.json` | Existing authenticated demo sessions are invalidated by password change. Use the current ignored reference. Rotation does not remove old hashes/artifacts from Git history; never deploy demo users |

### Database migration and concurrency result

- `0003_cancellation_reason` adds a blank/default-empty field without rewriting legacy reasons or deleting appointments.
- `0004_appointment_interval_guards` preflights existing confirmed intervals. If any doctor/patient overlap exists, it aborts with an actionable error rather than modifying records. SQLite gets INSERT/UPDATE triggers using half-open 30-minute intervals; PostgreSQL gets GiST exclusion constraints for doctor/time and patient/time using UTC timestamp ranges and `btree_gist`. The old exact-start unique constraints are preserved.
- Both migrations applied successfully to local SQLite. An ignored `.local/db-before-remediation.sqlite3` backup was created first. Comparing every original column/row in Appointment, AppointmentEvent, Doctor, Patient and DoctorAvailability showed no changes. All 103 appointments remain. New cancellation_reason values on legacy rows are blank, not fabricated.
- SQLite atomic transactions now use IMMEDIATE and a 20-second busy timeout (`config/settings.py`). API and HTML mutations handle busy/locked errors without exposing raw database details; API returns 409 with retry guidance. The generic concurrent-request regression runs on SQLite too and passed. SQLite has database-wide writer serialization and millisecond date-function precision; this is not a throughput benchmark or real PostgreSQL validation.
- PostgreSQL parent locks and exclusion constraints are implemented but **unverified against a running PostgreSQL server**. `btree_gist` installation needs appropriate privileges. The existing PostgreSQL-only concurrency test remains the sole justified skip. Future SQLite table-rebuilding migrations must preserve/reinstall the custom triggers; maintenance policies for schedule/notice/reason/event consistency remain separate from interval protection.

### Regression results and scope

Executed complete command: `.venv/Scripts/python.exe manage.py test --settings=config.test_settings --verbosity 2`. Actual result: **Ran 80 tests in 16.272s; OK (skipped=1)**. Fifteen new tests in `clinic/test_remediation.py` supplement the corrected existing cancellation tests in `clinic/tests.py`. The sole skip is `PostgreSQLConcurrencyTests.test_concurrent_same_slot_has_one_winner`, requiring an actual PostgreSQL test database. The general interval concurrency test executed and passed locally.

System checks passed; makemigrations --check --dry-run reports no changes; migrate --plan has no pending operations; pip check reports no broken dependencies. git diff --check is clean. Full output: ignored `.local/remediation-tests.txt`. Audit probes from before correction deliberately asserted broken behavior and were rerun before implementation; they are historical diagnostics, not the new correctness test suite.

Fresh server on localhost:8003 and headless Chrome checked **63 read-only page/viewport combinations** at 320/768/1440px covering anonymous public/authentication pages and patient, doctor and staff workspaces. No horizontal overflow, JavaScript exception or HTTP failure occurred. Evidence: `.local/remediation_browser.py`, `.local/remediation-browser-results.json`, `.local/browser/remediation-*.png`. This did not create new persistent appointments. API/HTML mutation regressions used isolated test data. No frontend redesign, Render deployment or unrelated feature work was performed.

### Current Section 2 status and remaining assessment gaps

- POST booking, date-based availability, cancellation with reason/release/repeat rejection and atomic rescheduling: implemented and locally regression-verified.
- Bonus upcoming list: implemented and locally verified; one-hour notice remains enforced for booking and rescheduling, including an exact-boundary rescheduling test and equivalent UTC timestamp.
- Remaining: actual PostgreSQL migration/concurrency evidence; reviewer-ready commit/push; PR CI; public deployment URL; automatic merge deployment; complete honest owner-specific reflection; design-before-code timing evidence remains unavailable. Old-history artifact exposure still needs review; no history rewrite was authorized.
- Next milestone: review/commit this corrected source, validate PostgreSQL, then implement PR CI and delivery. Human reflection answers remain deferred as requested. These later steps were not silently started during remediation.
