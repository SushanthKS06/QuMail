# Running QuMail with Docker

QuMail supports a hybrid running mode where the backend services (FastAPI, Key Manager, Vite Frontend Server) run in Docker, and the Electron application runs on your host machine. This is the recommended way to run the application for a seamless development and production-like experience.

## Prerequisites

- **Docker Desktop** installed and running.
- **Node.js** and **npm** installed on your host machine.
- **Git** installed.
- **Minimum Memory**: Ensure Docker is allocated at least **4GB RAM** (preferably 6GB+) because compiling `liboqs` (Quantum Safe Library) from source is resource-intensive.

## Step 1: Start Backend Services

Start the backend, key manager, and web frontend using Docker Compose:

```bash
# In the root project directory
docker-compose up -d --build
```

Wait a few minutes for the build to complete. 
> **Note**: The `key_manager` and `backend` builds involve compiling `liboqs` from source, which may take 5-10 minutes.

This will expose:
- **Backend API**: `http://localhost:8000`
- **Key Manager**: `http://localhost:8100` (mapped from 8001 internally)
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
- Instead, it connects directly to the services already running in your Docker containers.
- It loads the frontend application served by Docker (or the local dev server if configured), ensuring a smooth integration.
- The React frontend handles all UI, interacting securely with the Dockerized FastAPI backend.

## Troubleshooting

### "Internal Server Error" or "EOF" during build
This usually indicates Docker ran out of memory or the daemon crashed.
**Fix**: Increase memory allocation in Docker Desktop settings -> Resources -> Memory.

### "liboqs not found"
If the container starts but exits with this error, verify that the build completed successfully. The Dockerfile compiles this library automatically.

### "Connection Refused"
Ensure all containers are running (`docker-compose ps`). The frontend depends on the backend being ready, and the backend needs the Key Manager.
