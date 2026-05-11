# Backend – Videoflix Streaming Platform

This Videoflix backend was developed as part of a learning project to strengthen
backend development skills. It powers a Netflix-style video streaming platform
and is designed to work seamlessly with an existing frontend. The application
provides a RESTful API with JWT-based authentication via HTTP-only cookies, an
asynchronous video processing pipeline (FFmpeg → HLS) backed by Redis Queue,
and adaptive bitrate streaming in 480p, 720p and 1080p.

![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-6.0-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.17-red?logo=django&logoColor=white)

The corresponding frontend repository can be found here:  [Videoflix Frontend](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix)

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Getting Started (Docker)](#-getting-started-docker)
- [Local Development (without Docker)](#-local-development-without-docker)
- [Environment Variables](#-environment-variables)
- [Project Structure](#-project-structure)
- [Authentication](#-authentication)
- [API Endpoints](#-api-endpoints)
  - [Auth](#auth)
  - [Videos & HLS Streaming](#videos--hls-streaming)
- [Video Processing Pipeline](#-video-processing-pipeline)
- [Background Jobs (RQ)](#-background-jobs-rq)
- [E-Mails](#-e-mails)
- [CORS Configuration](#-cors-configuration)
- [Running Tests](#-running-tests)
- [Troubleshooting](#-troubleshooting)
- [Notes](#-notes)
- [Helpful Documentation](#-helpful-documentation)

---

## ✨ Features

- JWT authentication with HTTP-only cookies (access & refresh tokens)
- E-mail-based account activation flow
- Password reset via signed e-mail link
- Token refresh and refresh-token blacklisting on logout
- Video upload via the Django Admin
- Asynchronous transcoding to HLS in three resolutions (480p / 720p / 1080p)
- Automatic thumbnail generation with FFmpeg
- Adaptive HLS streaming (manifest + segment endpoints)
- Automatic cleanup of source files, thumbnails and HLS renditions on delete
- Redis-backed cache and RQ task queue
- Production-ready Docker setup (PostgreSQL, Redis, Gunicorn, Whitenoise)

---

## 🛠 Tech Stack

| Component | Version |
| --- | --- |
| Python | 3.12 |
| Django | 6.0.4 |
| Django REST Framework | 3.17.1 |
| djangorestframework-simplejwt | 5.5.1 |
| django-rq / rq | 4.1.0 / 2.8.0 |
| django-redis | 6.0.0 |
| django-cors-headers | 4.9.0 |
| psycopg2-binary | 2.9.12 |
| gunicorn | 25.3.0 |
| whitenoise | 6.12.0 |
| Database | PostgreSQL 17 |
| Cache & Queue | Redis 8 |
| Media processing | FFmpeg |

---

## 📦 Prerequisites

For the recommended Docker setup:

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

For running locally without Docker:

- Python 3.12 or higher
- PostgreSQL 14+
- Redis 7+
- FFmpeg (must be available in `$PATH`)
- `pip` and `venv` (included with Python)

---

## 🚀 Getting Started (Docker)

The fastest way to get a fully working stack (backend + PostgreSQL + Redis +
RQ worker) is via Docker Compose.

### 1. Clone the repository

```bash
git clone https://github.com/Marcel-Lukas/Videoflix-Backend.git
cd Videoflix-Backend
```

### 2. Create the `.env` file

Copy the provided template and fill in your own values:

```bash
cp .env.template .env
```

See [Environment Variables](#-environment-variables) for what each value means.

### 3. Build and start the stack

```bash
docker compose up --build
```

The entrypoint script (`backend.entrypoint.sh`) will automatically:

1. Wait for PostgreSQL to become available
2. Collect static files
3. Run `makemigrations` and `migrate`
4. Create a Django superuser (if not yet present) from the `DJANGO_SUPERUSER_*` env vars
5. Start an RQ worker for the `default` queue
6. Launch the Gunicorn application server

The API is then available at: `http://127.0.0.1:8000/`
Django Admin: `http://127.0.0.1:8000/admin/`
RQ Dashboard: `http://127.0.0.1:8000/django-rq/`

### 4. Stop the stack

```bash
docker compose down
```

To also remove volumes (database, redis, media, static):

```bash
docker compose down -v
```

---

## 💻 Local Development (without Docker)

If you prefer running the project directly on your machine:

### 1. Clone the repository

```bash
git clone https://github.com/Marcel-Lukas/Videoflix-Backend.git
cd Videoflix-Backend
```

### 2. Create and activate a virtual environment

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.template` to `.env` and adjust the values so that `DB_HOST` and
`REDIS_HOST` point to your local services (e.g. `localhost`).

### 5. Apply migrations and create a superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start a Redis Queue worker (separate terminal)

```bash
python manage.py rqworker default
```

### 7. Start the development server

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/`.

---

## 🔧 Environment Variables

All environment variables are loaded from a `.env` file at the project root
(via `python-dotenv`). A template is provided in `.env.template`.

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins |
| `DJANGO_SUPERUSER_USERNAME` | Auto-created superuser username (Docker) |
| `DJANGO_SUPERUSER_EMAIL` | Auto-created superuser email (Docker) |
| `DJANGO_SUPERUSER_PASSWORD` | Auto-created superuser password (Docker) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL credentials |
| `DB_HOST`, `DB_PORT` | PostgreSQL connection info |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Redis connection for RQ |
| `REDIS_LOCATION` | Full Redis URL used by the Django cache |
| `EMAIL_HOST`, `EMAIL_PORT` | SMTP server configuration |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | Transport security flags |
| `DEFAULT_FROM_EMAIL` | Sender address used in outgoing mails |
| `FRONTEND_URL` | Public frontend URL used to build activation / password-reset links |

---

## 📁 Project Structure

```
Videoflix-Backend/
│
├── core/                          # Django project configuration
│   ├── settings.py                # Global settings (JWT, DB, Redis, RQ, e-mail)
│   ├── test_settings.py           # Overrides used during the test suite
│   ├── urls.py                    # Root URL dispatcher
│   ├── wsgi.py / asgi.py
│
├── auth_app/                      # Authentication & user management
│   ├── tasks.py                   # RQ jobs for activation & password reset mails
│   ├── templates/                 # HTML templates for transactional e-mails
│   ├── api/
│   │   ├── views.py               # Register, Login, Logout, Refresh, Activate, Password reset
│   │   ├── serializers.py
│   │   ├── authentication.py      # CookieJWTAuthentication
│   │   └── urls.py
│   ├── migrations/
│   └── tests/
│       ├── test_register.py
│       ├── test_login.py
│       ├── test_logout.py
│       ├── test_token_refresh.py
│       ├── test_activate.py
│       └── test_password_reset.py
│
├── video_app/                     # Videos, HLS streaming & background processing
│   ├── models.py                  # Video model (status, category, files)
│   ├── signals.py                 # Enqueue conversion on save, cleanup on delete
│   ├── tasks.py                   # FFmpeg-based thumbnail + HLS conversion
│   ├── api/
│   │   ├── views.py               # VideoListView, HLS manifest & segment views
│   │   ├── serializers.py
│   │   └── urls.py
│   ├── migrations/
│   └── tests/
│       ├── test_models.py
│       ├── test_serializers.py
│       ├── test_signals.py
│       ├── test_tasks.py
│       ├── test_video_list.py
│       └── test_hls.py
│
├── media/                         # Uploaded videos, thumbnails, HLS renditions
├── static/                        # Collected static files
│
├── backend.Dockerfile             # Production image (Python 3.12 + ffmpeg)
├── backend.entrypoint.sh          # Container entrypoint (migrate, worker, gunicorn)
├── docker-compose.yml             # Web + PostgreSQL + Redis stack
├── manage.py
├── requirements.txt
└── .env.template
```

---

## 🔐 Authentication

The API uses **JSON Web Tokens (JWT)** issued by
`djangorestframework-simplejwt`, but the tokens are not handed back to the
client in the response body — they are stored in **HTTP-only cookies** instead:

| Cookie | Lifetime | Purpose |
| --- | --- | --- |
| `access_token` | 120 minutes | Sent automatically on every request |
| `refresh_token` | 1 days | Used by `/api/token/refresh/` to obtain a new access token |

Cookies are flagged `HttpOnly`, `Secure`, `SameSite=None` so they can be used
from the frontend across origins. On logout, the refresh token is added to the
SimpleJWT **blacklist** and both cookies are cleared.

The custom `CookieJWTAuthentication` class (in
`auth_app/api/authentication.py`) reads the access token from the cookie and
falls back to the standard `Authorization: Bearer <token>` header when no
cookie is present.

---

## 🔌 API Endpoints

Base prefix: `/api/`

### Auth

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| POST | `register/` | No | Register a new user; sends an activation e-mail |
| GET | `activate/<uidb64>/<token>/` | No | Activate the user account from the e-mail link |
| POST | `login/` | No | Authenticate and set access + refresh cookies |
| POST | `logout/` | Yes | Blacklist the refresh token and clear cookies |
| POST | `token/refresh/` | Cookie | Issue a new access token using the refresh cookie |
| POST | `password_reset/` | No | Send a password-reset e-mail (silent if e-mail unknown) |
| POST | `password_confirm/<uidb64>/<token>/` | No | Set a new password using the reset link |

**Register request body:**

```json
{
  "email": "user@example.com",
  "password": "yourPassword123",
  "confirmed_password": "yourPassword123"
}
```

**Login request body:**

```json
{
  "email": "user@example.com",
  "password": "yourPassword123"
}
```

**Password reset confirm body:**

```json
{
  "new_password": "newSecret123",
  "confirm_password": "newSecret123"
}
```

### Videos & HLS Streaming

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| GET | `video/` | Yes | List all available videos |
| GET | `video/<movie_id>/<resolution>/index.m3u8` | Yes | HLS manifest for a video at the given resolution |
| GET | `video/<movie_id>/<resolution>/<segment>/` | Yes | Single HLS segment (`.ts`) |

Allowed resolutions: `480p`, `720p`, `1080p`.

Example manifest URL:

```
GET /api/video/1/720p/index.m3u8
```

The `Video` model exposes the following fields via the list endpoint:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Primary key |
| `created_at` | datetime | Auto-set on creation |
| `title` | string | Display title |
| `description` | text | Long description |
| `thumbnail_url` | URL | Absolute URL to the generated thumbnail |
| `category` | string | One of: `action`, `adventure`, `animation`, `comedy`, `crime`, `documentary`, `drama`, `family`, `fantasy`, `kids`, `horror`, `music`, `mystery`, `romance`, `sci-fi`, `thriller` |

Videos are uploaded by staff users via the Django Admin
(`/admin/video_app/video/`).

---

## 🎬 Video Processing Pipeline

When a new `Video` is saved:

1. A `post_save` signal sets its `conversion_status` to `processing` and
   enqueues an RQ job (`video_app.tasks.convert_and_save`).
2. The worker uses **FFmpeg** to extract a thumbnail at ~20s into the video.
3. Three HLS renditions are generated under
   `media/hls/<video_id>/<resolution>p/index.m3u8` for 480p, 720p and 1080p.
4. On success the status is updated to `ready`, on failure to `failed`.

When a `Video` is deleted:

- The source file, thumbnail and the entire HLS directory tree are removed
  from `MEDIA_ROOT` via the `post_delete` signal.

The HLS endpoints are guarded against path traversal: requested paths are
resolved against `MEDIA_ROOT/hls` and rejected if they escape that directory.

---

## ⚙️ Background Jobs (RQ)

Background work is dispatched via [django-rq](https://github.com/rq/django-rq)
using Redis as the broker. The default queue is named `default`.

| Job | Location | Purpose |
| --- | --- | --- |
| `convert_and_save` | `video_app/tasks.py` | Generate thumbnail + HLS renditions |
| `job_send_activation_mail` | `auth_app/tasks.py` | Send the account activation e-mail |
| `job_send_reset_password_mail` | `auth_app/tasks.py` | Send the password reset e-mail |

The Docker entrypoint automatically starts an RQ worker in the same
container. The RQ dashboard is exposed at `/django-rq/` (staff only).

To run a worker manually:

```bash
python manage.py rqworker default
```

---

## 📧 E-Mails

Transactional e-mails are rendered from the HTML templates in
`auth_app/templates/`:

- `activation_mail.html` — sent on registration
- `reset_password.html` — sent on password-reset request

Both links use `FRONTEND_URL` as the base, so make sure to point it at the
correct frontend deployment (e.g. `http://localhost:5500` during development).

SMTP credentials are configured via the `EMAIL_*` environment variables.

---

## 🌐 CORS Configuration

CORS is enabled with credentials so that the frontend can send the JWT
cookies cross-origin. The following origins are whitelisted by default in
`core/settings.py`:

```python
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:4200",
    "http://localhost:4200",
]
```

`CSRF_TRUSTED_ORIGINS` is configurable via the `CSRF_TRUSTED_ORIGINS`
environment variable. To allow additional frontend origins in production,
extend both lists.

---

## 🐛 Running Tests

Run the full test suite using the dedicated test settings (SQLite, in-memory
cache, eager RQ jobs):

```bash
python manage.py test --settings=core.test_settings
```

Or inside the running Docker container:

```bash
docker compose exec web python manage.py test --settings=core.test_settings
```

Tests are organized per application under `<app>/tests/`:

```
auth_app/tests/      — Registration, login, logout, refresh, activation, password reset
video_app/tests/     — Models, serializers, signals, RQ tasks, video list, HLS
```

Run a single application or test file:

```bash
python manage.py test auth_app.tests.test_login --settings=core.test_settings -v 2
```

`-v 0` = very little output · `-v 1` = standard (default) ·
`-v 2` = detailed · `-v 3` = very detailed (near debug)

---

## 🩺 Troubleshooting

### `pg_isready` keeps looping in the container

PostgreSQL credentials in `.env` do not match the values the `db` service
expects, or the database container is not healthy. Check the logs:

```bash
docker compose logs db
```

### Videos stay in `processing` state

The RQ worker is not running or FFmpeg is missing. Inspect the queue at
`/django-rq/` and the worker logs:

```bash
docker compose logs web | grep -i rq
```

Make sure FFmpeg is installed (it is in the Docker image; for local dev
install it via your package manager, e.g. `apt install ffmpeg` or
`brew install ffmpeg`).

### Browser blocks the auth cookie

The cookies are flagged `Secure` and `SameSite=None`, so the frontend must
be served over HTTPS (or `localhost`, which browsers exempt) and the
backend origin must be whitelisted in `CORS_ALLOWED_ORIGINS`.

### `401 Unauthorized` on every request despite successful login

The access token cookie is not being sent. Common causes:

- The frontend origin is not in `CORS_ALLOWED_ORIGINS` → add it in `core/settings.py` or via `CORS_TRUSTED_ORIGINS`.
- The request is not made with `credentials: 'include'` (Fetch API) or `withCredentials: true` (XMLHttpRequest / Axios).
- The frontend is served over HTTP while the cookie is flagged `Secure` → use HTTPS or `localhost` for local development.

### `403 Forbidden` on POST / mutating requests

Django's CSRF middleware is rejecting the request. Make sure the frontend origin is listed in `CSRF_TRUSTED_ORIGINS`:

```bash
# .env
CSRF_TRUSTED_ORIGINS=https://your-frontend.example.com
```

### Activation or password-reset e-mail is not delivered

1. Check that the `EMAIL_*` variables in `.env` are correct (host, port, credentials).
2. Look in the spam folder of the recipient mailbox.
3. For local development you can switch to the console backend to see e-mails in the terminal without a real SMTP server:

```python
# core/settings.py (dev override)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

### `OperationalError: could not connect to server` (local dev)

PostgreSQL is not running or the connection details in `.env` are wrong. Start the database and verify the values:

```bash
# Example for a local PostgreSQL installation
sudo service postgresql start   # Linux
brew services start postgresql  # macOS
```

Then confirm that `DB_HOST=localhost` (not `db`, which is the Docker service name) is set in `.env`.

---

## 📝 Notes

- The default database is PostgreSQL via Docker. For pure local development
  you can either run PostgreSQL natively or override `DB_*` in `.env`.
- The provided `.env.template` contains development-only defaults. Before
  deploying to production, generate a fresh `SECRET_KEY`, set
  `DEBUG=False`, configure `ALLOWED_HOSTS` and use a real SMTP provider.
- All media (uploaded videos, thumbnails, HLS renditions) lives under
  `media/`. In Docker this is persisted in the `videoflix_media` volume.

---

## 🔗 Helpful Documentation

- [Django Documentation](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [django-rq](https://github.com/rq/django-rq) · [RQ](https://python-rq.org/)
- [django-redis](https://github.com/jazzband/django-redis)
- [Django CORS Headers](https://github.com/adamchainz/django-cors-headers)
- [FFmpeg](https://ffmpeg.org/documentation.html)
- [HLS (HTTP Live Streaming)](https://developer.apple.com/streaming/)

---

## 📧 Contact & Support

This is a lightweight backend built with Django and should mainly be seen as
a learning project. If you find any bugs or have ideas for improvements,
please open an issue in the repository.

---

[⬆️ Scroll up](#backend--videoflix-streaming-platform)
