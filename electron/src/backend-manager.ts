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

        console.log(`Spawning Backend: ${pythonPath} ${scriptPath}`);
        this.backendProcess = spawn(pythonPath, ['main.py'], {
            cwd,
            stdio: 'pipe', // Pipe stdio to log
            shell: true, // Needed for some env vars or path resolution on Windows sometimes
        });

        this.attachListeners(this.backendProcess, 'Backend');
    }

    private startKeyManager() {
        const pythonPath = this.getPythonPath();
        const scriptPath = path.join(__dirname, '../../key_manager/main.py');
        const cwd = path.join(__dirname, '../../key_manager');

        console.log(`Spawning Key Manager: ${pythonPath} ${scriptPath}`);
        this.keyManagerProcess = spawn(pythonPath, ['main.py'], {
            cwd,
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
