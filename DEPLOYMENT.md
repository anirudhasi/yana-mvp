# Deployment Prep

This repo is prepared for a simple split deployment:

- Backend: Django app from `backend/`
- Frontend: static site from `frontend/`

## Backend

Use the files in `backend/`:

- `Procfile`
- `build.sh`
- `.env.example`
- `yana/wsgi.py`

Set these environment variables on your host:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOW_ALL_ORIGINS=False`
- `CORS_ALLOWED_ORIGINS`
- `EXPOSE_OTP_IN_RESPONSE=True` for client validation, `False` later
- `DATABASE_URL` if using Postgres

If `DATABASE_URL` is not set, Django falls back to SQLite.

## Frontend

Before deploying the frontend, update `frontend/config.js`:

```js
window.YANA_CONFIG = {
  apiBaseUrl: "https://your-backend-url.example.com/api",
};
```

For a static host like Netlify, the included `netlify.toml` is enough.

## Render

This repo also includes `render.yaml` with a starter setup for:

- one Python web service for the backend
- one static site for the frontend

Update the frontend config to point at the final backend URL after the backend service is live.
