# Demonstration cleanup and transition plan

**Planning only: no cleanup, deletion, password reset or database reset has been performed.** Obtain separate authorization and take a verified backup before each destructive step. Do not reuse local `seed_demo` cleanup assumptions for hosted assessment fixtures.

## Disable access immediately

Use a trusted, authorized database/management connection to inspect members of `__savannah_assessment_demo_v1__`. Compare usernames, `@assessment.example.test` ownership emails, profiles and privileges with `seed_assessment_demo.roster()`. After review, set `is_active=False` for exactly the owned identities. Session authentication rejects inactive users; verify in fresh and existing sessions. Disabling assessment doctors also prevents new bookings with them. Do not modify unrelated users or the older `__savannah_local_demo__` group by name similarity.

Disable process seeding by removing `ASSESSMENT_DEMO_ENABLED` and credential variables, revoke the temporary seed role and remove temporary database IP access. Persistent Render configuration should never enable the assessment gate. No manual workflow/HTTP seed endpoint exists to remove.

## Rotate credentials

On a verified assessment target, supply three new distinct random passwords privately and run `seed_assessment_demo --rotate-passwords --confirm-database <exact-name>` with the process gate enabled. This affects the three existing active reviewer accounts only and does not reseed visits. Missing/disabled/privilege-changed accounts abort; investigate rather than silently recreating them. Store new credentials securely and revoke old sharing. Password changes invalidate existing Django signed sessions. No automatic password reset occurs on ordinary reruns.

## Remove only reviewed demo data

1. Back up the target and test restoration to a separate database. Review all 27 owned identities and all dependencies.
2. Build an explicit candidate list of appointment IDs whose patient AND doctor are owned by the assessment group and whose reason matches `Assessment demo v1 visit NNN`. Export/review it; do not rely on the text prefix alone.
3. Review reviewer-created bookings separately: they have no seed marker. Real/ambiguous appointments involving a demo identity must be preserved or deliberately reassigned under an approved data policy, not deleted by a broad queryset.
4. Only after approval delete the explicitly reviewed appointment IDs. Associated events cascade. Preserve unrelated events/appointments; this action is irreversible without recovery.
5. Review each owned doctor's availability and each profile/user. Appointment doctor/patient foreign keys use PROTECT, so remaining appointments block deletion. Stop and investigate those references; do not disable constraints or cascade around them.
6. After all dependencies are reviewed, remove only approved owned working periods, profiles, identities and the now-unused ownership group. Verify legitimate row counts/IDs remain unchanged.

No blanket delete command is provided because exact production contents are unknown. Disabling accounts and retaining history is usually safer than deletion. Re-running seeding after deleted rows is not a safe reset policy for a shared database.

## Fresh database, only with explicit authorization

Provision a distinct database, migrate, verify extension/constraints and explicitly decide whether fictional fixtures belong there. Preserve the old database/backup until recovery and data-retention requirements are satisfied. Never drop/reset the current database as a way to refresh a demonstration. Update the service connection only as an authorized deployment with recovery steps.

## Before real-world use

Remove reviewer access; verify there is no real patient data visible through shared staff credentials. Review application-wide staff access, least-privileged production roles, auditing, login abuse controls, password recovery, backups, privacy/retention, domain security and operational availability. The assessment environment is not a production clinical system. Free database expiry/backup limits require a deliberate hosting plan. Clear temporary local secrets/clipboard and verify no credentials appear in Git/logs. Never preserve public demo superusers in a real environment.
