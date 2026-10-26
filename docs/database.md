# Database architecture — Phase 2

PostgreSQL is the system of record for Project Voice. It stores structured, private coaching history; raw media remains outside the database in future private object storage.

| Area | Tables | Why it exists |
| --- | --- | --- |
| Private identity | `personal_profiles` | Enforces one local owner profile without introducing multi-user SaaS accounts. |
| Goals | `communication_goals` | Stores active coaching targets and their priorities. |
| Practice history | `speech_sessions` | One record per recording, upload, or presentation rehearsal. |
| Media inventory | `media_assets` | Holds object-storage keys, integrity metadata, and encryption-key version—not audio bytes. |
| Transcript | `transcripts`, `transcript_words` | Keeps text and word-level timestamps needed for deterministic analysis. |
| Analysis provenance | `analysis_runs`, `metric_values` | Preserves the pipeline version and the exact metrics it produced. |

## Key guarantees

- One `personal_profiles` row is permitted; every goal and speech session belongs to it.
- A session may have many media assets but one current transcript.
- Transcript words use a composite `(transcript_id, position)` primary key for deterministic ordering.
- An analysis run may emit each metric code only once.
- Cascade deletion removes dependent sensitive data when a profile or session is deleted.
- Indexes support the two important future reads: chronological session history and metric trends.

The initial schema migration is `8351061cbca6`. Do not edit an applied migration; add a new Alembic revision for every later schema change.
