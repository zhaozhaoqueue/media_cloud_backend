# backend_api

FastAPI backend for multiple frontends.

## PostgreSQL (Docker)

Run a local PostgreSQL container:

```bash
docker run --name media-cloud-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=media_cloud \
  -p 127.0.0.1:5432:5432 \
  -v media-cloud-pgdata:/var/lib/postgresql/data \
  -d postgres:15
```

Useful follow-up commands:

```bash
docker start media-cloud-postgres
docker stop media-cloud-postgres
docker logs -f media-cloud-postgres
```

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host $APP_HOST --port $APP_PORT
```

Auth: send `Authorization: Bearer <token>` header to protected endpoints.

Health check: `GET /api/v1/health`

## Docker Compose

Build and start API service:

```bash
docker compose up -d --build api
```

Start API + local PostgreSQL:

```bash
docker compose --profile with-db up -d --build
```

View logs:

```bash
docker compose logs -f api
```

## Config

`.env` is loaded automatically by the app.

You can bootstrap local config from:

```bash
cp .env.example .env
```

- `APP_ENV` / `LOG_LEVEL`
- `APP_HOST` / `APP_PORT`
- `APP_WORKERS` / `GUNICORN_TIMEOUT` / `GUNICORN_KEEPALIVE`
- `FORWARDED_ALLOW_IPS`
- `JWT_SECRET` / `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES`
- `DATABASE_URL`
- `STORAGE_BASE_URL` / `STORAGE_LOCAL_ROOT`
- `READ_URL_TTL_SECONDS` / `READ_URL_SIGNING_SECRET`
- `UPLOAD_TOKEN_TTL_SECONDS`
- `THUMB_MAX_SIZE`
- `CORS_ORIGINS` / `CORS_ALLOW_CREDENTIALS` / `CORS_ALLOW_METHODS` / `CORS_ALLOW_HEADERS`

`FORWARDED_ALLOW_IPS` controls whether the app trusts `X-Forwarded-*` headers from proxy.

- `*`: trust all upstreams. Use only when app is not publicly exposed directly and all traffic comes through trusted reverse proxy.
- Recommended production: set to your trusted proxy source IP(s), e.g. `127.0.0.1` or Docker bridge gateway.

For HTTPS URL generation behind Nginx, set:

```env
STORAGE_BASE_URL=https://your-api-domain.com
```

## Local Storage (Presigned PUT style)

- Upload token endpoint: `POST /api/v1/photos/upload-token`
- Upload URL returned: `PUT /api/v1/uploads/{fileId}?token=...`
- Raw download URL: `GET /api/v1/files/{fileId}/raw`
- Thumbnail URL: `GET /api/v1/files/{fileId}/thumb`

Batch create photos: `POST /api/v1/photos/batch`
