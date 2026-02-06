# backend_api

FastAPI backend for multiple frontends.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host $APP_HOST --port $APP_PORT
```

Dev auth: send `X-User-Id: <uuid>` header to protected endpoints.

Health check: `GET /v1/health`

## Config

`.env` is loaded automatically by the app.

- `APP_ENV` / `LOG_LEVEL`
- `APP_HOST` / `APP_PORT`
- `DATABASE_URL`
- `STORAGE_BASE_URL` / `STORAGE_LOCAL_ROOT`
- `UPLOAD_TOKEN_TTL_SECONDS`
- `THUMB_MAX_SIZE`
- `CORS_ORIGINS` / `CORS_ALLOW_CREDENTIALS` / `CORS_ALLOW_METHODS` / `CORS_ALLOW_HEADERS`

## Local Storage (Presigned PUT style)

- Upload token endpoint: `POST /v1/photos/upload-token`
- Upload URL returned: `PUT /v1/uploads/{fileId}?token=...`
- Raw download URL: `GET /v1/files/{fileId}/raw`
- Thumbnail URL: `GET /v1/files/{fileId}/thumb`

Batch create photos: `POST /v1/photos/batch`
