import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import { ProcessManager } from './backend-manager';

// Disable security warnings for dev (optional, but reduces noise)
process.env['ELECTRON_DISABLE_SECURITY_WARNINGS'] = 'true';

let mainWindow: BrowserWindow | null = null;
const processManager = ProcessManager.getInstance();

function createWindow(): void {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        title: 'QuMail - Quantum Secure Email',
        icon: path.join(__dirname, '../resources/icon.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
        backgroundColor: '#0a0a0f',
        show: false,
    });

    // Wait slightly for services to spin up, or just load and let retry
    // Ideally we'd poll, but for dev, a simple load is usually fine as Vite HMR connects later
    // or we refresh.
    // Let's add a small delay or retry logic?
    // Actually Vite takes a bit.

    // We'll try loading immediately, Vite might show "connecting..." 
    setTimeout(() => {
        mainWindow?.loadURL('http://localhost:5173');
    }, 3000); // 3 second delay to let Vite start

    mainWindow.once('ready-to-show', () => {
        mainWindow?.show();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(() => {
    processManager.start();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    processManager.stop();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    processManager.stop();
});
