# Final assessment compliance audit

> Later preparation milestone: CI workflow, production settings and Render blueprint are now implemented locally; README has been shortened to nine sections. This matrix preserves the pre-CI audit and its original section references. Hosted CI, deployment and merge-to-deploy evidence remain unverified. See [current deployment guide](RENDER_DEPLOYMENT_GUIDE.md) and [README](../README.md).

Audit date: **20 October 2026**, Africa/Nairobi. Scope: current local working tree, including uncommitted changes. This is a documentation/source audit; it did not rerun application tests, change business logic, alter migrations/data/passwords, commit/push or deploy.

## 1. Verdict and source of truth

**PARTIAL overall; not ready for final submission.** Section 2 and both bonus behaviors have recorded PostgreSQL verification. Section 1's technical content is documented, but design-before-code timing remains unverified. Section 3 has no verified public deployment or CI/CD. Section 4 still needs developer confirmation, explicitly left as TODO at the developer's request.

The authoritative source is the four-page [Savannah Informatics Backend Assessment (AI) (1).pdf](<../Savannah Informatics Backend Assessment (AI) (1).pdf>). All four pages were freshly extracted from the actual PDF with local pypdf and read for this audit. SHA-256: `ab13835063e146c619c20e28b9352eae135facb777f4b953e37a18b961258a16`.

| PDF location | Requirements extracted |
|---|---|
| Page 1 | Connected four-section clinic scenario; 3–5-day time limit; AI permitted/expected; cloud provider choice; CI/CD automatic deployment on merge |
| Page 2 | GitHub/GitLab repository public or shared; running application link; README with decisions, local run and CI/CD note; reflection in README or separate file; any database allowed; document choices for ambiguities and show reasoning |
| Page 3, Section 1 | Five doctors, set working hours, 30-minute slots, doctor/day free-slot lookup, booking removes availability, cancellation, growth; document models/components/decisions/trade-offs in README **before coding** |
| Pages 3–4, Section 2 | DRF/FastAPI/Go REST API and database; four specified endpoints; meaningful validation/status codes; sensible multi-file structure; basic booking tests |
| Page 4, bonuses | Upcoming patient appointments sorted by date; prevent bookings within one hour |
| Page 4, Section 3 | Cloud application publicly reachable at submission; tests on every PR; automatic deploy after PR merge into designated branch; README public URL, deployment branch/how and pipeline description |
| Page 4, Section 4 | AI use across all four sections; improvement example and actual prompt; incorrect/incomplete output and detection; two independent decisions and why judgment was trusted; honesty |

No extra official scoring scheme is inferred. PostgreSQL, Tailwind, dashboards and Render are project choices, not mandatory technology requirements in the PDF.

## 2. Evidence and status conventions

- **PASS:** implemented and supported by inspected source plus recorded verification where relevant.
- **PARTIAL:** some required content/behavior exists, with an identified gap.
- **FAIL:** required deliverable/behavior missing or not complete.
- **NOT VERIFIED:** evidence cannot establish the historical/external claim.
- Priorities: **P1** required before submission; **P2** production/engineering improvement; **P3** optional enhancement. These are audit priorities, not an official rubric.

Evidence reviewed: models, services, API/serializer, both route inclusions, views/forms/admin, migrations `0001`–`0004`, settings/test settings, requirements, seeder/demo helpers, tests, navigation, templates/static sources, `.env.example`, `.gitignore`, Render blueprint, local Git metadata, README and all three existing tracked reports. The sensitive local account reference was recognized as private operational material and was not consolidated or copied into public documentation. There is no separate `serializers.py` or PostgreSQL cheat sheet.

Recorded results are from [functional verification](APPLICATION_FUNCTIONAL_VERIFICATION.md) and available local artifacts, not fresh test execution in this audit. The user additionally confirmed a previous 80/80 PostgreSQL milestone. The older 80-test log available locally is SQLite-era with one skip; these are kept distinct.

## 3. Mandatory compliance matrix

### Section 1 — System Design

| ID / requirement | Status | Source evidence | Verification evidence | Remaining work | Priority |
|---|---|---|---|---|---|
| S1.1 README design before any code (p3) | NOT VERIFIED | README now describes current design; local history begins with code and README together | Inspected three local commit subjects; earlier audit also found no ordering proof | Developer TODO: original dated design artifact/history, if available; do not backdate current prose | P1 |
| S1.2 Identify models and components (p3) | PASS | `clinic/models.py`, `services.py`, `api.py`, `views.py`, `forms.py`, `config/`; README §§4–5 | Source/model/route inspection; architecture and ER diagrams match relationships | Preserve accuracy as code changes | P2 |
| S1.3 Explain decisions and trade-offs (p3) | PASS | README §6: monolith, DRF, templates, PostgreSQL, derived slots, locks, duration, growth limits | Compared prose to source; clearly retrospective reasoning | Original personal reasoning remains separate reflection TODO | P2 |
| S1.4 Five-doctor clinic and set hours (p3) | PASS | Doctor, DoctorAvailability, seeder with five doctors; README §§5–7 | Recorded runtime has five doctors; hours/split-period tests | Five is dataset size, not hard maximum | P3 |
| S1.5 30-minute free slots by doctor/day, exclusive booking and cancellation (p3) | PASS | `available_slots`, `validate_slot`, `book_appointment`, `change_appointment` | Recorded availability, persistence, conflicts, release and concurrency tests | Current browser mutation gap tracked separately | P2 |
| S1.6 Starting small with growth (p3) | PASS | README §6 describes aggregation, pagination, profiling and future policies | Source confirms repeated counts/unpaginated queries | Implement optimizations when justified; no scalability benchmark | P2 |

### Section 2 — API Implementation

Actual routes are `/api/...` and equivalent root aliases, without trailing slashes, from `config/urls.py`, `clinic/urls.py`, `clinic/api_urls.py`. All use SessionAuthentication and IsAuthenticated. Public HTML profiles separately expose doctor availability.

| ID / requirement | Status | Source evidence | Tests / recorded verification | Remaining work | Priority |
|---|---|---|---|---|---|
| S2.1 DRF/FastAPI/Go and a database (p3) | PASS | DRF views/AppointmentSerializer in `clinic/api.py`; PostgreSQL in settings | Recorded PostgreSQL 18.6, `clinic_local`; source/dependencies reviewed | None for prescribed stack choice | P2 |
| S2.2 POST appointment persists (p3) | PASS | `create_appointment`, atomic `book_appointment` | `ClinicTests.test_booking_persists`; 57-check development transaction | None for API requirement | P2 |
| S2.3 POST validates working hours/full slot (p3) | PASS | `schedule_matches` and `validate_slot` | `test_no_hours_rejected`, `test_gap_rejected`, `test_off_grid_rejected`, `test_partial_last_slot_rejected` | Leave/overnight policy optional | P2 |
| S2.4 POST rejects past appointment (p3) | PASS | `starts <= now + one hour` validator | `test_past_rejected`, `test_one_hour_rejected` | None | P2 |
| S2.5 POST rejects occupied slot (p3) | PASS | Doctor/patient parent locks; overlap query; SQL exclusions and exact-start uniqueness | Double-booking tests, direct SQL insert/update tests, both concurrency scenarios | No load-test claim | P2 |
| S2.6 GET doctor/day available 30-minute slots (p3) | PASS | `api.availability`, `available_slots` | Split periods, malformed date, occupation/release; previous-day overlap; maximum-date regressions | Doctor availability intentionally does not prefilter patient conflicts | P2 |
| S2.7 PATCH cancel with reason (p3) | PASS | `validate_cancellation_reason`; separate model field; serializer response | Missing/blank/invalid/long reasons rejected; trimmed value persisted; HTML/API tests | Historical blank reasons are not fabricated | P2 |
| S2.8 Cancellation releases slot (p3) | PASS | Status becomes cancelled; occupancy uses confirmed only | `test_cancel_releases_slot`; remediation rebooking/release tests | Notice still applies to released slots | P2 |
| S2.9 Already-cancelled error (p3) | PASS | Upcoming confirmed guard in `change_appointment` | `test_cancel_reason_persisted_trimmed_and_repeated_cancel_rejected`; recorded HTTP 400 | None | P2 |
| S2.10 Reschedule validates new slot like booking (p3) | PASS | Shared `validate_slot` in atomic change service | Aware rescheduling, hours/gap/conflict, patient/doctor overlap and exact-hour tests | Endpoint retains same doctor, documented choice | P2 |
| S2.11 Reschedule releases old slot and preserves original on failure (p3) | PASS | Transactional same-row timestamp update | `test_reschedule_aware_releases_old_slot`, rollback regressions and reversible probes | Browser visual review remains incomplete | P2 |
| S2.12 Reject cancelled rescheduling (p3) | PASS | Confirmed/future guard | `test_cancelled_cannot_reschedule`; development probes | None | P2 |
| S2.13 Meaningful errors / correct HTTP statuses (p3–4) | PASS | Serializer errors and `mutation_error` | Recorded 201/200 success, 400 validation, 403 auth/CSRF, 404 hidden/not found, 409 conflicts | Generic IntegrityError-to-conflict mapping is coarse but explicit | P2 |
| S2.14 Sensible multi-file structure (p4) | PASS | Models/services/API/views/forms/config/templates separated | Source tree inspected | Large views module/formatting can improve later | P3 |
| S2.15 At least basic booking tests (p4) | PASS | `clinic/tests.py`, `test_remediation.py`, `test_functional_verification.py` | Recorded 60 targeted PostgreSQL tests, zero failures/errors/skips | New full-suite count not measured in this audit | P2 |

### Section 3 — Deployment & CI/CD

| ID / requirement | Status | Source evidence | Verification evidence | Remaining work | Priority |
|---|---|---|---|---|---|
| S3.1 Deploy same application to a cloud provider (p1/p4) | FAIL | `render.yaml` draft only | No deployment event or service evidence | Correct configuration, provision and deploy in a later authorized milestone | P1 |
| S3.2 Public URL reachable at submission (p4) | FAIL | No public URL in project evidence | Localhost is development only | Obtain public URL; smoke-test static/auth/API/database | P1 |
| S3.3 Automated suite on every PR (p4) | FAIL | No `.github/workflows` at either root; no alternative CI found | No successful run evidence | Add PostgreSQL PR CI and demonstrate success/failure gating | P1 |
| S3.4 Auto-deploy after PR merge into designated branch (p4) | FAIL | No configured workflow/verified Render trigger; branch designation absent | Local `main` is not deployment evidence | Choose branch, configure protected merge/deploy flow, observe real merged PR deployment | P1 |
| S3.5 README public deployed URL (p4) | FAIL | README §2 honestly marks pending | No URL supplied/verified | Add verified live URL after deployment | P1 |
| S3.6 README branch and how deployment triggers (p4) | PARTIAL | README §17 explains proposal; no branch falsely designated | No running mechanism | Replace planned behavior with actual branch/trigger/run evidence | P1 |
| S3.7 README pipeline description (p4) | PARTIAL | Planned stages, PostgreSQL, secrets/failure behavior documented | Actual pipeline missing | Describe implemented behavior once verified | P1 |

### Section 4 — AI Reflection

| ID / requirement | Status | Source evidence | Verification evidence | Remaining work | Priority |
|---|---|---|---|---|---|
| S4.1 AI use across all four sections (p4) | PARTIAL | README §19 distinguishes observed assistance, reports and planned deployment | This conversation: verification, correction, source/PDF audit and documentation | Developer TODO: confirm original design/API assistance and actual use by section | P1 |
| S4.2 Useful suggestion including actual prompt (p4) | PARTIAL | README quotes actual Task 4 instruction and explains boundary guard/regressions | Recorded conversation, new boundary tests and functional report | Developer TODO: confirm personal example or provide preferred actual historical prompt | P1 |
| S4.3 Wrong/incomplete output and detection (p4) | PARTIAL | README describes AI verification harness's seeded-patient conflict and corrected assertion | Actual 409 response/harness correction in conversation and functional report | Developer TODO: confirm or supply own example; no unsupported attribution of application defects | P1 |
| S4.4 Two decisions without AI and why judgment trusted (p4) | FAIL | Explicit README TODO | Developer instructed “TAG THIS AS TODO IN README” | Developer must supply two independent decisions and reasons; AI cannot infer independence | P1 |

### Submission instructions and general rules

| ID / requirement | Status | Source / verification evidence | Remaining work | Priority |
|---|---|---|---|---|
| SUB1 GitHub/GitLab link public or shared (p2) | PARTIAL | Local origin URL documented; external fetch attempt returned cache-miss/error, not access evidence | Verify reviewer access and latest source on remote | P1 |
| SUB2 Running application link (p2) | FAIL | No verified public URL | Complete S3.2 | P1 |
| SUB3 README design/local run/CI note (p2) | PASS | Rewritten 22-section README includes these, with pending CI explicitly marked | Operational and deployment examples remain unexecuted by this documentation task | P2 |
| SUB4 Reflection in README/separate file (p2) | PARTIAL | README §19 exists, but content incomplete | Complete S4 TODOs | P1 |
| GEN1 Document decisions where ambiguous (p2) | PASS | README strict one-hour boundary, authenticated API, future-confirmed list, same-doctor rescheduling, five doctors as data | Source agrees with documented choices | Retain when requirements evolve | P2 |
| GEN2 Clear reasoning, connected design/build/deploy (p1–2) | PARTIAL | Current design/build aligned; deployment not delivered | Finish same-application cloud delivery | P1 |
| GEN3 3–5-day time limit (p1) | NOT VERIFIED | PDF instruction noted; no complete start/submission timeline | Developer to confirm timing if requested | P1 |
| GEN4 AI allowed/expected; honest reflection (p1–2/p4) | PARTIAL | AI assistance evident; unknown personal history marked TODO | Developer confirmation; avoid invented experiences | P1 |

## 4. Bonus requirements (separate from mandatory)

| Requirement | Status | Source | Tests / verification | Remaining work | Priority |
|---|---|---|---|---|---|
| GET patient upcoming appointments sorted by date (p4) | PASS | `patient_appointments`: confirmed, future, order by `starts_at`, `pk` | `test_bonus_upcoming_filter_sort_and_permissions`; recorded owner/admin/doctor/anonymous restrictions | Admin unknown-patient empty-list behavior documented | P3 |
| Prevent bookings within one hour (p4) | PASS | Shared `validate_slot` rejects `<= now + one hour` | Booking test plus exact-boundary/equivalent-UTC reschedule regression; development probes | Strict equality choice documented | P3 |

## 5. Recorded verification and provenance

| Record | Outcome / interpretation |
|---|---|
| Developer-confirmed PostgreSQL milestone | 80/80 automated tests passed including concurrency; acknowledged as supplied historical evidence, original full-run PostgreSQL log not located |
| Functional verification targeted command | 60 PostgreSQL tests in 4.563s; OK, no skips; local `.local/task4-regression.txt` and functional report |
| Boundary-only run | 3 tests in 0.152s; service/public/API guard tests pass, already included in the later targeted 60 |
| Populated database checks | 57 passed; explicit transaction rollback; all compared User/Doctor/Patient/Appointment/Event fields unchanged |
| Chrome viewport matrix | 63 combinations at 320/768/1440px; no overflow, JS exceptions or failed local HTTP responses |
| Chrome interactions | 7 passed: mobile open/close, form validation, real availability fetch, slot selection, empty availability, authenticated redirect |
| Boundary browser follow-up | Corrected public maximum-date page passed |
| Current runtime in functional report | PostgreSQL 18.6, local `clinic_local`, 5 doctors, 21 patients, 100 appointments, 115 events |
| Older remediation full run | SQLite-era 80 run, 79 passed, one PostgreSQL skip; distinct historical evidence, not current PostgreSQL failure |

Three boundary tests were added after the earlier 80-test milestone. Do not advertise the current total as exactly 80 or infer a fresh full-suite success from a targeted run. No full application suite, seeder or browser matrix was executed in this audit. Documentation QA checks are listed below separately.

Current browser booking/cancel/reschedule **submissions** remain NOT VERIFIED on PostgreSQL; API/HTML regression coverage does not establish every browser interaction. Older implementation-report SQLite workflows remain historical, not fresh PostgreSQL evidence. Physical devices, other engines and production behavior are also unverified.

## 6. Configuration, security and delivery findings

| Finding | Current evidence / impact | Action | Priority |
|---|---|---|---|
| Nested repository layout | Git root contains inner app; blueprint lacks `rootDir`, commands assume app directory | Configure app working directory/blueprint location before deploying | P1 |
| Render variable mismatch | Blueprint uses `DEBUG`; settings read `DJANGO_DEBUG` (default false) | Correct variable; review hosts, secrets, database and runtime | P1 |
| Production hosts/runtime missing | Blueprint has local-host defaults and no Python runtime pin | Configure actual hostname/runtime; smoke-test real environment | P1 |
| Trusted-origin env unsupported | Settings do not read `CSRF_TRUSTED_ORIGINS`; `.env` entry alone is ineffective | Evaluate same-origin/proxy setup; wire additional settings only if needed | P1 |
| HTTPS deployment unverified | Secure cookies configured when debug off; proxy trust/redirect/HSTS not explicitly configured | Verify HTTPS headers/cookies/auth on real service | P1 |
| CI absent | No workflow despite older report claims | Implement PR checks and verified merge deployment | P1 |
| Source publication incomplete | Essential local changes remain staged/modified/untracked | Owner-authorized review/commit/push later; no commit during audit | P1 |
| Historical artifacts | Index no longer includes SQLite/pyc, but earlier commits retain artifacts | Review exposure; keep secrets/demo data out of production | P1 |
| Maintenance bypass | Admin registers models directly; ORM/admin do not route all mutations through locked/event services | Define maintenance policy; SQL overlap checks are not all business rules | P2 |
| Schedule changes | Working-period overlap validated in clean/forms; SQL does not exclude period overlap or protect existing visits from later schedule edits | Define safe schedule-change/leave policy | P2 |
| Abuse controls | No application login throttling; no penetration/load test | Add appropriate controls before real patient use | P2 |
| Scalability/history | Unpaginated queries, repeated counts, events lack before/after slots | Profile, aggregate, paginate, enrich history as needed | P2 |
| Password recovery | Explicit coming-soon informational page | Optional account-recovery implementation; not a mandatory PDF endpoint | P3 |

No application changes were made to resolve these findings because this task expressly restricts business-logic, migration and deployment changes.

## 7. Documentation consolidation and corrections

The existing README was replaced, not extended with another dated appendix. It now contains all 22 requested topics: overview, URLs, features, architecture, models, trade-offs, rules, five-endpoint API reference, roles, Windows setup, actual environment variables, database operations, demo safeguards, tests, security, planned deployment/CI, compliance, honest reflection TODOs, source tree, limitations and index.

Sources consolidated:

- Previous README: relevant route/setup/design material, rewritten against current source.
- `IMPLEMENTATION_REPORT.md`: architecture/UI/history and demo composition, without copying stale current-state counts or claims.
- `ASSESSMENT_COMPLIANCE_AUDIT.md`: original findings and remediation history, superseded by current matrices without deleting the history.
- `APPLICATION_FUNCTIONAL_VERIFICATION.md`: PostgreSQL evidence, corrected date boundary, actual browser scope and outstanding manual work.
- Actual settings/URLs/models/services/migrations/seeder/Render config: authority when older prose conflicts.

Corrections include:

1. PostgreSQL is now verified locally; old SQLite/no-server claims are dated history.
2. Full-suite 80/80 developer confirmation, old SQLite 79+skip and targeted PostgreSQL 60 are separate results.
3. Cancellation reason and bonus filtering defects were fixed; no longer listed as open mandatory API failures.
4. Five doctors is a dataset scenario, not an enforced model maximum.
5. API prefixes, no trailing slash, session CSRF, Patient-vs-User IDs and actual response fields/errors are explicit.
6. Environment names use `DJANGO_*`; unsupported trusted-origin env configuration is not presented as implemented.
7. Render YAML is draft configuration; no live URL/branch/CI success invented.
8. Database counts/time-sensitive upcoming totals from older reports are not current truth.
9. Earlier no-Git/workflow-exists claims are superseded by actual Git metadata and absent workflows.
10. No independent human decisions, missing prompt history or AI authorship of application defects is invented.
11. No PostgreSQL cheat sheet was found; README contains concise procedures instead of a broken link.
12. Private credentials/roster passwords remain outside tracked documentation.

The three original supporting reports remain untouched. Their historical claims are explicitly qualified through the new README and this final audit. The private local credential reference is not linked as public documentation.

## 8. Documentation quality control

Validation scope: local link/file checks; unique 22-section structure; URL resolution for primary and alias API routes; serializer/model fields; test labels; seeder help; source/config comparison; absence of actual private credential values; Git whitespace check. Fresh installation, database provisioning/restore and cloud commands are instructions reviewed against source/tool help, not operations executed against the populated environment.

External repository retrieval was attempted but failed with a cache-miss/error. The URL is verified as configured Git origin only; remote existence/permissions/current source are NOT VERIFIED. No deployment link is fabricated.

**PASS: 67 documentation checks** executed by the local `.local/final_docs_qa.py` harness: all local Markdown link targets exist, the README has exactly 22 sequential top-level sections, JSON examples parse, documented source paths exist, both sets of API routes resolve to their actual DRF callbacks, serializer/model fields agree, command names and test labels exist, and neither deliverable contains the current private secret/password values. `manage.py seed_demo --help` was inspected without invoking seeding. `git diff --check` passed with line-ending conversion notices only. The first QA route-name assertion needed correction because DRF wraps the view name; callback identity checks then passed. Application test outcomes above remain historical.

## 9. Developer confirmation and remaining submission work

At the developer's instruction, README TODOs explicitly request original AI usage by section, confirmation/preferred prompt and mistake examples, two genuinely independent decisions with reasons, and any original design-before-code evidence. No further answer is required to complete the documentation deliverables.

Prioritized next milestone: **GitHub Actions CI/CD implementation and Render preparation**. First review current source, define the deployment branch, add PostgreSQL PR tests/migration checks and branch protection. Then correct the draft Render configuration, deploy, verify public HTTPS/static/auth/API/database behavior and demonstrate a merged PR automatically updating it. Record real links/run evidence and complete reflection before submission. Current browser mutation checklist should be finished before claiming complete browser end-to-end verification.

Files intentionally changed by this documentation task: `README.md` and `docs/FINAL_ASSESSMENT_COMPLIANCE_AUDIT.md`. Original reports, application logic, migrations and existing demonstration data are preserved.
