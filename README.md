# Project Voice

Project Voice is a private, single-user communication coaching application. The first release is a modular monolith: a browser interface and a Python API that share one repository and one deployment boundary.

## Phase 1 foundation

This phase establishes a runnable development baseline. It intentionally does **not** process audio, persist user data, or call AI services yet.

- `apps/web`: Next.js browser application
- `apps/api`: FastAPI internal API
- `docs`: architecture decisions and phase notes
- `compose.yaml`: local container configuration

## Local setup

Prerequisites: Node.js 22+, Python 3.11+, and optionally Docker Desktop.

1. Copy `.env.example` to `.env`.
2. Start the API:

   ```powershell
   cd apps/api
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   uvicorn app.main:app --reload --port 8000
   ```

3. In another terminal, start the web app:

   ```powershell
   cd apps/web
   npm install
   npm run dev
   ```

Open `http://localhost:3000`. The API health endpoint is `http://localhost:8000/api/v1/health/live`.

## Quality checks

```powershell
cd apps/api
pytest
ruff check .

cd ../web
npm run lint
npm run typecheck
```

## Privacy baseline

No audio, transcripts, or user content is logged by the starter application. Environment files and future runtime storage are excluded from version control. Database and audio-storage implementation begins in Phase 2.
