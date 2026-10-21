# Render deployment and GitHub CI guide

Prepared 20 October 2026. **No commit, push, resource creation or deployment has been performed.** Local readiness does not establish completion of the assessment's hosted CI/deployment requirements.

## 1. Repository preparation

Repository layout (paths below are relative to Git root):

- Workflow: `.github/workflows/ci.yml`.
- Django root: `clinic-appointment-booking-system/`.
- Manage/requirements/blueprint: `clinic-appointment-booking-system/{manage.py,requirements.txt,render.yaml}`.
- Build script: `clinic-appointment-booking-system/scripts/render-build.sh`.

Review `git status` and `git diff` from Git root before a separately authorized commit/push. Include essential untracked runtime modules, migrations, templates and tests from prior milestones. Keep `.env`, `.local`, private accounts and databases out of Git. Review earlier history for sensitive artifacts. The root `.gitattributes` preserves LF in shell/YAML files. No new frontend runtime is required.

The local origin is `https://github.com/noelkips/clinic-appointment-booking-system.git`; reviewer permission and latest remote source still need verification. Run all Django commands below from the inner application directory unless noted otherwise.

## 2. GitHub branch protection

After an authorized push:

1. Repository Settings → Actions → General: enable GitHub Actions and permit checkout/setup-python; do not grant write permission unnecessarily.
2. Open a PR targeting `main` so GitHub registers the `PostgreSQL tests` job from workflow `CI`.
3. Settings → Rules → Rulesets (or branch protection): target `main`; require a PR, required reviews as appropriate, resolved conversations and the successful **PostgreSQL tests** status check. Select the exact check shown by GitHub after its first run.
4. Require the PR branch to be up to date; prohibit force pushes/deletions and restrict bypasses/direct pushes. Availability of enforcement depends on repository/account plan; confirm it actually applies.
5. The workflow also runs on pushes to `main`, so the merged revision is checked again. There are no paths filters or conditional test skips. If adopting a merge queue later, add/test `merge_group` support before enabling it.

The workflow uses Ubuntu 24.04, Python 3.13.12 and `postgres:18.6`. Service-only credentials in YAML are disposable test credentials, not production secrets. `contents: read` is the only requested token permission; checkout does not persist credentials. No Render secret or deploy hook belongs in Actions for this strategy.

## 3. Render account setup

Connect Render to the GitHub repository using the GitHub integration so it can see commits and checks. Review account quotas and plan costs before authorizing provisioning. Do not create a service from a public Git URL disconnected from the integration and assume checks will be detected.

The blueprint explicitly selects **free** web/PostgreSQL plans to avoid silently assuming paid features. This is assessment-hosting preparation, not a recommendation for real patient data. Render documents free cold starts, an expiring database, lack of managed backups and no free service shell/one-off jobs. Review current limits in [Render's free-plan documentation](https://render.com/docs/free) before creation. A free database expires after 30 days; plan continuity through submission and preserve authorized backups. Existing free-database quotas can block creation. No paid upgrade is authorized here.

## 4. Managed PostgreSQL creation

Preferred single provisioning path: Render → New → Blueprint → select repository and `main` → set blueprint path to **`clinic-appointment-booking-system/render.yaml`** → review the resource plan before applying. This creates `savannah-postgres` and `savannah-clinic` together when later authorized. Do not separately create duplicates with the same names.

The database uses PostgreSQL major 18 and `ipAllowList: []`, disabling external database access by default while the service uses Render's internal connection. Both resources must be in the same region. The owner connection must support schema changes and extension creation. Migration `0004` requests `btree_gist`; [Render lists it as supported](https://render.com/docs/postgresql-extensions).

If creation is done manually instead of Blueprint, create PostgreSQL first, same region as web, select its internal URL and mirror all blueprint values. Do not copy the local seeded database. External administration requires a deliberately limited IP rule and secure connection; restore the restriction after use.

## 5. Web service creation

For the Blueprint path above, review these generated settings rather than making a competing service:

| Setting | Value |
|---|---|
| Branch | `main` |
| Root directory | `clinic-appointment-booking-system` |
| Runtime | Python |
| Python version | `3.13.12` via `PYTHON_VERSION` |
| Build | `bash scripts/render-build.sh` |
| Start | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --access-logfile - --error-logfile -` |
| Health check | `/health/` |
| Auto-Deploy | **After CI Checks Pass** (`autoDeployTrigger: checksPass`) |

See [Blueprint schema](https://render.com/docs/blueprint-spec) and [Python selection](https://render.com/docs/python-version). A first Blueprint apply can initiate a deployment; treat Apply/Create as a deployment action requiring separate authorization. All setup here is prepared, not executed.

Render root-directory filtering means a change only to root `.github` files may not trigger an application redeploy; CI still runs. Use a reviewed application change for the final merge-to-deploy demonstration. Do not add a GitHub deploy-hook job alongside Render automatic deployment.

## 6. Environment variables

| Name | Production value |
|---|---|
| `DJANGO_SECRET_KEY` | Persistent, privately generated `secrets.token_urlsafe(64)` value supplied in Dashboard (`sync: false`), not the local key |
| `DATABASE_URL` | `fromDatabase` internal connection; never print it |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_TRUST_PROXY` | `True` only behind Render's trusted HTTPS proxy |
| `DJANGO_ALLOWED_HOSTS` | Blueprint includes localhost/127.0.0.1; settings append actual `RENDER_EXTERNAL_HOSTNAME`; add any verified custom domains explicitly |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Optional comma-separated HTTPS origins for actual trusted origins; empty for ordinary same-origin operation |
| `DEMO_SEED_ENABLED` | `False` |
| `DJANGO_ALLOW_SQLITE` | `False` |
| `PYTHON_VERSION` | `3.13.12` |

`DEBUG` and unprefixed `CSRF_TRUSTED_ORIGINS` are not supported environment keys. Do not invent an application domain before Render assigns one. Keep hosts without URL schemes; origins include the scheme. No wildcard hosts/origins are necessary.

Debug-off settings use secure session/CSRF cookies, HTTPS redirect, one-hour HSTS and console logging. HSTS is deliberately host-only with no preload commitment; Django advisory checks W005/W021 are silenced with source comments. Do not enable preload or includeSubDomains before confirming all relevant domains use HTTPS.

`DJANGO_TRUST_PROXY` tells Django to trust `X-Forwarded-Proto`. Verify Render strips/replaces client forwarding headers and that HTTPS requests are recognized as secure; never enable this on an untrusted direct server. Forwarded HTTPS tests exercise redirect-loop prevention locally, not Render's actual network boundary. Console logs use Django's request exception handling; do not log request bodies, environment values or credential URLs. This is not a comprehensive privacy/log-retention audit.

### Secret-key deployment failure and recovery

Render documents `generateValue: true` as a base64-encoded 256-bit random value (44 characters). Django's W009 length heuristic requires at least 50 characters, at least five distinct characters and no `django-insecure-` prefix. A Render-format random value reproduces W009 locally; it is not evidence that Render's randomness is weak. CI used a separate longer test-only key, so passing CI did not test the Render-generated value.

The reported Render W009 proves the effective setting failed Django's criteria, but the deployed value/metadata has not been inspected. A Dashboard override could produce the same warning. Settings load `.env` with `override=False`, so an existing Render environment value wins. No test settings are selected by the build script, no other key override was found, and `os.getenv` and `os.environ.get` are equivalent; duplicate assignments do not fix the problem.

The Blueprint now uses `sync: false` to request a persistent operator-supplied secret for new services. **Changing YAML alone does not replace the existing service's value.** For `savannah-clinic`, open Environment in Render Dashboard and replace `DJANGO_SECRET_KEY` with one privately generated strong value. Generate it once on a trusted Windows terminal and copy directly to the clipboard without displaying it:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64), end='')" | Set-Clipboard
```

Store it securely, paste it into the service's private environment field, then clear the clipboard with `Set-Clipboard -Value ''`. Do not paste it into chat, Git, CI variables, a build command or logs. Use Save only if offered; changing environment settings or choosing Save/Rebuild/Deploy can initiate a deployment, so do that only when authorized. Keep the value stable across builds and instances. Do not use the public CI key. Replacing an existing signing key invalidates existing signed sessions/tokens unless a separately planned fallback rotation is used; no fallback is added here.

After the fix is published through `development` ? PR ? `main`, confirm Render's service Environment contains the private value, the build uses `config.settings` (no unexpected `DJANGO_SETTINGS_MODULE=config.test_settings` override), and production check passes before collectstatic/migrations. If it still reports W009, verify the value's length/criteria privately; never print the value. Blueprint `sync: false` does not silently regenerate or update existing values on every sync. Build script retains `check --deploy --fail-level WARNING` unchanged.

Local recovery verification: **69 PostgreSQL tests passed in 7.219s**, including nine production-configuration/health/proxy tests, core booking, direct constraints, both concurrency scenarios and date boundaries. Production checks with a temporary strong in-memory key passed with only the existing two intentional HSTS advisories silenced; fresh static collection, WSGI/login, missing-migration and applied-migration checks passed. Compared clinic/auth rows were unchanged. The populated database was not migrated or reset. No secret was printed or persisted by validation. No live Render environment inspection/deployment was performed.

## 7. Database migration procedure

Migration ordering is unchanged: `0001_initial` → `0002` schedules/events → `0003_cancellation_reason` → `0004_appointment_interval_guards`. The final migration checks preexisting confirmed overlaps, installs `btree_gist` and doctor/patient GiST exclusions. Existing exact-start uniqueness remains. It must fail on incompatible data instead of silently rewriting it.

Free compute has no pre-deploy command. The prepared build script runs dependency checks, deploy checks, static collection, then `migrate --noinput` and `migrate --check`, with `set -euo pipefail`. This is a supported build-stage alternative; no seeding or administrator creation occurs. Never run this build script against your populated local database merely to test it.

**Trade-off:** migrations can affect the database while the previous version still serves, and a later deploy failure does not roll back schema changes. Use additive/backward-compatible migrations and backups; use a planned maintenance process for breaking changes. Only one service instance/deploy process should migrate the shared database. Do not add a second migration mechanism.

If a paid service is later chosen explicitly, move migrations to its supported pre-deploy command and remove them from the build script in the same change. Do not assume a free plan provides release commands. See [Render deploy stages](https://render.com/docs/deploys).

## 8. Static assets

The checked-in `static/css/tailwind.css` is already compiled. No Tailwind download/Node build is required on Render. Collection uses:

```bash
python manage.py collectstatic --noinput --ignore=src
```

`static/src/input.css` is CLI source and imports the Tailwind package by name; collecting it with manifest rewriting caused MissingFileError. Excluding its directory fixes the production build. WhiteNoise serves compressed hashed assets using `staticfiles.json`. Build scripts and CI use the same exclusion.

## 9. First authorized deployment

1. Finish source review, explicitly authorize commit/push and verify main's hosted CI before provisioning.
2. Create the Blueprint as described; confirm plans, assigned hostname, internal database URL and settings without disclosing credentials.
3. Inspect build logs: pip check, production checks, static collection, migrations. A failing stage must stop the deploy.
4. Confirm Gunicorn starts and `/health/` returns 200 after database connectivity. Health failures return generic 503, not database details; it is a simple connection check, not proof every migration/business rule is correct.
5. For production administration, use a separately authorized private bootstrap process. Free service shell/one-off jobs are unavailable. One option is a temporary IP-restricted external DB connection from a secured local environment, pointing only a dedicated settings/process environment at the production DB and running `manage.py createsuperuser` interactively. Never overwrite the local `.env`, publish passwords, use shared demo credentials or automate bootstrap in every build. Revoke temporary network access afterward.
6. Record the actual service URL and revision in README only after verification. No URL exists yet in these deliverables.

## 10. Production verification

Set `$appUrl` privately to the actual deployed origin; these are future commands, not an invented URL:

```powershell
Invoke-WebRequest -Uri "$appUrl/health/"
Invoke-WebRequest -Uri "$appUrl/accounts/login/"
Invoke-WebRequest -Uri "$appUrl/doctors/"
```

Check HTTPS redirect, certificate, secure cookies, CSRF login/logout, correct role dashboards, static URLs/manifest, no DEBUG traceback, doctor availability and all required APIs. Use disposable authorized records for booking/conflict/cancel/reschedule verification, preserving existing data. Test real browser mutation submissions and role isolation. Inspect extension/exclusions through an authorized database connection. Observe logs for secrets/errors. Confirm any custom domain is explicitly allowed and health checks succeed with that host.

Render may treat redirects as healthy, so explicitly inspect a direct HTTPS **200** JSON response from `/health/`; a 301 loop must not be counted as success. [Health-check behavior](https://render.com/docs/health-checks).

## 11. Pull request CI verification

After authorized push, open a PR to `main`. Confirm that all steps run against PostgreSQL and the complete test output includes both `PostgreSQLConcurrencyTests` and `IntervalConcurrencyTests`, without backend skips. Capture the run URL and commit SHA. Do not rely only on a green job name.

In a disposable PR, introduce a deliberately failing assertion, verify the required check fails and merging is blocked, then revert that assertion and confirm green. No failing change needs to reach main. Verify branch-protection enforcement on the actual account plan. No hosted run has been performed in this task.

## 12. Automatic deployment verification

Single mechanism: Render's **After CI Checks Pass**, linked to `main`. PR checks gate merging via branch protection; a merged PR then triggers this workflow's main push check. Render waits for the linked revision's checks before deploying. Render considers neutral/skipped checks passed, so keep the test job unconditional and require its successful status; zero detected checks or failed checks do not trigger deployment. See [Render CI integration](https://render.com/docs/deploys).

Merge a reviewed application change after separate authorization. Capture PR URL, merged SHA, main CI run URL, Render deploy event/SHA and public response showing the new version. Failed main CI must not deploy. Direct pushes can also trigger checks/deploys; enforce the PR-only policy in GitHub. This requirement remains incomplete until the actual observed sequence succeeds.

## 13. Rollback and troubleshooting

- **CI cannot connect:** confirm service health/5432 mapping, PostgreSQL credentials and extension support. CI-only role is an ephemeral superuser for test DB creation; do not reuse it in production.
- **Test DB privilege failure:** grant CREATEDB only to local/test credentials; extension install needs appropriate DB ownership/privileges. Never run tests on production.
- **BadHost/CSRF/redirect loop:** inspect actual hostname, allowed hosts, origins and HTTPS forwarding. Do not disable security checks to hide a proxy mismatch.
- **Static MissingFileError:** confirm `--ignore=src`, checked-in compiled CSS and application working directory. Rebuild assets if references changed.
- **Migration overlap/privilege error:** stop and review data/extension ownership. Preserve constraints; do not delete records or fake-apply migrations.
- **No auto-deploy:** check `main`, `checksPass`, GitHub integration, detected checks, rootDir filters and skip phrases. Avoid adding a second trigger as a workaround.
- **Rollback:** stop automatic promotion if necessary, select a known good revision in Render and verify health. Code rollback does not reverse migrations. Use backward-compatible schema or an explicitly approved database recovery plan/backup restore; do not blindly reverse migrations or restore over live data. Re-enable the intended automatic trigger only after the incident is resolved.
- **Free plan:** cold starts, expiry, missing shell and absent managed backups are real constraints. Upgrade only with approval or arrange a supported alternate operating process.

## Local validation

Executed locally in this milestone:

- Django system checks, no missing model migrations, pip check: PASS.
- Full PostgreSQL suite with `config.test_settings`: **88 tests, 31.577s, OK, no skips**; final CI-like-environment rerun with demo seeding disabled: **88 tests, 31.546s, OK, no skips** (including concurrency and five new health/proxy regressions). Seeder/rotation test messages concern the isolated test database only.
- `DJANGO_DEBUG=False`, proxy trust enabled: deploy checks PASS with W005/W021 deliberately silenced; static collection with source exclusion PASS; WSGI import and manifest-backed login/HTTPS health smoke PASS.
- Initial deploy checks reported the intentional HSTS advisories; initial static collection exposed the Tailwind source import error, corrected by source exclusion. No business-rule/migration changes made.

GitHub workflow and Render YAML both passed local JSON Schema validation using the public GitHub SchemaStore and Render schemas. A fresh isolated static output directory passed manifest collection and a real static response, login/health responses, proxy/origin/hostname setting assertions and read-only extension/exclusion checks. Development totals remain 5 doctors, 21 patients, 100 appointments and 115 events. Five health/proxy regressions were rerun after final settings changes: PASS in 0.290s. Full-suite outputs are in ignored `.local/ci-full-tests.txt` and `.local/ci-final-tests.txt`; schemas and smoke scripts are also local ignored artifacts. Bash syntax-only validation passed. All 19 local documentation links and nine README sections passed; actual private environment values are absent from prepared public files. `git diff --check` passed with line-ending notices only. These validate source configuration, not hosted execution. Linux Gunicorn execution and actual GitHub/Render validation remain unverified until hosted execution; Windows can import the Django WSGI application but cannot run Gunicorn's Unix worker runtime.


## 14. Explicit one-time demo seeding on Render Free

Current investigation (21 October 2026): `seed_assessment_demo` was implemented and committed in `910b248` on development. Local main and cached origin/main point to `c5910f1`, which lacks that implementation. Remote refresh failed, so current GitHub main and Render's deployed SHA still require Dashboard verification. Builds only migrate; migrations do not create demo records. `DEMO_SEED_ENABLED=False` intentionally blocks the local `seed_demo`; it does not control `seed_assessment_demo`, which requires its own explicit gate and target confirmation.

The Blueprint uses Render's internal connection string and `ipAllowList: []` (external access disabled). Actual Dashboard configuration may differ. No live inventory has been obtained; the local .env targets a loopback database and must not be used to infer live counts. The owner-supplied application URL is https://savannah-clinic-diul.onrender.com/ (older documentation had `duil`).

Use a trusted workstation, not GitHub Actions. No workflow, HTTP endpoint or build hook is added. Render Free has no Shell/one-off jobs. See [Free limitations](https://render.com/docs/free) and [external PostgreSQL connectivity/network restrictions](https://render.com/docs/postgresql-creating-connecting).

1. Review these changes and the existing seeder. Publication/merge/deployment require separate owner authorization; none were performed here. Confirm the checked-out schema matches the live deployed revision. No migration or test suite may be run against production by this procedure.
2. In Render, identify the **existing database attached to savannah-clinic**, its database name and full external hostname. Verify the deployed SHA and internal DATABASE_URL refer to that same database. Never create a replacement database. Privately preserve a backup where supported.
3. Only with owner authorization, temporarily add the trusted workstation's public egress IPv4 `/32` to this database's network allowlist. Preserve other authorized entries; never add `0.0.0.0/0`. Copy its External Database URL privately from Connect. The internal URL does not work from a workstation. If policy disallows external access, stop and use the alternative below.
4. Use Python 3.13 and the pinned requirements in a private virtual environment. Open a new, non-transcribed terminal in the inner Django directory. Do not edit .env or print the URL. Run:

```powershell
.venv/Scripts/python.exe scripts/render-demo.py inspect
```

The URL is entered at a hidden prompt. The runner requires a full Render external hostname, forces `sslmode=verify-full`, `sslrootcert=system`, a connection timeout, checks negotiated TLS and actual database name, checks pending migrations without applying them, then prints counts/collisions. libpq must support the system trust store; the pinned psycopg binary supplies modern libpq. If certificate verification fails, repair the trusted CA installation/client configuration; do not downgrade TLS. A successful inspect proves this workstation can connect through the current allowlist. It does not prove another runner can connect.

5. Review counts, existing username collisions and target identity. Obtain explicit owner authorization for **this inspected database** and the 27 fictional identities/100 appointments. Generate three independent random passwords (for example with a password manager, at least 24 characters and five distinct characters) and save each privately. The additional fixture users have unusable passwords. Do not reuse a password from .env. Run only after authorization:

```powershell
.venv/Scripts/python.exe scripts/render-demo.py seed
```

Re-enter the external URL privately. Inspect the repeated inventory, then type the displayed `SEED hostname/database` phrase. Enter administrator, doctor and patient passwords at the hidden prompts. The runner enables ASSESSMENT_DEMO_ENABLED only inside this process. Seeding is transactional, additive and ownership-checked; it never resets/deletes data. Stable markers preserve appointments on rerun. Existing non-demo identity collisions abort. Database constraints remain active. Dataset: 5 doctors, 20 patients, 100 visits (85 confirmed, 15 cancelled), weekday schedules, historical/future visits and one rescheduling event. Existing non-demo records can make total database counts higher.

6. Obtain explicit authorization for an idempotency rerun, run the same `seed` command with the **same passwords**, and compare inspection/fixture counts before and after; they must not increase. Local regression tests also compare every appointment value and password hash. No automatic rerun is performed by the wrapper.
7. Run read-only verification:

```powershell
.venv/Scripts/python.exe scripts/render-demo.py verify
```

Enter the three stored passwords when prompted. The credential-free JSON reports total and fixture counts, statuses, historical/future visits, rescheduling events, free slots over the next 14 days and authentication/role results. It exits nonzero on incomplete data, missing future slots or failed credentials. This tests Django authentication without writing sessions; separately sign in over HTTPS to the owner-confirmed live URL and confirm `/platform/`, `/doctor-dashboard/`, `/dashboard/` for the respective accounts. Record live results and any errors in LIVE_DEMO_VERIFICATION.md. Reruns preserve original dates; aged fixtures require a separately reviewed additive refresh, never a reset.
8. Close the process, clear clipboard and restore the prior network allowlist/remove the temporary `/32`. Revoke any temporary database role. Keep the web service's DEMO_SEED_ENABLED=False; do not add ASSESSMENT_* secrets to Render or GitHub. Share reviewer credentials only through a password manager or agreed private assessor channel.

Required process configuration: the wrapper prompts for DATABASE_URL, creates an ephemeral DJANGO_SECRET_KEY for Django initialization, enforces DJANGO_DEBUG=False and config.settings, and sets ASSESSMENT_DEMO_ENABLED=True only after confirmation. No production signing key is needed. Direct management-command use instead requires DATABASE_URL, DJANGO_SECRET_KEY, DJANGO_DEBUG=False and (for writes) ASSESSMENT_DEMO_ENABLED=True plus `--confirm-database <exact-name>`. Passwords may be entered at hidden prompts; optional process-only variables are ASSESSMENT_ADMINISTRATOR_PASSWORD, ASSESSMENT_DOCTOR_PASSWORD, ASSESSMENT_PATIENT_PASSWORD. Never store them in repository files or command arguments. `--rotate-passwords` is a separate action requiring separate authorization.

If external access is prohibited or unavailable, do not bypass network restrictions. Leave seeding pending. A separately authorized temporary paid service upgrade can provide Shell access in Render's private network: use the reviewed revision, existing internal DATABASE_URL, run `python manage.py seed_assessment_demo --inspect`, then after target-specific approval `ASSESSMENT_DEMO_ENABLED=True python manage.py seed_assessment_demo --confirm-database <inspected-name>` and enter passwords privately. Run `python manage.py verify_assessment_demo`, then remove temporary secrets/access. Confirm charges and lifecycle before any upgrade. Never put the command in start/build commands. No paid operation was requested or performed.
