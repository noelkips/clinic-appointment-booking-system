## Investigation update: 21 October 2026 (Africa/Nairobi)

No production seeding, login attempt, network change or authenticated database inspection was performed. Live doctors/patients/appointments and slots remain UNKNOWN. The owner supplied `https://savannah-clinic-diul.onrender.com/`; the earlier report below used `duil` and does not verify the current URL. The current web fetch failed.

`910b248` contains the hosted seeder on development; local main/cached origin/main remain at `c5910f1`. Remote `git ls-remote` failed due to unavailable proxy/network; current remote merge/deployed SHA are unverified. Local .env points to loopback, not Render. Blueprint external access is disabled (`ipAllowList: []`); actual Dashboard allowlist is unverified. No credentials were printed. Follow Render guide section 14 after owner authorization, then replace UNKNOWN counts with actual verification JSON and live browser login results.

﻿# Live demo verification status

Date: 20 October 2026, Africa/Nairobi. Working branch: development. No hosted database connection or credentials were supplied to the agent; no live seeding/mutations/restart were performed. Do not confuse the local test database with Render.

| Check | Status | Evidence / limit |
|---|---|---|
| Owner-supplied live URL | PASS | https://savannah-clinic-duil.onrender.com/ returned HTTP 200 via read-only HTTPS request |
| Live `/health/` | PASS | HTTP 200; connectivity check only, not a database-content inspection |
| Live `/doctors/` | PASS for reachability | HTTP 200; zero distinct numeric doctor-profile links found; this is not proof of an empty database |
| Live `/accounts/login/` retrieval | BLOCKED | Read-only request timed out; no credential submitted |
| Render database inventory / intended username collisions | NOT TESTED | Requires operator's authorized private connection and `--inspect` |
| Hosted five doctors, schedules and available slots | NOT TESTED | Hosted seed has not run |
| Hosted administrator/doctor/patient login | NOT TESTED | Three accounts prepared in code, not claimed to exist remotely |
| Hosted booking/cancellation/rescheduling/conflict/notice tests | NOT TESTED | Await authorized seeding and designated-record testing |
| Hosted restart persistence | NOT TESTED | No restart authorized or performed |
| Local database inventory | PASS, local only | Read-only: 28 users, 5 doctors, 21 patients, 49 schedules, 100 appointments, 115 events; zero proposed reviewer-name collisions |
| New safety regressions | PASS | Tests cover gated target/flag, collision rollback, distinct credentials, repeatability, explicit rotation and no missing-account recreation; isolated PostgreSQL |
| Full automated suite | PASS | 100 PostgreSQL tests in 36.647s, OK, no skips; includes eight new assessment tests, production secret regressions and concurrency |

Local `seed_assessment_demo --inspect` was read-only. No persistent local data was seeded/reset/rotated. All mutation tests used Django's separate test database. Password values were neither logged nor stored in documentation. Evidence: ignored `.local/assessment-full-tests.txt`, `.local/live-assessment-public.json` and local test command output. The browser web tool could not retrieve the live URL; direct authorized HTTPS requests produced the actual results above. No real browser mutation coverage is claimed.

Remaining operator steps: publish reviewed changes through development → PR → main; inspect the actual external Render database privately with narrow network permissions; explicitly authorize that target; provide three random passwords through hidden prompts; seed once; disable temporary access and complete the live checklist in [testing guide](LIVE_DEMO_TESTING_GUIDE.md). Update README account status only after successful live login and role checks. Keep CI/build scripts free of automatic seeding.
