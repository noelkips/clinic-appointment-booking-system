# REST API reference

## 8. REST API reference

All endpoints require a Django session. Sign in at `/accounts/login/`, retain cookies and supply a valid CSRF token for POST/PATCH. The browsable API shares that session. There is no token/JWT endpoint.

Primary paths start with `/api`; equivalent assessment paths without that prefix also exist. **No trailing slash on API paths.** HTML `/appointments/` and API `/appointments` differ.

Examples illustrate the contract; they are not captured production responses or guaranteed free slots. Obtain IDs/times from your database. Appointment responses share this representation:

```json
{"id":101,"patient":20,"doctor":1,"starts_at":"2026-11-02T09:00:00+03:00","reason":"Consultation","cancellation_reason":"","status":"confirmed","created_at":"2026-10-20T12:00:00+03:00"}
```

### Book

`POST /api/appointments` — patient only. Required `doctor` profile PK and `starts_at` datetime; optional consultation `reason`, maximum 200 characters. Patient/status/cancellation reason/creation time are server controlled.

```http
POST /api/appointments
Content-Type: application/json
X-CSRFToken: <current-session-token>

{"doctor":1,"starts_at":"2026-11-02T09:00:00+03:00","reason":"Consultation"}
```

Success: **201**, the representation above. Invalid doctor/time/hours/notice/reason: **400**. Doctor/patient conflict: **409**. Logged-in non-patient: **403**.

### Doctor availability

`GET /api/doctors/{id}/availability?date=YYYY-MM-DD` — any authenticated role. Required doctor ID and date query; date denotes the Nairobi schedule day.

```http
GET /api/doctors/1/availability?date=2026-11-02
```

Example **200**:

```json
{"date":"2026-11-02","slots":["2026-11-02T09:00:00+03:00","2026-11-02T09:30:00+03:00"]}
```

Missing/malformed date: **400**, e.g. `{"detail":"Provide date as YYYY-MM-DD."}`. Unknown doctor: **404**. No eligible slots/past date/inactive doctor: **200** with empty `slots`. Anonymous public profiles render availability server-side; anonymous API requests are forbidden.

### Cancel

`PATCH /api/appointments/{id}/cancel` — owning patient or administrator. Required `reason` is the cancellation explanation.

```http
PATCH /api/appointments/101/cancel
Content-Type: application/json
X-CSRFToken: <current-session-token>

{"reason":"Unable to attend"}
```

Example **200**:

```json
{"id":101,"patient":20,"doctor":1,"starts_at":"2026-11-02T09:00:00+03:00","reason":"Consultation","cancellation_reason":"Unable to attend","status":"cancelled","created_at":"2026-10-20T12:00:00+03:00"}
```

Missing/blank/non-string/overlong reason or already cancelled/past record: **400**. Reason error example: `{"reason":["A nonblank cancellation reason is required."]}`. Released slots still need to meet schedule/notice rules. Assigned doctor: **403**; unrelated patient's record: **404**.

### Reschedule

`PATCH /api/appointments/{id}/reschedule` — owning patient or administrator. Required `starts_at` must be eligible with the same doctor.

```http
PATCH /api/appointments/101/reschedule
Content-Type: application/json
X-CSRFToken: <current-session-token>

{"starts_at":"2026-11-02T10:00:00+03:00"}
```

Example **200**, for a confirmed appointment:

```json
{"id":101,"patient":20,"doctor":1,"starts_at":"2026-11-02T10:00:00+03:00","reason":"Consultation","cancellation_reason":"","status":"confirmed","created_at":"2026-10-20T12:00:00+03:00"}
```

Invalid time/hours/notice or cancelled/past record: **400**. Occupied new interval: **409**, retaining original time. Assigned doctor: **403**; unknown/inaccessible record: **404**.

### Upcoming patient appointments (bonus)

`GET /api/patients/{id}/appointments` — that patient or administrator. `id` is the **Patient profile PK**, not necessarily the User PK. No body.

```http
GET /api/patients/20/appointments
```

Example **200**:

```json
[{"id":101,"patient":20,"doctor":1,"starts_at":"2026-11-02T09:00:00+03:00","reason":"Consultation","cancellation_reason":"","status":"confirmed","created_at":"2026-10-20T12:00:00+03:00"}]
```

Future confirmed visits only, sorted by `starts_at`, then ID. No matches returns `[]`; administrators also receive `[]` for nonexistent patients. Other patients/doctors receive **403**. HTML interfaces retain authorized complete history.

### Common errors

Anonymous access and missing/invalid CSRF on authenticated unsafe requests return **403** under session authentication; unsupported methods return **405**. Errors use DRF field arrays or service `detail` arrays/strings. Example overlap (**409**): `{"detail":["This doctor or patient already has an appointment at that time."]}`. SQL integrity failures become generic slot conflicts rather than unique messages per constraint.
