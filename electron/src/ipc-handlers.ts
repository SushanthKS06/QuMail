/**
 * IPC Handlers
 * 
 * Handles IPC communication between renderer and main process.
 */

import { ipcMain, BrowserWindow, shell } from 'electron'
import { getBackendManager } from './backend-manager'

export function setupIpcHandlers(): void {
    const backendManager = getBackendManager()

    // Backend URL
    ipcMain.handle('get-backend-url', () => {
        return backendManager.getUrl()
    })

    // API Token
    ipcMain.handle('get-api-token', () => {
        return backendManager.getToken()
    })

    // Backend status
    ipcMain.handle('is-backend-ready', () => {
        return backendManager.getIsReady()
    })

    // Restart backend
    ipcMain.handle('restart-backend', async () => {
        await backendManager.restart()
    })

    // OAuth window handling
    ipcMain.handle('open-oauth-window', async (_event, url: string) => {
        return new Promise<string>((resolve, reject) => {
            const authWindow = new BrowserWindow({
                width: 600,
                height: 700,
                show: true,
                webPreferences: {
                    nodeIntegration: false,
                    contextIsolation: true,
                },
            })

            authWindow.loadURL(url)

            // Listen for redirect to our callback URL
            authWindow.webContents.on('will-redirect', (_event, redirectUrl) => {
                if (redirectUrl.includes('/api/v1/auth/oauth/gmail/callback')) {
                    authWindow.close()
                    resolve(redirectUrl)
                }
            })

            authWindow.on('closed', () => {
                reject(new Error('Auth window closed'))
            })
        })
    })

    // Window controls
    ipcMain.on('window-minimize', (event) => {
        const window = BrowserWindow.fromWebContents(event.sender)
        window?.minimize()
    })

    ipcMain.on('window-maximize', (event) => {
        const window = BrowserWindow.fromWebContents(event.sender)
        if (window?.isMaximized()) {
            window.unmaximize()
        } else {
            window?.maximize()
        }
    })

    ipcMain.on('window-close', (event) => {
        const window = BrowserWindow.fromWebContents(event.sender)
        window?.close()
    })
}
