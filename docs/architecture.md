# Architecture decisions — Phase 1

## Modular monolith

Project Voice will use a single repository and a single private deployment. The browser application and API are separate runtime processes because their workloads differ, but they evolve together and will share one database, one object store, and one release process. This keeps future audio processing isolated without prematurely adopting microservices.

## Boundaries

| Boundary | Responsibility | Not responsible for yet |
| --- | --- | --- |
| `apps/web` | Recording and coaching user experience | Audio processing or business rules |
| `apps/api` | Private API, orchestration, domain logic | Long-running analysis jobs |
| future worker module | Audio/AI processing jobs | Public-facing HTTP requests |

## Privacy principles

- Raw audio, transcripts, and coaching content are sensitive data.
- Application logs contain operational metadata only: request ID, route, status, and duration.
- Secrets live in environment variables or a deployment secret store, never source control.
- Cloud AI integrations will be opt-in and isolated behind explicit adapters in a later phase.

## Authentication

Authentication is deliberately deferred until the persistence and deployment design are in place. Before any network-accessible deployment, Phase 12 will add a single-user login, secure session handling, rate limits, and HTTPS-only deployment settings.
