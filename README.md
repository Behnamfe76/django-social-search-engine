# Social Search Engine

A search API over LinkedIn-style profile data, plus an ingestion pipeline that
takes the raw export off the request path entirely: uploads are stored and
queued, split into record-aligned byte ranges, and imported by Celery workers
while the client polls for progress.

Django 6.1 · DRF · PostgreSQL 17 · Celery + Redis · Docker

---

## Quick start

The only prerequisite is Docker (Desktop, or Engine with the Compose plugin).
No local Python needed.

```bash
git clone <repo> && cd DjangoProject2
./sse init
```

`./sse init` writes a `.env` with a freshly generated `SECRET_KEY`, builds the
image, starts Postgres, Redis and the app, applies migrations, collects static
files, and waits until the app reports healthy.

| | |
|---|---|
| API | http://localhost:8000/api/v1/ |
| Swagger | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |
| Admin | http://localhost:8000/admin/ |
| Health | http://localhost:8000/api/v1/health/ |

Then create a login:

```bash
./sse createsuperuser
```

## Loading the dataset

Everything goes through the API — there is no offline import command, because
the point of the pipeline is that ingestion is a normal, observable API
operation.

```bash
# 1. get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"your-password"}' | jq -r .access)

# 2. upload — returns 202 immediately, nothing is parsed in the request
curl -X POST http://localhost:8000/api/v1/imports/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@'300 user linkedin.csv'"

# 3. poll for progress
curl http://localhost:8000/api/v1/imports/1/ -H "Authorization: Bearer $TOKEN"

# 4. see which rows were rejected and why
curl http://localhost:8000/api/v1/imports/1/errors/ -H "Authorization: Bearer $TOKEN"
```

Step 3 returns the shape a frontend polls until `is_terminal` is true:

```json
{
  "id": 1, "status": "processing", "progress": 63.69,
  "row_count": 336, "processed_rows": 214,
  "total_chunks": 5, "pending_chunks": 2,
  "created_rows": 181, "updated_rows": 0, "failed_rows": 33,
  "duration_seconds": 6.3, "is_terminal": false
}
```

Imports are idempotent. Uploading the same file twice updates the existing
profiles rather than duplicating them, so re-running is always safe.

## Everyday commands

`./sse` is the single entry point. Anything it does not recognise is passed
through to `manage.py` inside the container.

```bash
./sse up | down | restart      # lifecycle  (down -v also drops the database)
./sse logs                     # follow web + worker output together
./sse ps | doctor              # what is running / is the host set up
./sse migrate                  # ... and any other manage.py command
./sse makemigrations social_api
./sse createsuperuser
./sse shell
./sse test                     # the full suite, inside the container
./sse bash                     # a shell in the container
./sse ctl status               # supervisorctl: `./sse ctl restart worker`
```

### Starting over

`./sse reinit` is the equivalent of Laravel's `migrate:fresh` plus the rest of
the setup. It asks for confirmation first; `--yes` skips the prompt.

```bash
./sse reinit          # wipe everything and set it up again
./sse reinit --yes
```

It stops the worker, purges queued tasks, drops every table, re-runs all
migrations, deletes every uploaded file, recreates the superuser from `.env`,
and restarts both processes onto the new schema.

The order matters. The worker is stopped first so nothing is mid-import while
the tables go, and both processes are restarted afterwards because gunicorn
holds pooled connections (`CONN_MAX_AGE`) whose cached query plans still refer
to the tables that were just dropped.

For the database alone, leaving uploads and the queue untouched:

```bash
./sse migrate:fresh              # or migrate_fresh; both reach the same command
./sse migrate_fresh --skip-migrate   # drop the tables and stop there
```

`migrate_fresh` is a real management command
([`social_api/management/commands/migrate_fresh.py`](social_api/management/commands/migrate_fresh.py)),
so it works outside Docker too. It refuses to run with `DEBUG` off unless you
pass `--force`, and prompts with the database name and host unless you pass
`--noinput`.

For a bare `sse` instead of `./sse`, add `alias sse="$PWD/sse"` to your shell.

---

## Architecture

### Layout

The app is split by **layer**, and each layer again by **domain**, one class per
file. There is no `models.py` or `admin.py` monolith.

```
social_api/
  models/       {app, attribute, companies, employment, geography, occupation, social}/
  admin/        mirrors the model domains
  api/v1/       views/, serializers/, filters/, urls.py, pagination.py
  selectors/    read-side query building
  services/     write-side logic (slug, imports/)
  tasks/        thin Celery wrappers
  middleware/   route-level JWT gate
```

Each package re-exports its classes, so imports stay flat:
`from social_api.models import Personality`.

### Data model

`Personality` is the hub: a person, with foreign keys to `Industry` and
`ImportBatch`, and five many-to-many relations through explicit join models
(`Location`, `Skill`, `Interest`, `Language`, `Certification`). Around it sit
`Employment` (person ↔ company ↔ a four-level occupation taxonomy), `Company`,
`Location`, and social profiles for both people and companies.

Identity is `Personality.external_id`, taken from `linkedin_id` and falling back
to `linkedin_username`. That is the key the importer upserts on, and it is what
makes re-importing a no-op instead of a duplicate.

Deletes are soft (`deleted_at`); the read selector filters them out.

### Authentication

Two layers. DRF's `IsAuthenticated` is the global default, and
`JWTRouteAuthMiddleware` additionally gates whole path prefixes before routing,
so a route is protected regardless of what serves it. `AUTH_PROTECTED_PREFIXES`
and `AUTH_EXEMPT_PREFIXES` control it, and exempt wins.

Because the middleware runs before the view, `force_authenticate` does not work
in tests — use `social_api.tests.support.authenticate`, which attaches a real
bearer token.

### The import pipeline

```
POST /api/v1/imports/     store the upload, return 202. The request never
                          opens the file.
        │
        ▼
plan_batch                stream the file once in 1 MB blocks, tracking CSV
                          quote state, and emit record-aligned (start, end)
                          byte ranges as ImportChunk rows — one task each.
        │                 Memory stays flat regardless of file size.
        ▼
process_chunk × N         seek(start); read(n); parse with the header
                          prepended; upsert inside one transaction.
        │
        ▼
finalise_batch            the chunk whose atomic decrement lands on zero
                          claims finalisation, flips the status and deletes
                          the upload.
```

Four decisions worth naming:

**Chunks are byte offsets, not payloads.** A single profile in this dataset
reaches 53 KB, so a few hundred inline rows would put multi-megabyte messages on
the broker. `seek(start); read(n)` is also exactly an S3 ranged GET, which is
what keeps the storage backend swappable — local disk here, `STORAGES` change in
production.

**The splitter is quote-aware.** RFC 4180 lets a quoted field contain a literal
newline, and this dataset uses it: the sample export is 357 physical lines but
337 records. The scanner mirrors CPython's `csv` reader state machine byte for
byte, including the rule that a quote only opens a quoted field at the *start*
of a field. Treating every quote as significant makes the planner merge records
the reader later splits, and the advertised row count stops matching reality.

**Completion is a database counter, not a Celery chord.** Each chunk atomically
decrements `pending_chunks`; a conditional UPDATE that can only be won once
claims finalisation. No result backend, and it survives worker restarts.

**Every stage claims its row first.** A conditional UPDATE is the first thing
`plan_batch`, `process_chunk` and `finalise_batch` do, so a redelivered message
finds nothing to claim and returns. Rows that lose a deadlock — routine when
several chunks upsert the same companies — retry inside their own savepoint.

The web process and the worker share one container under supervisor, on purpose:
the importer writes uploads to `MEDIA_ROOT` and the worker reads byte ranges back
out, so they need a shared filesystem. Splitting them is the production move, and
it is exactly the point at which storage has to become S3.

### Why not ElasticSearch

The brief allows either. At this scale — a few hundred profiles, ~1400 distinct
skills — a second stateful service would cost more in setup and operational
surface than it buys in query quality, and "simple and runnable" was the stated
bar. Postgres does the work. The search is deliberately confined to
`social_api/api/v1/filters/` and the selectors, so moving it later is a change in
one layer rather than a rewrite.

---

## Search and filters

`GET /api/v1/personalities/`

| Parameter | Effect |
|---|---|
| `search` | case-insensitive match across `full_name`, `first_name`, `last_name` |
| `full_name` | `icontains` on the full name |
| `gender` | exact: `male`, `female`, `other`, `unknown` |
| `industry_id` | exact FK match |
| `import_batch_id` | exact FK match — scopes results to one upload |
| `birth_year_min` / `birth_year_max` | inclusive range |
| `ordering` | `id`, `full_name`, `last_name`, `created_at`, `updated_at`; prefix `-` to reverse |
| `page` / `page_size` | 20 per page by default, 100 maximum |

```bash
curl "http://localhost:8000/api/v1/personalities/?search=maria&gender=female&ordering=-full_name" \
  -H "Authorization: Bearer $TOKEN"
```

`search` is DRF's `SearchFilter` over the indexed name columns; the rest are
django-filter definitions in
[`api/v1/filters/personality.py`](social_api/api/v1/filters/personality.py).
Foreign keys are exposed as `<name>_id` and are writable — DRF silently makes an
`_id` attname read-only unless it is declared explicitly, which is what
`fk_id_field()` in the serializers exists to fix.

---

## API reference

| Method | Path | Auth | |
|---|---|---|---|
| `GET` | `/api/v1/health/` | – | liveness |
| `POST` | `/api/v1/auth/register/` | – | create an account |
| `POST` | `/api/v1/auth/login/` | – | email + password → token pair |
| `POST` | `/api/v1/auth/refresh/` | – | rotate the access token |
| `POST` | `/api/v1/auth/verify/` | – | check a token |
| `GET` | `/api/v1/auth/me/` | ✓ | the token's user |
| `GET` `POST` | `/api/v1/personalities/` | ✓ | search / create |
| `GET` `PUT` `PATCH` `DELETE` | `/api/v1/personalities/{id}/` | ✓ | delete is soft |
| `POST` | `/api/v1/imports/` | ✓ | upload a dataset → `202` |
| `GET` | `/api/v1/imports/` | ✓ | recent batches |
| `GET` | `/api/v1/imports/{id}/` | ✓ | progress, for polling |
| `GET` | `/api/v1/imports/{id}/errors/` | ✓ | rejected rows with reasons |

Full schema at `/api/schema/`, browsable at `/api/docs/`.

---

## Configuration

`./sse init` creates `.env` from `.env.example`; every value has a working
default. `./sse doctor` reports keys that `.env.example` has gained since your
`.env` was written.

| Variable | Default | |
|---|---|---|
| `DJANGO_SECRET_KEY` | generated | also signs JWTs; must be ≥ 32 bytes |
| `DJANGO_DEBUG` | `True` | `migrate_fresh` refuses to run when this is off |
| `DJANGO_SUPERUSER_EMAIL` / `_NAME` / `_PASSWORD` | – | set the password and `./sse init` and `./sse reinit` create the account for you |
| `APP_PORT` | `8000` | host port |
| `APP_UID` / `APP_GID` | `1000` | Linux only: set to `id -u` / `id -g` |
| `GUNICORN_WORKERS` | `3` | |
| `CELERY_CONCURRENCY` | `4` | chunks processed in parallel |
| `IMPORT_CHUNK_TARGET_BYTES` | `1048576` | chunk size: parallelism vs task overhead |
| `IMPORT_CHUNK_MAX_ROWS` | `500` | row ceiling per chunk |
| `IMPORT_SCAN_BLOCK_BYTES` | `1048576` | bounds the planner's memory |
| `IMPORT_MAX_UPLOAD_BYTES` | `2 GiB` | rejected with `400` above this |
| `IMPORT_DELETE_FILE_WHEN_DONE` | `True` | set `False` to keep uploads for debugging |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | `15` / `7` | |

`POSTGRES_HOST` and `CELERY_BROKER_URL` stay on `localhost` in `.env`;
docker-compose overrides them with the service names inside the network, so the
same file works from the host too.

## Tests

```bash
./sse test                          # in the container
./sse test social_api.tests.test_import_chunking
```

149 tests. The pipeline ones are worth a look: `test_import_chunking` checks the
splitter against `csv.reader` on pathological quoting, and `test_import_pipeline`
drives the real Celery tasks inline, including redelivery, deadlock retry and a
chunk whose retries run out.

## Running without Docker

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
docker compose up -d postgres redis          # or your own instances
cp .env.example .env                          # then set DJANGO_SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver          # terminal 1
.venv/bin/celery -A social_search_engine worker -l info   # terminal 2
```

The worker is a separate process. Without it, uploads are accepted and then sit
at `pending` forever.

---

## Notes on the dataset

The provided export is dirty, and the importer is built around that rather than
assuming it away.

- **53 of 336 rows have the wrong column count** (widths from 6 to 133); one
  even contains a stray Windows path. They are recorded individually in
  `/imports/{id}/errors/` and the batch finishes as `partial`. Losing 283 good
  profiles to fix 53 bad ones would be the wrong trade.
- **87 further rows are shifted while still having 77 columns** — a Facebook
  username sitting in `middle_name`, an industry in `facebook_username`. A
  column-count check cannot catch a shift that preserves the count, so those
  import as-is and show up as odd middle names.
- **`linkedin_id` is not clean**: 14 rows are blank and around 35 are repeated.
  Blank identities insert unconditionally; repeats collapse onto one profile.

## Not done yet

- No filter on skill or job title. The tables are populated and indexed, but the
  filterset does not expose them yet — this is the most valuable next addition.
- `education` is the one nested column the importer drops; there is no
  `Education`/`School` model.
- No CORS headers, so a browser frontend on another origin cannot call the API
  until `django-cors-headers` is added.
