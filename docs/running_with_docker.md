# Running QuMail with Docker

QuMail supports a hybrid running mode where the backend services run in Docker, and the Electron application runs on your host machine.

## Prerequisites

- Docker Desktop installed and running.
- Node.js and npm installed.

## Step 1: Start Backend Services

Start the backend, key manager, and web frontend using Docker Compose:

```bash
# In the root usage directory (d:\QuMail)
docker-compose up -d --build
```

This will expose:
- **Backend**: `http://localhost:8000`
- **Key Manager**: `http://localhost:8100` (mapped from 8001)
- **Web Frontend**: `http://localhost:5173`

## Step 2: Run Electron App

Open a **new terminal** and navigate to the `electron` directory:

```bash
cd electron
```

### Install Dependencies (First Time Only)

```bash
npm install
```

### Start Electron in "Docker Mode"

Set the `QUMAIL_USE_DOCKER` environment variable to `1` before running `npm run dev`.

**PowerShell (Windows):**
```powershell
$env:QUMAIL_USE_DOCKER="1"; npm run dev
```

**Command Prompt (cmd):**
```cmd
set QUMAIL_USE_DOCKER=1 && npm run dev
```

**Bash (Git Bash / Linux / Mac):**
```bash
QUMAIL_USE_DOCKER=1 npm run dev
```

## How it Works

- When `QUMAIL_USE_DOCKER` is set, the Electron app **skips** spawning its own local instances of the backend and key manager.
- Instead, it connects to the services already running in your Docker containers.
- It also loads the frontend application served by Docker (or the local dev server if configured), ensuring a smooth integration.
