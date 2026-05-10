# Development Guide

## Getting Started

See [deployment.md](deployment.md) for local development setup.

## Code Style

### Backend (Python)

- Follow PEP 8
- Use type annotations (`from __future__ import annotations`)
- Organize imports: stdlib, third-party, local
- Use Pydantic for all data models
- Keep routes thin — business logic in services

### Frontend (Vue 3 / TypeScript)

- Use Vue 3 `<script setup lang="ts">` syntax
- Use Composition API with Pinia stores
- Prefer `@/` path alias for imports
- Type all props, emits, and API responses

## Adding a New Feature

### Backend

1. Define schemas in `backend/app/schemas/`
2. Create database models in `backend/app/models/`
3. Add CRUD operations in `backend/app/crud/`
4. Implement business logic in `backend/app/services/`
5. Create API endpoint in `backend/app/api/v1/endpoints/`
6. Register route in `backend/app/api/v1/router.py`

### Frontend

1. Add types in `frontend/src/types/`
2. Add API functions in `frontend/src/api/`
3. Create page component in `frontend/src/pages/`
4. Add route in `frontend/src/router/index.ts`
5. Create store in `frontend/src/stores/` (if needed)

## Testing

### Backend

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
pytest app/tests/
```

### Frontend

```bash
cd frontend
npm run build  # type-check + build
```

## Database Migrations

```bash
cd backend
# Generate migration
alembic revision --autogenerate -m "description"
# Apply migration
alembic upgrade head
```
