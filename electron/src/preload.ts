/**
 * Electron Preload Script
 * 
 * Exposes a secure API to the renderer process.
 * This is the bridge between the frontend and the main process.
 */

import { contextBridge, ipcRenderer } from 'electron'

// Expose protected methods to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
    // Backend communication
    getBackendUrl: (): Promise<string> => ipcRenderer.invoke('get-backend-url'),
    getApiToken: (): Promise<string> => ipcRenderer.invoke('get-api-token'),

    // Backend status
    isBackendReady: (): Promise<boolean> => ipcRenderer.invoke('is-backend-ready'),
    restartBackend: (): Promise<void> => ipcRenderer.invoke('restart-backend'),

    // OAuth handling
    openOAuthWindow: (url: string): Promise<string> => ipcRenderer.invoke('open-oauth-window', url),

    // App info
    getAppVersion: (): string => process.env.npm_package_version || '1.0.0',
    getPlatform: (): string => process.platform,

    // Window controls
    minimizeWindow: (): void => ipcRenderer.send('window-minimize'),
    maximizeWindow: (): void => ipcRenderer.send('window-maximize'),
    closeWindow: (): void => ipcRenderer.send('window-close'),

    // Events
    onBackendStatusChange: (callback: (status: string) => void): void => {
        ipcRenderer.on('backend-status', (_event, status) => callback(status))
    },
})

// Type declarations for the exposed API
declare global {
    interface Window {
        electronAPI: {
            getBackendUrl: () => Promise<string>
            getApiToken: () => Promise<string>
            isBackendReady: () => Promise<boolean>
            restartBackend: () => Promise<void>
            openOAuthWindow: (url: string) => Promise<string>
            getAppVersion: () => string
            getPlatform: () => string
            minimizeWindow: () => void
            maximizeWindow: () => void
            closeWindow: () => void
            onBackendStatusChange: (callback: (status: string) => void) => void
        }
    }
}
