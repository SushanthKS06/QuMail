import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { app } from 'electron';
import * as fs from 'fs';

export class ProcessManager {
    private backendProcess: ChildProcess | null = null;
    private keyManagerProcess: ChildProcess | null = null;
    private frontendProcess: ChildProcess | null = null;
    private isDev: boolean;
    private static instance: ProcessManager;

    constructor() {
        this.isDev = !app.isPackaged;
    }

    public static getInstance(): ProcessManager {
        if (!ProcessManager.instance) {
            ProcessManager.instance = new ProcessManager();
        }
        return ProcessManager.instance;
    }

    start() {
        if (process.env.QUMAIL_USE_DOCKER === '1') {
            console.log('Docker mode detected. Skipping local service spawning. Connecting to running containers.');
            // We assume backend is at localhost:8000 and KM at localhost:8001
            // Frontend is spawned by Electron (this process) usually via loadURL, 
            // but here 'startFrontend' spawns the 'npm run dev' key... wait.
            // If in Docker, Frontend is also running in Docker (nginx/port 5173).
            // But Electron needs to load a URL.
            // If we are developing Electron, we might want the frontend from Docker too?
            // Actually, usually in dev we want HMR. 
            // If we use Docker backend, we still need a frontend to load.
            // Option A: Load from localhost:5173 (Docker Frontend)
            // Option B: Spawn local frontend with npm run dev (for HMR) but change its API target?

            // Let's stick to the simplest integration:
            // "Docker Backend" means: 
            // 1. Don't spawn Backend (Python)
            // 2. Don't spawn KeyManager (Python)
            // 3. DO spawn Frontend (React) LOCALLY if we want HMR, OR just load from Docker if we don't care about frontend changes?
            // The user asked "how will my electron app opens". 
            // If they modify frontend code, they probably want local React.
            // But if they just want to RUN it, connecting to Docker is fine.

            // Let's assume: If QUMAIL_USE_DOCKER=1, we DO NOT spawn backend/KM.
            // But we SHOULD spawn frontend? No, if we use Docker, we might as well use the Docker frontend.
            // Wait, Electron `loadURL` in `main.ts` likely points to `http://localhost:5173`.
            // If Docker is running frontend at 5173, we don't need to spawn it either!

            return;
        }

        if (this.isDev) {
            console.log('Starting services in development mode...');
            this.startBackend();
            this.startKeyManager();
            this.startFrontend();
        } else {
            // In production, backend/KM heavily depends on packaging strategy.
            // For now, assume we proceed with dev logic or similar.
            // But typically frontend is static files, so we might only need backend/KM.
            // If the user hasn't bundled python, this won't work in prod exe.
            // We'll focus on dev environment as requested.
            console.log('Production mode detected. Ensure services are bundled or managed externally.');
            // Still try to start backend if relative paths exist (e.g. portable app structure)
        }
    }

    stop() {
        console.log('Stopping services...');
        this.killProcess(this.backendProcess, 'Backend');
        this.killProcess(this.keyManagerProcess, 'Key Manager');
        this.killProcess(this.frontendProcess, 'Frontend');
    }

    async restart() {
        this.stop();
        // Give time for ports to free up
        setTimeout(() => this.start(), 1000);
    }

    getUrl(): string {
        return 'http://localhost:8000';
    }

    getToken(): string | null {
        // Logic to retrieve token if managed by electron, otherwise null
        return null;
    }

    getIsReady(): boolean {
        return !!this.backendProcess;
    }

    private startBackend() {
        const pythonPath = this.getPythonPath();
        const scriptPath = path.join(__dirname, '../../backend/main.py');
        const cwd = path.join(__dirname, '../../backend');

        const env = {
            ...process.env,
            QUMAIL_DEV_MODE: this.isDev ? '1' : (process.env.QUMAIL_DEV_MODE || '0')
        };

        console.log(`Spawning Backend: ${pythonPath} ${scriptPath}`);
        this.backendProcess = spawn(pythonPath, ['main.py'], {
            cwd,
            env,
            stdio: 'pipe', // Pipe stdio to log
            shell: true, // Needed for some env vars or path resolution on Windows sometimes
        });

        this.attachListeners(this.backendProcess, 'Backend');
    }

    private startKeyManager() {
        const pythonPath = this.getPythonPath();
        const scriptPath = path.join(__dirname, '../../key_manager/main.py');
        const cwd = path.join(__dirname, '../../key_manager');

        const env = {
            ...process.env,
            QUMAIL_DEV_MODE: this.isDev ? '1' : (process.env.QUMAIL_DEV_MODE || '0')
        };

        console.log(`Spawning Key Manager: ${pythonPath} ${scriptPath}`);
        this.keyManagerProcess = spawn(pythonPath, ['main.py'], {
            cwd,
            env,
            stdio: 'pipe',
            shell: true,
        });

        this.attachListeners(this.keyManagerProcess, 'Key Manager');
    }

    private startFrontend() {
        // Start 'npm run dev' in frontend directory
        const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
        const cwd = path.join(__dirname, '../../frontend');

        console.log(`Spawning Frontend: ${npmCmd} run dev in ${cwd}`);
        this.frontendProcess = spawn(npmCmd, ['run', 'dev'], {
            cwd,
            stdio: 'pipe',
            shell: true,
        });

        this.attachListeners(this.frontendProcess, 'Frontend');
    }

    private getPythonPath(): string {
        // Try to find the virtual environment python
        const venvPythonProxy = path.join(__dirname, '../../myenv/Scripts/python.exe');
        if (fs.existsSync(venvPythonProxy)) {
            return venvPythonProxy;
        }

        // Fallback to global python
        return 'python';
    }

    private attachListeners(process: ChildProcess | null, name: string) {
        if (!process) return;

        process.stdout?.on('data', (data) => {
            console.log(`[${name}] ${data.toString().trim()}`);
        });

        process.stderr?.on('data', (data) => {
            console.error(`[${name} ERROR] ${data.toString().trim()}`);
        });

        process.on('close', (code) => {
            console.log(`[${name}] process exited with code ${code}`);
        });

        process.on('error', (err) => {
            console.error(`[${name}] Failed to start: ${err.message}`);
        });
    }

    private killProcess(child: ChildProcess | null, name: string) {
        if (child) {
            console.log(`Killing ${name}...`);
            // On Windows, child processes spawned with shell:true might need tree-kill
            // But basic kill might catch the shell.
            // For robustness in dev, we just try .kill()
            child.kill();
            // Typically on Windows with shell:true you need `taskkill /pid ${pid} /T /F`
            if (process.platform === 'win32' && child.pid) {
                try {
                    spawn('taskkill', ['/pid', child.pid.toString(), '/T', '/F']);
                } catch (e) {
                    // ignore
                }
            }
        }
    }
}

export function getBackendManager() {
    return ProcessManager.getInstance();
}
