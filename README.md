# BioQC Agent

Phase 1 scaffold for the BioQC Agent platform.

## Project structure

```
backend/     FastAPI application (SQLite + SQLAlchemy + Pydantic)
frontend/    Next.js application (TypeScript + Tailwind)
uploads/     Uploaded source files (future phases)
reports/     Generated reports (future phases)
docs/        Project documentation
```

## Backend

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "service": "bioqc-agent"}
```

API docs: http://localhost:8000/docs

## Frontend

### Setup

```bash
cd frontend
npm install
```

### Run

```bash
npm run dev
```

App: http://localhost:3000

## Phase 1 scope

- FastAPI app with SQLAlchemy database setup
- Health endpoint
- Next.js + TypeScript + Tailwind scaffold

Not yet implemented: file uploads, parsing, Gemini integration, PDF generation, or application UI pages.
