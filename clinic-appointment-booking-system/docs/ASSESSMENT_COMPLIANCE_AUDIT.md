# Assessment Compliance Audit

> Current status: the October 19 targeted remediation section at the end supersedes the original API/test/credential findings. Local suite: 80 tests, 79 passed, zero failures/errors, one PostgreSQL skip. Delivery and reflection gaps remain.


Audit date: October 19, 2026, Africa/Nairobi. Scope: current working tree, not only committed HEAD. This is a verification milestone; application features, booking rules, credentials and deployment resources were not changed.

Authoritative source: `Savannah Informatics Backend Assessment (AI) (1).pdf`, four pages, SHA-256 `ab13835063e146c619c20e28b9352eae135facb777f4b953e37a18b961258a16`. All four pages were extracted and read. Page 2 defines submission materials and permits any database; page 3 defines design and mandatory APIs; page 4 completes API constraints, bonus requirements, deployment/CI/CD and reflection. Earlier prompts and implementation reports were treated as claims to check, not requirements.

Evidence includes direct inspection of models, both migrations, services, API/serializer, URLs, forms, views, admin registrations, navigation, templates, CSS/JavaScript, demo helpers, tests, settings, requirements, Render configuration, Git metadata, README and the full implementation report. There is no separate serializers.py: the serializer is in clinic/api.py.

## A. Executive Summary

**Not ready for submission.** The core booking/rescheduling implementation has meaningful passing tests and role isolation. Mandatory cancellation-with-reason is absent. There is no checked-in CI workflow, verified public deployment URL, demonstrated deployment-on-merge or completed AI reflection. Current work includes untracked essential modules and templates. The complete test suite is red.

Confirmed results: **65 repository tests: 54 passed, 0 assertion failures, 10 setup/runtime errors, 1 skipped**. Six additional isolated diagnostic probes passed by confirming the observed behaviors; these are not six additional assessment requirements satisfied. Chrome passed 63 read-only page/viewport combinations. The audit reproduced cancellation without a reason, discarded supplied reasons, historical/cancelled records in the bonus upcoming list, and overlapping patient appointments on different doctor slot grids.

Assessment compliance: **partially compliant overall; submission blocked**. Engineering quality: **promising service-layer structure and authorization coverage, with significant integrity, reproducibility and release gaps**. No invented official scoring rubric or coverage percentage is used. Custom dashboards, Tailwind and hospital navigation are useful extras, not substitutes for the PDF's backend and delivery requirements.

## B. Assessment Requirements Matrix

Statuses: Implemented and verified (IV); Implemented but not verified (IN); Partially implemented (PI); Missing (M); Incorrect or failing (F); Not applicable (NA). Priorities: P0 before publication/security exposure; P1 before submission; P2 important engineering improvement; P3 optional polish. PDF page numbers refer to the original four-page file.

| ID | Assessment requirement | Implementation evidence | Test evidence | Status | Gap | Priority |
|---|---|---|---|---|---|---|
| SUB1 | GitHub/GitLab repository link, public or shared (p2) | Git origin is https://github.com/noelkips/clinic-appointment-booking-system.git; main at 7edf178 | git remote -v, branch -avv, log | PI | Remote metadata exists; reviewer access and latest changes being pushed are unverified | P1 |
| SUB2 | Deployed running application link (p2/p4) | No public application URL found in README/config | No URL supplied to probe | M | Deploy and verify a real URL; localhost is not deployment | P1 |
| SUB3 | README: decisions, local startup, CI/CD note (p2) | README rewritten during audit to describe actual state | Settings, commands and source inspected | PI | Setup/design documented; CI/CD implementation and live URL missing | P1 |
| SUB4 | Section 4 reflection (p2/p4) | README includes evidence-backed draft and pending items after audit | Conversation evidence; no complete earlier reflection file | PI | Owner's independent decisions deferred by request | P1 |
| S1.1 | Design in README before coding (p3) | Earliest inspected commit 537f022 contains both application code and README | git show/log | IN | No evidence establishes design was written first; cannot fix historical timing by dating new prose | P1 |
| S1.2 | Describe models and components (p3) | models.py, services.py, api.py, views.py; current README design | Source/migrations read; migrations check passes | IV | Current documentation is retrospective | P2 |
| S1.3 | Key decisions and trade-offs, growth (p3) | README explains monolith, derived slots, locks, database choice and limitations | Compare current source to documentation | IV | Original human decision history is not established | P2 |
| S1.4 | Five-doctor, fixed-hours, 30-minute scenario (p3) | Doctor/DoctorAvailability/Appointment; five local doctors | Database count; split-slot tests | IV | Number of doctors is data, not hardcoded maximum | P2 |
| S2.1 | Use DRF/FastAPI/Go and a database (p3) | Django/DRF, ORM, local SQLite | Runtime vendor and passing application tests | IV | PDF permits any database; PostgreSQL is optional engineering choice | NA |
| S2.2 | POST /appointments: hours, future, not taken (p3) | api.create_appointment; services.book_appointment/validate_slot | Persistence, conflict, invalid doctor/time, hours, lead-time tests | PI | Standard cases pass; interval overlaps and real concurrent DB behavior need work | P1 |
| S2.3 | GET /doctors/{id}/availability: date-based 30-minute slots (p3) | api.availability; services.available_slots | Split periods, malformed date, occupancy/release; audit past/unavailable probes | IV | API intentionally requires login; patient conflicts may still reject offered doctor slots | P2 |
| S2.4 | PATCH cancel: reason, release, reject already cancelled (p3) | api.cancel_appointment; change_appointment | Slot release passes; audit confirms repeat cancellation 400 | F | Missing/blank reason accepted; supplied reason discarded; no cancellation-reason field | P1 |
| S2.5 | PATCH reschedule: validate new, release old, reject cancelled (p3) | api.reschedule_appointment; change_appointment atomic service | Aware reschedule, gap rollback, cancelled rejection; occupied-target audit probe | IV | Shared interval-overlap weakness remains; exact one-hour edge tests absent | P1 |
| S2.6 | Meaningful errors and correct HTTP codes (p3-4) | Serializer errors, mutation_error | 201 success, 400 invalid, 403 forbidden, 404 hidden, 409 conflict | PI | Missing cancellation validation; broad IntegrityError maps every constraint failure to slot conflict | P1 |
| S2.7 | Sensible multi-file structure (p4) | Models/services/API/forms/views separated | Direct source inspection | IV | Formatting and large views module can improve without new architecture | P3 |
| S2.8 | Basic booking tests (p4) | clinic/tests.py | Core booking tests pass in full run | IV | Full suite still has ten seeder errors | P1 |
| BONUS1 | Upcoming patient appointments sorted by date (p4) | api.patient_appointments; model ordering | Isolation passes; audit confirms ascending order but includes past and cancelled | F | Add future confirmed filter and dedicated regression tests | P2 |
| BONUS2 | Prevent booking within one hour (p4) | validate_slot rejects starts <= now + one hour | Booking test passes; rescheduling shares validator | PI | Implemented; exact boundary/offset/time-frozen reschedule tests missing | P2 |
| S3.1 | Cloud application reachable publicly at submission (p4) | render.yaml only | No deployment evidence or URL | M | Provision, configure, deploy and verify | P1 |
| S3.2 | Test suite on every pull request (p4) | No .github workflow or alternative CI configuration found | Working tree and HEAD tree inspected | M | Add CI, database setup and successful PR execution evidence | P1 |
| S3.3 | Automatic deploy on PR merge into designated branch (p4) | No demonstrated deployment trigger/branch | main exists; no run evidence | M | Configure and exercise an actual merged-PR deployment | P1 |
| S3.4 | README public URL, branch/how and pipeline description (p4) | Current README explicitly marks these pending | Documentation inspection | PI | Honest missing-state documentation does not fulfill live deployment requirement | P1 |
| S4.1 | AI use across all four sections (p4) | Current README draft documents only available evidence | This conversation records navigation, audit and documentation assistance | PI | Earlier design/API/deployment assistance cannot be reconstructed confidently | P1 |
| S4.2 | Improvement example including actual prompt (p4) | README draft uses supplied Chiromo navigation request | Supplied screenshot and browser evidence from this session | IV | Example is frontend/supporting work, not evidence of deployment completion | P2 |
| S4.3 | Wrong/incomplete AI output and discovery (p4) | README draft identifies rejected previous header and correction | Owner's correction request and reference-based follow-up | IV | Further examples may be added by owner; no invention required | P2 |
| S4.4 | Two independent decisions and reasons (p4) | Pending owner input | Owner requested deferral during audit | M | Cannot honestly author these on owner's behalf | P1 |

## C. Section 1 - System Design

Overall: **partially verified**. The README now documents current architecture; historical before-code timing remains unverified. The initial commit includes both code and design prose, which proves neither writing order nor an earlier design review. No claim of retrospective compliance with timing is made.

| Design topic | Implementation and verification | Status/gap | Recommended correction |
|---|---|---|---|
| Components | config settings/URLs/WSGI; templates/forms; DRF API; shared services; ORM | IV: sensible small monolith | Keep this boundary; no microservices needed |
| Users and roles | Django User; Doctor and Patient one-to-one; is_staff means app administrator | IV via role and registration tests | Document staff policy; ensure maintenance permissions stay intentional |
| Working hours | Weekly periods with weekday/start/end/30-minute constraints; split schedules | PI: clean() rejects overlap, SQL does not | Define safe schedule-change policy and serialize all mutation paths |
| Appointments | Doctor/patient PROTECT FKs; aware starts_at; confirmed/cancelled; ordered by start | PI: cancellation reason missing | Add separate cancellation reason; preserve original consultation reason |
| Reschedule/audit | Timestamp updated atomically; AppointmentEvent records actor/action/time | PI: no previous/new timestamps or cancellation detail | Capture event details if required for meaningful history |
| Slot representation | Derived 30-minute intervals from period start, no pre-generated Slot table | IV: simple, supports split hours | Address arbitrary grid starts and interval conflicts |
| Timezones | USE_TZ; Africa/Nairobi; serializer normalizes ISO inputs; local schedule evaluation | IN for all boundaries: ordinary aware paths tested | Add midnight, offset-equivalence, naive-input policy and exact-hour tests |
| Database/concurrency | PostgreSQL preferred; SQLite explicitly enabled locally; partial unique indexes and parent locks | IN for PostgreSQL | Verify on actual target database; PDF does not mandate PostgreSQL |
| Growth | ORM relations and indexes adequate for five doctors | PI: no pagination, many dashboard count queries | Add pagination/aggregations when needed, not a rewrite |

## D. Section 2 - REST API

Root routes are included through clinic/urls.py and API-prefix routes through config/urls.py. Exact no-trailing-slash paths exist. All API views inherit IsAuthenticated and SessionAuthentication; unauthorized session/API access normally returns 403, not a token-style 401. The public doctor page renders availability server-side without anonymous API access.

| Method / required path | Actual paths | Auth | Validation / success | Errors / evidence | Status |
|---|---|---|---|---|---|
| POST /appointments | /appointments and /api/appointments | Patient only; patient derived from session | doctor PK, starts_at, optional reason; 201 persists appointment and event | tests booking_persists, double_booking_rejected, patient_double_booking_rejected, no_hours/gap/off_grid/partial/past/one_hour/unavailable/invalid; 400/403/409 | PI: valid same-grid behavior verified; interval issue below |
| GET /doctors/{id}/availability | Both root and /api prefix | Authenticated | date query; 200 with date and ISO slots; excludes confirmed doctor bookings and incomplete periods | bad date 400; missing doctor 404 by get_object_or_404; past/unavailable returns empty 200 in audit; split_availability tests | IV for implemented policy |
| PATCH /appointments/{id}/cancel | Both root and /api prefix | Owner patient or administrator | 200 changes status, adds event, frees future slot | Other patient 404; assigned doctor 403; already cancelled 400 in audit | F: no cancellation reason accepted/validated/stored |
| PATCH /appointments/{id}/reschedule | Both root and /api prefix | Owner patient or administrator | starts_at required; 200 moves timestamp under locks/transaction | Invalid/gap 400; occupied 409; original retained on failure; cancelled 400; owner checks shared | IV standard behavior; common overlap limitation |
| GET /patients/{id}/appointments (bonus) | Both root and /api prefix | Owner patient or administrator | 200 ascending model ordering | Returns historical and cancelled records; nonexistent patient for admin produces empty list rather than 404 | F for upcoming-only requirement |

Reproduction evidence from `.local/audit_probes.py` (isolated, destroyed test database):

- Missing cancellation body `{}`, blank reason, and nonblank reason all returned 200. The stored appointment reason remained empty even when a reason was supplied. A second cancellation returned 400. The existing test_cancel_releases_slot explicitly expects `{}` to succeed, so a green core test does not prove PDF compliance.
- Patient listing returned a historical appointment, cancelled future appointment and confirmed future appointment, in ascending order. Ordering works; the required filter does not exist.
- Same patient: doctor A at 09:00-09:30, doctor B with a permitted 09:15-start schedule at 09:15-09:45. Both bookings succeeded (second POST 201). starts_at equality is insufficient for overlapping intervals. The same issue can affect one doctor after schedule edits/direct maintenance create a shifted grid.
- Rescheduling onto an occupied target returned 409 and preserved the original timestamp. Past availability returned empty slots; unavailable doctor returned no slots; anonymous API availability returned 403.

Availability lists doctor freedom, not patient-specific freedom. A patient's conflict with another doctor is caught only during booking, which may produce a rejected selection even after a slot is offered. This is a UX limitation, not a failure to return a doctor's availability.

## E. Section 3 - Deployment and CI/CD

Overall: **missing verified delivery; submission blocker**.

- Git works. Repository metadata is in the outer directory. main and origin/main point to 7edf178; three local commits were available. Remote: https://github.com/noelkips/clinic-appointment-booking-system.git. Remote access/current server state was not contacted; cached branch metadata is not proof of reviewer access or pushed latest work.
- The pre-audit working tree had 22 short-status entries, including untracked essential demo/navigation modules and shared templates. Latest local functionality is not entirely committed. Existing changes were preserved; no commit/push/reset was performed.
- HEAD tracks db.sqlite3 and Python bytecode. .gitignore rules do not untrack already committed files. .env and docs/LOCAL_TEST_ACCOUNTS.md are ignored and not tracked. Plaintext local demo credentials were also present in the working README before this audit; the rewritten README removes the password column while retaining the roster and local reference instructions. This does not remove prior exposure or rotate any account.
- No CI workflow is present in the working tree or inspected HEAD. Historical README claims about .github/workflows/test.yml are unsupported. No CI run, test gate or successful PR check was verified.
- render.yaml configures a Python service, PostgreSQL, install/migrate/collectstatic and Gunicorn. It does not prove provisioning or deployment. It sets DEBUG, but settings read DJANGO_DEBUG; False currently defaults safely, yet the configuration key is wrong. DJANGO_ALLOWED_HOSTS defaults to local hosts and is not set to a deployed domain in the blueprint. Cross-origin CSRF configuration is absent; same-origin deployments do not inherently need trusted origins, but the actual proxy/domain setup must be verified.
- Git tree root contains the inner clinic-appointment-booking-system folder. The blueprint lacks rootDir; its relative requirements.txt/manage.py commands need that working directory configured. Without external configuration, repository-root builds would fail. Actual provider configuration is unknown.
- No Python runtime pin or deployment branch is declared in the blueprint. No merged-PR deployment evidence exists. A designated branch and automatic trigger remain unconfigured/unverified.
- No public application URL was found or supplied. Cloud authentication, static files, database connectivity, required endpoints and DEBUG=False therefore remain unverified; localhost screenshots are not deployment evidence.

Required next evidence: clean reproducible checkout, passing PR checks with target database, provider configuration, public URL smoke tests and an observed PR merge that updates the application.

## F. Section 4 - AI Reflection

Overall: **not ready**. The owner explicitly deferred questions requiring human answers during this audit. A labeled draft in README now uses only available conversation evidence; no independent decision or earlier AI usage was invented.

| Question | Evidence | Status | Remaining action |
|---|---|---|---|
| 1. AI across all four sections | Current chat records navigation implementation, browser verification, audit and documentation; earlier authorship unknown | PI | Owner must confirm actual design/API/deployment assistance |
| 2. Improvement and prompt | Faithful navigation-reference prompt, explicit flex implementation and screenshots | IV | Owner can retain supporting-work example or provide a stronger backend example |
| 3. Wrong/incomplete output and how caught | Owner rejected first header; supplied Chiromo reference; implementation and screenshots corrected | IV | No false claim that all initial output was correct |
| 4. Two decisions without AI and reasons | No authenticated human account of two decisions | M | Deferred to owner; do not attribute AI-written design rationale as independent decisions |

## G. Security Findings

| ID / severity | Evidence and impact | Verification / recommended fix |
|---|---|---|
| SEC1 High for publication | Git tracks db.sqlite3, including users/password hashes and data; ignore pattern does not protect history | git ls-files/tree; remove DB from index with review, assess history/data exposure, rotate any published reusable credentials; preserve local database |
| SEC2 High if demo credentials reach a deployed environment | Shared demo credential was documented in README; two demo users are superusers | Password values deliberately omitted here. README scrubbed in this audit, local reference retained. Never deploy demo accounts; rotate any exposed reused credentials separately |
| SEC3 Medium | No app login throttling/rate-limit configuration | Source/config inspection; use deployment/app controls appropriate to risk, test invalid-login behavior and abuse limits |
| SEC4 Medium production configuration | check --deploy emits five local warnings; HTTPS/HSTS not configured by app; allowed hosts are local | Local DEBUG=True is intentional, not proof of a production vulnerability. Verify production HTTPS/proxy/hosts/secure cookies; do not enable proxy trust blindly |
| SEC5 Low | Registration exposes ordinary username-exists feedback; authenticated registration POST is not explicitly rejected though GET redirects | forms.RegisterForm and views.RegisterView; document enumeration policy, guard authenticated POST if desired |
| SEC6 Medium integrity | Shifted-grid patient overlaps accepted; direct admin/ORM paths bypass service policy | Audit overlap probe; enforce interval conflicts under consistent locks and test every write path |

Verified protections: scoped visible_appointments prevents cross-patient disclosure; doctors see assigned appointments and cannot read a patient's full API history; platform routes require staff; foreign appointment mutations return 404; doctors cannot mutate bookings; registration does not permit privilege assignment; unsafe/incompatible next redirects are rejected; logout is POST-only; login and session-authenticated API mutations require CSRF; normal persistent passwords use PBKDF2. These have named regression tests in clinic/tests.py and clinic/test_navigation.py.

No user-controlled raw SQL, eval, csrf_exempt or unescaped innerHTML was found in inspected application sources. ORM filtering and Django escaping are used. The template safe filter is applied to Django-controlled form help text; no arbitrary user safe-html path was found. This is source review and behavioral testing, not a penetration test, dependency-CVE scan or guarantee of no vulnerabilities. Dependency installation consistency was checked with pip check, not a vulnerability database.

## H. Database and Concurrency Findings

Current runtime is SQLite, USE_TZ=True, Africa/Nairobi, DEBUG=True and local-demo seeding enabled. select_for_update is unsupported by this connection. A localhost:5432 probe found no listener; no PostgreSQL server/version/migrations or real lock behavior was verified. The assessment allows SQLite; the issue is unverified documented reliability and SQLite write-contention handling, not database-brand noncompliance.

- Both migrations are applied locally; makemigrations --check --dry-run reports no changes and migrate --plan has no operations.
- Partial SQL unique indexes protect confirmed doctor/start and patient/start pairs. Doctor/patient appointment references use PROTECT; event actor uses SET_NULL. Cancellation status frees the exact slot index. Reschedule rollback uses transaction.atomic and is verified for gap and occupied failures.
- Parent row locks (Doctor then Patient) serialize normal service mutations on PostgreSQL; appointment changes also lock the appointment. Code analysis supports one winner for the same exact slot; only the actual PostgreSQL test can verify that path. SQLite's unique constraint prevents duplicate confirmed exact starts, but contending requests may raise an uncaught OperationalError/database-locked response instead of a clean 409. That was not exercised concurrently here.
- DoctorAvailability.clean prevents overlaps, and platform_schedules revalidates under a doctor lock. SQL only checks positive duration, valid weekday, 30-minute slot size and duplicate starts; a direct ORM create of an overlapping period succeeded in the isolated audit. Admin writes do not share the service's locking protocol.
- Appointment.status choices are not a database CHECK. Slot validity and future notice require service/model validation; direct .save/update bypasses clean. Django admin appointment editing is model-based, not the full locked service or event mechanism. Edits to existing cancelled appointments may also validate against current future-slot rules. This requires an intentional maintenance policy.
- Interval overlap, cancellation reason storage and schedule changes affecting existing appointments remain integrity gaps. AppointmentEvent has actor/action/time, but no old/new slot details or cancellation reason.
- All 103 current local appointments fit current schedules; current schedule validation errors: 0; confirmed exact-start duplicate groups: 0 doctor and 0 patient. These current-data checks do not disprove the reproduced shifted-grid defect.

## I. Automated Test Results

Commands were executed from the inner application directory using .venv/Scripts/python.exe.

| Command | Actual result |
|---|---|
| manage.py test --settings=config.test_settings --verbosity 2 | Ran 65 tests in 8.690s; FAILED (errors=10, skipped=1): 54 pass, 0 assertion failures, 10 errors, 1 skip |
| .local/audit_probes.py | 6 diagnostic tests passed in 0.481s, isolated test DB destroyed |
| manage.py check | No issues |
| manage.py makemigrations --check --dry-run | No changes detected |
| manage.py migrate --plan | No planned migration operations |
| -m pip check | No broken requirements found |
| manage.py check --deploy | Five local warnings: W004 HSTS, W008 HTTPS redirect, W012 secure session cookie, W016 secure CSRF cookie, W018 DEBUG; this was local settings, not a production smoke test |

Full output is local/ignored at .local/audit-test-results.txt. The skipped test is PostgreSQLConcurrencyTests.test_concurrent_same_slot_has_one_winner. Ten errors originate in seed_demo.py's validate_slot call: a generated same-day future appointment inside the next hour is not historical, so it fails lead-time validation. This makes otherwise unrelated credential-rotation tests fail in setUp before exercising their target behavior.

Error tests: DemoRotationTests.test_ambiguous_admin_aborts_entire_rotation, test_explicit_local_opt_in_required, test_missing_user_aborts, test_ordinary_seed_does_not_reset_hashes, test_password_only_command_preserves_dataset, test_passwords_only_requires_reset_flag, test_production_refused, test_rotation_authenticates_and_preserves_data; DemoSeedTests.test_password_refresh_requires_deliberate_option and test_seed_idempotence_authentication_and_counts.

Meaningful existing tests cover persistence, doctor/patient exact-slot conflicts, hours, gaps, off-grid and incomplete slots, past/notice rejection, invalid doctor/timestamps, split availability, schedule errors, release/rollback, permissions, registration privilege isolation, CSRF and database doctor uniqueness. Other tests merely check menus/page status; they supplement rather than replace business tests. API force_authenticate tests do not by themselves exercise real login/CSRF; separate tests do.

Missing high-value permanent regressions: mandatory cancellation reason missing/blank/persisted; upcoming list filters and ordering with mixed history; interval conflicts across shifted schedules and schedule edits; exact one-hour boundaries and rescheduling; equivalent UTC/Nairobi timestamps and midnight; reschedule races/cancel races/patient races across different doctors; unavailable/inactive doctor availability API; status/schedule bypass policies; SQLite contention outcome if retained as a supported deployment backend. Audit probes are ignored local diagnostics and should become maintained tests when fixes are implemented. No coverage percentage was measured.

## J. Frontend and UX Findings

Fresh Chrome/CDP smoke audit at localhost:8001: **63 read-only page/viewport combinations**, 320/768/1440px. Anonymous: home, directory, doctor profile, login, register, forgot-password. Patient: dashboard, appointments, booking, account. Doctor: dashboard, schedule, appointments, account. Administrator: overview, appointments, doctors, patients, schedules, activity, account. No horizontal-overflow assertion, JavaScript exception or HTTP failure was observed. Source and browser evidence are .local/audit_browser.py and .local/audit-browser-results.json.

Screenshots captured for all four roles at 320/1440px. The administrator overview at 320/1440px and public homepage at 1440px were visually inspected; no blocking layout issue was found in those views. Prior navigation interaction checks are historical evidence, not rerun by this read-only smoke script. Booking/cancel/reschedule mutations in this audit were exercised on isolated test data, not through a new persistent browser booking workflow.

Source findings: the rebuilt public header uses explicit flex regions, active-route markers and a shared accessible drawer. Drawer has ARIA state, focus trap/restoration, inert background, Escape/backdrop dismissal, scroll lock and reduced motion. Forms have labels, error messages and loading/empty states; availability loads with fetch and guards stale responses. Full assistive-technology, Firefox/Safari and physical-device verification was not performed.

Cancellation UI has no reason input, matching the backend defect. Password recovery is honestly informational, not a working reset service. Required fields can fail server-side without losing booking atomicity. Public invalid date falls back silently to tomorrow while API rejects it, a minor consistency issue. Login avoids external/role-incompatible redirects; the booking next path is preserved for patients.

Charts and statistics are database-derived in views.platform/dashboard_page and templates/platform/overview.html, including explicit cancellation-in-total labeling. They are not fabricated demo metrics. Admin overview issued **42 queries even on an empty isolated fixture**; aggregate the repeated per-day count queries before larger-scale usage. Doctor cards and listings lack pagination. These optimizations and further accessibility work are not explicit PDF requirements.

## K. Demo Data Findings

Read-only local database snapshot on October 19, 2026: 28 users; 27 marked demo users including 2 administrators; 5 doctors; 21 patient profiles including 20 demo patients; 49 working periods; 103 appointments including 100 demo appointments; 17 cancellations; 45 future confirmed visits; 122 events. Time-sensitive counts may change without data changes. One non-demo patient is present and was not overwritten. No seed command was run against the persistent database or any production service during this audit.

require_local_demo enforces DEBUG, explicit enablement and loopback/local host. Account ownership uses marker group, demo email, expected role and active state. rotate_passwords checks all 27 identities before changes and uses atomic rollback. Seeding preserves unrelated users and existing historical appointments by intent. Production refusal/unmarked-user tests that can execute pass; eight rotation tests currently cannot reach assertions because of the common setup failure.

Reproducibility is currently **failing**, not verified idempotent: two seed tests error at current time. Freeze test time and define generation behavior for today's near-future slots; do not weaken production booking notice rules. Local credential values remain in the ignored account reference; audit reports deliberately do not print them. Earlier successful authentication of all 27 accounts is session-history evidence; this audit did not repeat persistent credential rotation or authenticate every account.

## L. Code Quality Findings

- Appropriate small-app structure: shared service used by HTML and API, transactions in business mutations, scoped query helper, reusable template components and model forms. Avoid introducing repositories/microservices simply for the assessment.
- Service/API exception boundaries generally avoid leaking raw database details. However broad IntegrityError handling hides non-slot constraint errors and SQLite OperationalError is unhandled.
- Dense one-line definitions and minified handwritten templates make changes harder to review. Runtime requirements are broad ranges, with no pinned deployment Python/dependency lock. No static type checks or lint configuration were found; these are optional, not PDF requirements.
- Row-lock paths should stay consistent across services, schedules and maintenance operations. There is duplicate slot validation in book_appointment and full_clean, increasing queries; optimize only after preserving correctness.
- Doctor and patient listing API/querysets lack pagination. Platform charts perform many small queries. Existing select_related/annotate usage avoids several obvious per-row user lookups; no complete N+1 benchmark at production scale was performed.
- No clearly unused required Python dependency was established. The inner lib directory has no application files in the inspected listing. Bytecode/database artifacts should not be submitted as source. No broad dead-code or dependency-vulnerability scan was claimed.

## M. Missing Requirements

Mandatory: cancellation reason validation/persistence; a verified public deployed application and URL; PR CI; automatic merge-triggered deployment to a documented branch; complete reflection across four sections including two human-independent decisions; submission of the current code in the shared repository. Historical pre-code design timing is unverified rather than definitely missing. Basic tests and sensible structure are present, but the complete suite is not release-green.

Bonus gap: upcoming-only patient appointment filtering. One-hour booking prevention exists but boundary test depth is incomplete. PostgreSQL, custom dashboards, full Tailwind utility conversion, operational email recovery and a particular cloud provider are **not** mandatory requirements in the PDF.

## N. Submission Blockers

1. Mandatory cancellation-with-reason behavior fails.
2. No verified deployed URL/public running application.
3. No PR CI or demonstrated automatic deploy-on-merge.
4. Reflection incomplete; owner-specific answers intentionally deferred.
5. Uncommitted/untracked essential source and tracked database/bytecode undermine safe reproducible submission.
6. Ten errors in the full suite prevent a credible passing PR gate.
7. Confirmed interval-overlap defect undermines reliable appointment scheduling; real target-database concurrency evidence is absent.

## O. Recommended Fixes

Top ten corrective actions, in order:

1. **P0:** Address tracked DB and credential exposure before publishing or deployment; retain local data, review history, remove artifacts from tracking with deliberate Git changes, rotate any reused exposed credentials. README password column removed; no rotation/history rewrite performed in audit.
2. **P1:** Implement a dedicated cancellation reason in model/migration, serializer, service, HTML form and events; reject blank/missing; test release and double cancellation.
3. **P1:** Reproduce and fix near-now seeder generation, add frozen-time tests and restore all 65 tests to passing/skipped-as-appropriate without changing real booking rules.
4. **P1:** Enforce interval conflicts on booking/reschedule and define grid/schedule-edit invariants; cover patient and doctor shifted-grid cases under locks.
5. **P1:** Select and verify target DB concurrency/constraint behavior, including same-slot and cross-doctor patient races. PostgreSQL is recommended by the existing design, not mandated by assessment.
6. **P1:** Review and commit all essential changes from a clean checkout; remove tracked runtime artifacts, verify reviewer repository access and dependency/runtime reproducibility.
7. **P1:** Add real PR CI with database service, migrations and tests; demonstrate both failure gating and a successful run.
8. **P1:** Correct Render working-directory/env/hosts/runtime configuration (or choose another provider), deploy publicly and verify static/auth/API/DB/production security.
9. **P1:** Connect a designated branch to automatic deployment, exercise an actual merged PR, record the public URL/branch/pipeline evidence in README.
10. **P1/P2:** Complete the honest owner-reviewed reflection; fix bonus upcoming filtering with tests; then improve query aggregation/pagination as scale requires.

Recommended next milestone: a **backend correctness and reproducibility pass** (reason handling, overlap protection, deterministic seed tests, upcoming filter, safe repository), followed by CI and real cloud delivery. Finish reflection with the owner before final submission. No major feature development was silently performed during this audit.

## P. Submission Checklist

- [ ] Shared repository link verified for reviewer access and current source pushed (origin configured).
- [ ] Real deployed application URL reachable at submission.
- [x] Current README includes local setup and retrospective design explanation.
- [ ] Historical design-before-code evidence available, or limitation explicitly disclosed.
- [ ] All four mandatory endpoints fully compliant (cancellation reason is missing).
- [x] Basic meaningful booking tests exist and pass.
- [ ] Entire test suite green; target-database concurrency verified.
- [ ] CI tests each PR and successful execution evidence retained.
- [ ] Designated-branch merged PR automatically deploys; demonstrated publicly.
- [ ] Complete and truthful four-question AI reflection.
- [ ] Database artifacts/credentials excluded from submitted source and exposed credentials handled.

Documentation changes in this audit: this report created; implementation report receives a current audit summary; README rewritten as requested with current setup/design/API status and a clearly incomplete reflection draft. Historical implementation-report entries remain, but this audit supersedes conflicting compliance/security/repository claims.

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
