/**
 * Python Backend Manager
 * 
 * Handles starting, stopping, and monitoring the Python FastAPI backend.
 */

import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as http from 'http'
import { app } from 'electron'

export class BackendManager {
    private process: ChildProcess | null = null
    private readonly port: number = 8000
    private readonly host: string = '127.0.0.1'
    private apiToken: string = ''
    private isReady: boolean = false

    constructor() {
        // Generate a random API token for frontend-backend auth
        this.apiToken = this.generateToken()
    }

    async start(): Promise<void> {
        if (this.process) {
            console.log('Backend already running')
            return
        }

        const backendPath = this.getBackendPath()
        const pythonPath = this.getPythonPath()

        console.log(`Starting backend from: ${backendPath}`)
        console.log(`Using Python: ${pythonPath}`)

        return new Promise((resolve, reject) => {
            this.process = spawn(pythonPath, ['main.py'], {
                cwd: backendPath,
                env: {
                    ...process.env,
                    API_TOKEN: this.apiToken,
                    PYTHONUNBUFFERED: '1',
                },
                stdio: ['ignore', 'pipe', 'pipe'],
            })

            this.process.stdout?.on('data', (data) => {
                console.log(`[Backend] ${data.toString().trim()}`)
            })

            this.process.stderr?.on('data', (data) => {
                console.error(`[Backend Error] ${data.toString().trim()}`)
            })

            this.process.on('error', (error) => {
                console.error('Failed to start backend:', error)
                reject(error)
            })

            this.process.on('exit', (code, signal) => {
                console.log(`Backend exited with code ${code}, signal ${signal}`)
                this.process = null
                this.isReady = false
            })

            // Wait for backend to be ready
            this.waitForReady()
                .then(() => {
                    this.isReady = true
                    resolve()
                })
                .catch(reject)
        })
    }

    async stop(): Promise<void> {
        if (!this.process) {
            return
        }

        return new Promise((resolve) => {
            if (this.process) {
                this.process.on('exit', () => {
                    this.process = null
                    this.isReady = false
                    resolve()
                })

                // Send SIGTERM for graceful shutdown
                this.process.kill('SIGTERM')

                // Force kill after 5 seconds if not stopped
                setTimeout(() => {
                    if (this.process) {
                        this.process.kill('SIGKILL')
                    }
                }, 5000)
            } else {
                resolve()
            }
        })
    }

    async restart(): Promise<void> {
        await this.stop()
        await this.start()
    }

    getUrl(): string {
        return `http://${this.host}:${this.port}`
    }

    getToken(): string {
        return this.apiToken
    }

    getIsReady(): boolean {
        return this.isReady
    }

    private async waitForReady(maxAttempts: number = 30): Promise<void> {
        for (let i = 0; i < maxAttempts; i++) {
            try {
                await this.healthCheck()
                console.log('Backend is ready')
                return
            } catch {
                await this.sleep(500)
            }
        }
        throw new Error('Backend failed to start within timeout')
    }

    private healthCheck(): Promise<void> {
        return new Promise((resolve, reject) => {
            const request = http.get(`${this.getUrl()}/health`, (response) => {
                if (response.statusCode === 200) {
                    resolve()
                } else {
                    reject(new Error(`Health check failed: ${response.statusCode}`))
                }
            })

            request.on('error', reject)
            request.setTimeout(1000, () => {
                request.destroy()
                reject(new Error('Health check timeout'))
            })
        })
    }

    private getBackendPath(): string {
        if (app.isPackaged) {
            // In packaged app, backend is in resources
            return path.join(process.resourcesPath, 'backend')
        } else {
            // In development, backend is sibling directory
            return path.join(__dirname, '../../backend')
        }
    }

    private getPythonPath(): string {
        // Try to find Python in common locations
        const pythonPaths = [
            'python',
            'python3',
            'python.exe',
            'python3.exe',
        ]

        // In packaged app, we might bundle Python
        if (app.isPackaged) {
            const bundledPython = path.join(process.resourcesPath, 'python', 'python.exe')
            pythonPaths.unshift(bundledPython)
        }

        // For now, just use system Python
        return process.platform === 'win32' ? 'python' : 'python3'
    }

    private generateToken(): string {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        let result = ''
        for (let i = 0; i < 32; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length))
        }
        return result
    }

    private sleep(ms: number): Promise<void> {
        return new Promise((resolve) => setTimeout(resolve, ms))
    }
}

// Global instance
let backendManagerInstance: BackendManager | null = null

export function getBackendManager(): BackendManager {
    if (!backendManagerInstance) {
        backendManagerInstance = new BackendManager()
    }
    return backendManagerInstance
}
