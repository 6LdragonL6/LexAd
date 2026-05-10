# Deployment Guide

## Prerequisites

- [Render](https://render.com) account
- [Neon](https://neon.tech) PostgreSQL database
- GitHub repository

## Neon PostgreSQL Setup

1. Create a Neon project at [neon.tech](https://neon.tech)
2. Create a database named `lexad`
3. Copy the connection string:
   `postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/lexad?sslmode=require`

## Render Deployment

### Backend (Web Service)

1. In Render Dashboard, create a new **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `DATABASE_URL` — Neon connection string
   - `SECRET_KEY` — random secure string
   - `APP_ENV` — `production`
   - `FRONTEND_ORIGIN` — your frontend URL
   - `DEEPSEEK_API_KEY` — (optional)

### Frontend (Static Site)

1. In Render Dashboard, create a new **Static Site**
2. Connect the same GitHub repository
3. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Add environment variable:
   - `VITE_API_BASE_URL` — backend URL (e.g., `https://lexad-api.onrender.com/api/v1`)

Alternatively, render.yaml in the repo root defines both services for
Render Blueprint auto-deployment.

## Docker Compose (Local)

```bash
# Start both services
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:5173. The dev server proxies `/api` requests to the backend.
