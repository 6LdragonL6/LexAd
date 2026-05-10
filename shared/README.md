# LexAd Shared

This directory is reserved for shared artifacts between frontend and backend:

- API contract definitions (OpenAPI / JSON Schema)
- Shared TypeScript type definitions
- Shared validation schemas
- Data format specifications

Currently, backend API types are defined in `backend/app/schemas/` and mirrored
in `frontend/src/types/`. For larger projects, consider auto-generating types
from the OpenAPI schema.
