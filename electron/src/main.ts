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

    const FRONTEND_URL = 'http://localhost:5174';

    const loadFrontend = (retries = 3) => {
        mainWindow?.loadURL(FRONTEND_URL).catch((err) => {
            console.error(`Failed to load frontend: ${err.message}`);
            if (retries > 0) {
                console.log(`Retrying in 2 seconds... (${retries} attempts left)`);
                setTimeout(() => loadFrontend(retries - 1), 2000);
            }
        });
    };

    // Handle navigation failures (e.g., after OAuth redirect)
    mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
        console.error(`Navigation failed: ${errorDescription} (${errorCode}) for ${validatedURL}`);
        // If it failed to load the frontend URL, retry
        if (validatedURL.startsWith(FRONTEND_URL) || validatedURL.includes('localhost:5173')) {
            console.log('Retrying frontend load after navigation failure...');
            setTimeout(() => loadFrontend(2), 1500);
        }
    });

    // Wait for services to spin up
    setTimeout(() => loadFrontend(), 3000);

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
