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

## Database setup (Phase 2)

Project Voice uses PostgreSQL for its private, persistent data. The schema covers your profile, goals, speech sessions, media metadata, timestamped transcripts, analysis runs, and measured metrics. Audio is **not** stored in the database; a future phase will store it in private object storage and retain only its metadata here.

With Docker Desktop installed, create the root `.env` file from `.env.example`, change `POSTGRES_PASSWORD`, then run:

```powershell
docker compose up -d db
docker compose --profile setup run --rm migrate
docker compose up api web
```

The API readiness endpoint (`/api/v1/health/ready`) returns `ready` only when PostgreSQL is reachable. Run migrations after every future schema update:

```powershell
cd apps/api
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

## Recording a practice session (Phase 3)

Start the database and API using the commands above, then start the web app with `npm run dev` from `apps/web`. At `http://localhost:3000`, select **Record** and permit microphone access—or choose **Or upload audio**. A saved recording is held in the local `storage/` folder, which is excluded from Git. This phase captures and stores audio only; transcription and coaching arrive later.

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

No audio, transcripts, or user content is logged by the application. Environment files and future runtime storage are excluded from version control. Audio-storage implementation begins in a later phase.

## Phase 7: AI coaching (Gemini)

After local transcription and deterministic metrics, open the session report from the recorder. Run local preprocessing, transcription, and analysis first. The separate **Generate Gemini coaching** action requires an explicit in-app consent checkbox and sends only transcript text, deterministic metrics, and any saved goal/context. Raw audio is never sent to Gemini.

Set these server-side values in the root `.env` file to enable coaching:

```dotenv
VOICE_COACH_GEMINI_API_KEY=your_google_ai_studio_key
VOICE_COACH_GEMINI_MODEL=your_account_enabled_model_id
```

Confirm the model identifier is available to your own API key before setting it. These values are passed only to the API container and must never use a `NEXT_PUBLIC_` prefix. The coaching output is Pydantic-validated, every strength/improvement must cite a supplied metric value or exact transcript excerpt, and the report is stored in PostgreSQL. If Gemini is unavailable or returns unverifiable evidence, the API returns a safe generic error rather than provider details.
