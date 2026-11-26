# Grocery App

Sprint 0 establishes the Hebrew Expo mobile app, the FastAPI service, and continuous integration.

## Prerequisites

- Git, Node.js 24 with npm, and Python 3.13
- An Android or iOS device or simulator with an Expo Go version compatible with SDK 56 to open the mobile screen

## Mobile

From the repository root:

```sh
npm ci
npm start
```

Open the app from the Expo CLI using a device or simulator.

## API

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements-dev.txt
Set-Location apps/api
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On macOS or Linux, use `./.venv/bin/python` from the root and `../../.venv/bin/python` from `apps/api`. GET `http://127.0.0.1:8000/health` returns HTTP 200 and `{"status":"ok"}`.

## Checks

Run from the repository root:

```sh
npm run typecheck
npm test
npm exec --workspace @grocery/mobile -- expo install --check
```

Run from `apps/api` with the virtual environment active, or substitute its Python executable:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

See [architecture](docs/architecture.md) and the mandatory [project rules](AGENTS.md).
