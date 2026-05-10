# LexAd Architecture

## Overview

LexAd is an advertising compliance review platform using a monorepo
frontend/backend separated architecture.

```
                  ┌─────────────┐
                  │   Browser   │
                  └──────┬──────┘
                         │
              ┌──────────┴──────────┐
              │                     │
     ┌────────▼────────┐   ┌───────▼────────┐
     │  Frontend (Vue) │   │  Backend (API) │
     │  Static Site    │──▶│  Web Service   │
     │  Render Static  │   │  Render Web    │
     └─────────────────┘   └───────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │  Neon PostgreSQL │
                          └─────────────────┘
```

## Tech Stack

| Layer    | Technology                    |
|----------|-------------------------------|
| Frontend | Vue 3, Vite, TypeScript, Pinia |
| Backend  | FastAPI, Python 3.11, SQLAlchemy |
| Database | PostgreSQL (Neon)              |
| Deploy   | Render (Web Service + Static) |

## Directory Structure

```
LexAd/
├─ backend/        FastAPI application
├─ frontend/       Vue 3 SPA
├─ data/           JSON data files (rules, cases, templates)
├─ shared/         Shared artifacts
├─ docs/           Documentation
└─ .github/        CI/CD workflows
```

## Backend Layers

```
api/          HTTP endpoints (thin controllers)
schemas/      Pydantic request/response models
models/       SQLAlchemy database models
crud/         Data access operations
services/     Business logic orchestration
integrations/ Third-party API adapters
tasks/        Async task definitions
storage/      File/object storage abstraction
permissions/  Authorization logic
```

## Extension Points

The architecture reserves the following extension points for future
development:

1. **User Auth** — `permissions/`, `api/v1/endpoints/auth.py`
2. **File Upload / Object Storage** — `storage/`
3. **Async Tasks / Message Queue** — `tasks/`
4. **Third-party API Integration** — `integrations/`
5. **Admin Panel Module** — Separate frontend routes + backend endpoints
6. **Multi-Module Business Services** — `services/`
