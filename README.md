# ctfprofile-ctfd-plugin

A [CTFd](https://ctfd.io) plugin that syncs your CTFd competition data to a [CTFProfile](https://github.com/CTFProfile) instance in real time.

---

## Features

- **Live solve sync** — pushes a minimal payload to CTFProfile every time a flag is captured
- **Full sync** — one-click push of all challenges, users, teams, solves, and standings
- **Admin UI** — configure everything from the CTFd admin panel (`/admin/ctfprofile/`)
- **Test connection** — verify your API key and URL without touching real data
- **Zero extra dependencies** — uses only Python stdlib (`urllib`, `json`) and CTFd's own models

---

## Requirements

| Component | Version |
|-----------|---------|
| CTFd | 3.x |
| Python | 3.9+ |
| CTFProfile | any version with the `/api/events/<slug>/ctfd-sync/` endpoint |

---

## Installation

### Option A — Copy the package

```bash
cp -r ctfprofile_sync /path/to/CTFd/CTFd/plugins/
```

### Option B — Symlink (development)

```bash
ln -s /path/to/ctfprofile-ctfd-plugin/ctfprofile_sync \
      /path/to/CTFd/CTFd/plugins/ctfprofile_sync
```

Restart CTFd. The plugin is auto-discovered because it contains a `load(app)` function in `__init__.py`.

---

## Configuration

1. Open the CTFd admin panel and navigate to **Admin → CTFProfile Sync** (or go to `/admin/ctfprofile/` directly).

2. Fill in the three required fields:

   | Field | Where to find it |
   |-------|-----------------|
   | **CTFProfile Base URL** | Root URL of your CTFProfile instance, e.g. `https://ctfprofile.example.com` |
   | **Event API Key** | CTFProfile → your event → **Integrations** page → copy the `ctfp_evt_…` key |
   | **Event Slug** | The slug in the event URL: `…/events/<slug>/` |

3. Click **Save Settings**, then **Test Connection** to verify.

4. Enable **Sync automatically on each solve** if you want real-time updates, and click **Full Sync Now** to push any existing data.

---

## How it works

```
CTFd solve submission
      │
      ▼
SQLAlchemy after_insert (Solves)
      │
      ▼
build_solve_payload()   ← minimal JSON: 1 solve + associated challenge/user/team
      │
      ▼
POST /api/events/<slug>/ctfd-sync/   ← authenticated with X-CTFProfile-API-Key header
      │
      ▼
CTFProfile upserts challenges, participants, solves
```

For a **Full Sync**, `build_full_payload()` queries every CTFd table and sends the complete state in one request. CTFProfile performs `update_or_create` on all records so it is safe to run repeatedly.

### User matching

CTFProfile tries to match CTFd users in this order:

1. `ctfprofile_public_id` field on the CTFd user object (if your CTFd has it set)
2. CTFd username vs. `ctfd_username` on a linked CTFProfile account
3. CTFd username vs. CTFProfile username (case-insensitive)

---

## Project layout

```
ctfprofile_sync/
├── __init__.py        # CTFd plugin entry-point; registers blueprint + solve listener
├── api.py             # CTFProfileClient — HTTP calls to the sync endpoint
├── config.py          # Read/write settings via CTFd's Configs table
├── routes.py          # Flask blueprint: /admin/ctfprofile/
├── sync.py            # Payload builders: build_full_payload(), build_solve_payload()
└── templates/
    └── ctfprofile_sync/
        └── settings.html   # Admin UI template
```

---

## License

MIT — see [LICENSE](LICENSE).
