# Sprint 0 architecture

| Directory | Responsibility |
| --- | --- |
| `apps/mobile` | Expo and TypeScript client. The entry point registers a static Hebrew screen with right-to-left text and safe-area spacing. |
| `apps/api` | FastAPI service. The application module registers the health router, which provides the typed response for `GET /health`. |
| `.github/workflows` | Independent mobile and API checks on pull requests and pushes to `main`. |

The apps run independently. The mobile screen renders locally, and the health endpoint reports API liveness with no external dependencies. Mobile tests render the screen, and API tests exercise the HTTP contract in process. Product features, persistence and external integrations are outside Sprint 0.
