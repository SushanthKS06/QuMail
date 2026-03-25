# Running QuMail with Docker

This guide explains how to build and run the entire QuMail system (Backend, Key Manager, Frontend) using Docker Compose.

## Prerequisites

- **Docker Desktop** installed and running.
- **Git** installed.
- **Minimum Memory**: Ensure Docker is allocated at least **4GB RAM** (preferably 6GB+) because compelling `liboqs` from source is resource-intensive.

## Configuration

The project is already configured for Docker.
- `docker-compose.yml`: Orchestrates the services.
- `.dockerignore`: Optimizes build time by excluding unnecessary files.

## Running the System

1. Open a terminal in the project root (`D:\QuMail`).
2. Run the build and start command:
    ```bash
    docker-compose up --build
    ```
3. Wait for the build to complete. 
    > **Note**: The `key_manager` and `backend` builds involve compiling `liboqs` (Quantum Safe Library) from source, which may take 5-10 minutes.

4. Once running, access the application:
    - **Frontend**: http://localhost:5173
    - **Backend API**: http://localhost:8000
    - **Key Manager**: http://localhost:8001

## Troubleshooting

### "Internal Server Error" or "EOF" during build
This usually indicates Docker ran out of memory or the daemon crashed.
**Fix**: Increase memory allocation in Docker Desktop settings -> Resources -> Memory.

### "liboqs not found"
If the container starts but exits with this error, verify that the build completed successfully. The Dockerfile compiles this library automatically.

### "Connection Refused"
Ensure all containers are running (`docker-compose ps`). The frontend depends on the backend being ready.

## Architecture

- **qumail-backend**: Python/FastAPI service.
- **qumail-km**: Python Key Manager service (simulates Quantum Key Distribution).
- **qumail-frontend**: React/Vite app serving via Nginx.
