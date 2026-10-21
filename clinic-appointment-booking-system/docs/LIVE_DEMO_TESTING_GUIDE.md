> Updated 21 October 2026: use the guarded executable procedure in [Render guide section 14](RENDER_DEPLOYMENT_GUIDE.md#14-explicit-one-time-demo-seeding-on-render-free). It enforces external-host TLS verification and adds read-only reporting. The older direct-command procedure below is background reference. Hosted execution remains pending explicit authorization.

﻿# Live assessment demonstration: operation and verification

This is a temporary fictional assessment environment, not a clinical deployment. No live seed has been executed by this change. The owner supplied `https://savannah-clinic-duil.onrender.com/`; public reachability checks are recorded below. Public pages cannot establish whether a database is empty.

## Existing versus hosted seeder

`seed_demo` remains unchanged: it requires DEBUG, DEMO_SEED_ENABLED and a loopback host, uses one shared password and creates local superusers. Do not weaken its safeguards or use it on Render.

`seed_assessment_demo` is a separate, manually invoked additive command. It requires PostgreSQL, process-only `ASSESSMENT_DEMO_ENABLED=True` and exact `--confirm-database`. It never runs from builds, deployments, migrations or an HTTP endpoint. No new workflow or web management endpoint is added.

Fresh dataset: five doctors, twenty patients, two staff administrators, fifty Monday–Friday working periods (09:00–12:00 and 14:00–17:00 Nairobi), 100 appointments, fifteen cancellations with fictional reasons, past/future history and one rescheduling event. Past visits deliberately use the existing validator's historical mode within this explicitly gated command; ordinary booking still rejects past times. Future visits begin at least two calendar days ahead. SQL exclusion constraints remain enabled. Many slots remain free. Dates are fixed on first insertion; reruns preserve history rather than silently advancing it. If the demonstration ages out, review an additive refresh separately rather than reset.

## Reviewer identities (planned, not live-verified)

| Role | Username | Access |
|---|---|---|
| Administrator | demo_admin | Staff dashboard and appointment oversight; no superuser/model permissions |
| Doctor | demo_doctor | Own assigned appointments and weekly schedule |
| Patient | demo_patient | Own visits, booking, cancellation with reason and rescheduling |

Remaining fixture users have unusable passwords. Both administrators are staff, not superusers; only demo_admin has a reviewer password. Staff can see clinic-wide records and change eligible appointments, so release that credential only to authorized assessors. Do not use this mode with real patient data. Doctors remain active for booking even when auxiliary logins have unusable passwords.

Primary passwords are read from hidden terminal prompts or process-only `ASSESSMENT_ADMINISTRATOR_PASSWORD`, `ASSESSMENT_DOCTOR_PASSWORD`, `ASSESSMENT_PATIENT_PASSWORD`. Use three distinct `secrets.token_urlsafe(32)` values, store them in a password manager, then provision through prompts. Each must have at least 24 characters/five distinct characters; this length check cannot prove operator-generated randomness. Values never appear in command output or a credential file. Share via a private password-manager invitation or the assessor's secure channel, never README/chat/Render logs.

## Supported free-plan execution mechanism

Use a trusted administrator workstation and temporary IP-restricted **external** PostgreSQL access. Free Render services do not provide shell/one-off jobs; there is no need to bypass that with a public endpoint. Verify current constraints in [Render free plans](https://render.com/docs/free). No GitHub manual workflow is needed, avoiding broad hosted-runner network exposure and another persistent credential store.

1. Review/publish this command through development → PR → main only after authorization. Ensure CI passes and the same revision is checked out on your workstation. Installation uses ordinary `config.settings`, never test settings/fast hashing for hosted fixtures.
2. In Render database settings, temporarily permit only your workstation's public IP `/32`. Do not enable `0.0.0.0/0`. Obtain the external connection hostname privately; the internal Render URL is inaccessible outside Render.
3. Prefer a temporary least-privileged LOGIN role without SUPERUSER, CREATEDB, CREATEROLE or DELETE/DDL. An authorized database owner can grant schema USAGE; SELECT on `auth_user`, `auth_group`, `auth_permission`, `auth_user_groups`, `auth_user_user_permissions`, `auth_group_permissions` and all clinic tables; INSERT/UPDATE on those user/group/membership and clinic fixture tables; and USAGE/SELECT on their sequences. No migrations run through this role. Use a hidden `\password` prompt when provisioning. Database/network permissions must be explicitly authorized; no role was created by this implementation.
4. Use a separate PowerShell process. Keep the local `.env` unchanged. Read the temporary external URL through a hidden prompt and override only that process's DATABASE_URL:

```powershell
# From the inner Django directory; use your virtual environment.
$privateUrl = Read-Host 'Temporary external PostgreSQL URL (include sslmode=require)' -AsSecureString
$env:DATABASE_URL = [System.Net.NetworkCredential]::new('', $privateUrl).Password
$env:DJANGO_DEBUG = 'False'
python manage.py seed_assessment_demo --inspect
```

The URL must include TLS verification appropriate to the provider (at least `sslmode=require`; prefer verify-full with trusted CA configuration). It is temporarily present in process memory, not a tracked file or printed log. Do not start a transcript, dump environment variables or pass secrets on a command line. The existing local signing secret may be used only to initialize this administrative process; do not copy the deployed signing secret. This process does not serve sessions.

5. Read inspection counts and exact database name; verify Render's host/database identity privately and confirm whether records are fictional or legitimate. Inspection reports counts/colliding names only, not patient details. **Stop if ownership/content is uncertain.** Do not infer an empty database from the doctor page. New primary names must not collide; the transaction refuses unmarked, privilege-changed, inactive or differently profiled identities. Existing legitimate records are neither removed nor overwritten.
6. Only after explicit authorization of that inspected target:

```powershell
$env:ASSESSMENT_DEMO_ENABLED = 'True'
python manage.py seed_assessment_demo --confirm-database '<exact-name-reported-by-inspection>'
# Hidden prompts request the three distinct stored reviewer passwords.
Remove-Item Env:ASSESSMENT_DEMO_ENABLED
Remove-Item Env:DATABASE_URL
Remove-Item Env:DJANGO_DEBUG
```

7. Close the terminal, revoke the temporary role's access and remove the temporary IP allowance. Ensure the persistent Render service still has `DEMO_SEED_ENABLED=False` and no `ASSESSMENT_*` password variables. Never add seeding to render-build.sh.

## Repeatability and reset policy

All operations are inside one transaction; an ownership/collision failure rolls back everything. Reruns verify group/email/roles/profiles, preserve existing visit timestamps/statuses/reasons and password hashes, and skip the stable patient/visit markers. Same-group command invocations serialize via a locked ownership row. Doctor and patient row locks plus database constraints protect insertion against simultaneous booking. An externally changed schedule or ambiguous marker aborts for review rather than repairing data silently.

Use the same three credentials for a normal rerun; mismatched primary passwords are refused. `--rotate-passwords` explicitly changes only the three verified primary password hashes, preserving schedule/appointment records; it refuses missing identities. It does not reactivate accounts or recreate deleted fixtures. Partial datasets and disabled identities need manual ownership review. No reset/delete option is provided.

## Verification checklist after authorized seeding

Record results in `LIVE_DEMO_VERIFICATION.md`, with timestamp/revision and no credentials:

- Inspect counts, five additional fixture doctors, weekday periods and future free slots. Existing doctors remain; a nonempty target may legitimately show more than five total doctors.
- Log in at `/accounts/login/` as each primary reviewer and confirm the correct scoped dashboard. Do not claim live accounts exist based on local tests.
- Use designated demo_patient/demo_doctor records only: book a future available slot, confirm persistence/dashboard visibility, reschedule and verify old/new slot occupancy, then cancel with reason and confirm release.
- Attempt duplicate booking, past time and a time within one hour; expect conflict/validation errors. Check that failed requests leave existing visits unchanged.
- Reload from a separate browser session. After an explicitly authorized service restart, verify database counts/visit persistence again. A normal refresh alone does not prove restart persistence.
- Check CSRF, generic errors, logs, HTTPS and absence of credentials. Keep any mutation records clearly labeled as assessment verification.

These live actions were not performed by this implementation. Local tests exercise ownership collisions, safeguards, passwords, stable reruns, rotation and the designated fixture booking/reschedule/cancel flow against an isolated PostgreSQL test database.

## Publish and record verified identities

From Git root, review only this task's changes before explicitly authorized publication (commands below were not executed):

```powershell
git switch development
git add -- clinic-appointment-booking-system/README.md clinic-appointment-booking-system/clinic/management/commands/seed_assessment_demo.py clinic-appointment-booking-system/clinic/test_assessment_demo.py clinic-appointment-booking-system/docs/LIVE_DEMO_TESTING_GUIDE.md clinic-appointment-booking-system/docs/LIVE_DEMO_VERIFICATION.md clinic-appointment-booking-system/docs/DEMO_DATA_CLEANUP_GUIDE.md
git diff --cached
git commit -m "Add controlled assessment demo provisioning"
git push origin development
```

Open a PR into main, require the PostgreSQL test check and merge only with authorization. Confirm Render deploys that revision; deployment must still not seed automatically. Then follow the private inspection/seed procedure. Only after successful hosted logins replace the README's prepared/unverified labels with verified usernames and add the verification timestamp/results. Supply credentials through the agreed secure assessor channel, never Git.
