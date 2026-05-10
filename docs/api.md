# LexAd API Documentation

Base URL: `https://<backend-host>/api/v1`

## Endpoints

### Health

| Method | Path             | Description         |
|--------|------------------|---------------------|
| GET    | `/health`        | Global health check |
| GET    | `/api/v1/health` | API health check    |

### Review

| Method | Path                           | Description                |
|--------|--------------------------------|----------------------------|
| POST   | `/api/v1/review/submit`        | Submit ad for review       |
| GET    | `/api/v1/review/result/{id}`   | Get review result by ID    |
| GET    | `/api/v1/review/cases`         | List case library          |
| GET    | `/api/v1/review/templates`     | List rewrite templates     |

### Auth (placeholder)

| Method | Path                  | Description      |
|--------|-----------------------|------------------|
| POST   | `/api/v1/auth/login`  | User login (501) |
| POST   | `/api/v1/auth/register` | Register (501) |

### Users (placeholder)

| Method | Path                | Description          |
|--------|---------------------|----------------------|
| GET    | `/api/v1/users/me`  | Current user profile |

## Submit Review

```
POST /api/v1/review/submit
Content-Type: multipart/form-data

raw_text: string (required)
image_file: file (optional)
```

Response: `StandardResponse` with full review pipeline output.

## Error Responses

```json
{
  "detail": "Error description"
}
```

Status codes: 401, 404, 422, 500, 501.
