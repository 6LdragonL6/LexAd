# LexAd Shared

This directory is reserved for shared artifacts between frontend and backend:

- API contract definitions (OpenAPI / JSON Schema)
- Shared TypeScript type definitions
- Shared validation schemas
- Data format specifications

Currently, backend types are defined in `backend/app/schemas/` and mirrored manually in `frontend/src/types/`. Future iterations may auto-generate frontend types from the OpenAPI schema via `openapi-typescript`.
